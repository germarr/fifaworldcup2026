from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import requests
import time
from sqlmodel import SQLModel, Session, create_engine, select, text
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from app.config import DATABASE_URL
from app.models.fifa_team import FifaTeam
from app.models.kalshi_team_chance import KalshiTeamChance
from app.models.kalshi_team_ranking import KalshiTeamRanking

DEFAULT_EVENT_TICKER = "kxmenworldcup-26"
LOCAL_TZ = "America/New_York"


class KalshiClient:
    def __init__(self, base_url: str = "https://api.elections.kalshi.com/trade-api/v2"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get_event(self, event_ticker: str) -> Dict[str, object]:
        url = f"{self.base_url}/events/{event_ticker.upper()}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_candlesticks(
        self,
        series_ticker: str,
        market_ticker: str,
        start_ts: int,
        end_ts: int,
        minutes: int,
    ) -> Dict[str, object]:
        url = (
            f"{self.base_url}/series/{series_ticker}/markets/{market_ticker}/candlesticks"
            f"?start_ts={start_ts}&end_ts={end_ts}&period_interval={minutes}"
        )
        delay_seconds = 5
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            response = self.session.get(url, timeout=30)
            if response.status_code == 429:
                print(f"Rate limited (429) for {market_ticker}. Sleeping {delay_seconds}s before retry {attempt}/{max_attempts}.")
                time.sleep(delay_seconds)
                delay_seconds = min(delay_seconds * 2, 120)
                continue
            response.raise_for_status()
            return response.json()

        print(f"Rate limit retries exhausted for {market_ticker}. Returning empty response.")
        return {"candlesticks": []}


def add_time_features(df, current_time_utc=None, open_col="open_time", close_col="close_time"):
    """
    Adds:
      - time_since_open
      - time_to_close
      - total_duration
      - lifecycle_pct  (clipped to [0, 1])
    """
    if current_time_utc is None:
        current_time_utc = datetime.now(timezone.utc)

    out = df.copy()

    # Ensure datetimes are tz-aware UTC
    out[open_col] = pd.to_datetime(out[open_col], utc=True)
    out[close_col] = pd.to_datetime(out[close_col], utc=True)

    current_ts = pd.to_datetime(current_time_utc).tz_convert('UTC')
    out['current_time_utc'] = current_ts

    # Time deltas
    out['time_since_open'] = out['current_time_utc'] - out[open_col]
    out['time_to_close']   = out[close_col] - out['current_time_utc']
    out['total_duration']  = out[close_col] - out[open_col]

    # Lifecycle percentage, clipped to [0, 1]
    # (will be NaN if total_duration == 0)
    lifecycle_raw = out['time_since_open'] / out['total_duration']
    out['lifecycle_pct'] = lifecycle_raw.clip(lower=0, upper=1)

    return out

def add_phase_and_granularity(df):
    """
    Uses lifecycle_pct + time_to_close to add:
      - phase                ('early', 'middle', 'late')
      - granularity_phase    (1440, 60, 1)
      - granularity_final    (final choice with time-to-close override)
    """
    out = df.copy()

    # --- Phase from lifecycle_pct ---
    conditions = [
        out['lifecycle_pct'] < 0.6,
        (out['lifecycle_pct'] >= 0.6) & (out['lifecycle_pct'] < 0.9),
        out['lifecycle_pct'] >= 0.9
    ]
    choices = ['early', 'middle', 'late']

    out['phase'] = np.select(conditions, choices, default='late')

    # Map phase → base granularity (in minutes)
    phase_to_gran = {
        'early': 1440,
        'middle': 60,
        'late': 1
    }
    out['granularity_phase'] = out['phase'].map(phase_to_gran)

    # --- Time-to-close override ---
    one_day = pd.Timedelta(days=1)
    seven_days = pd.Timedelta(days=7)

    def gran_from_ttc(ttc):
        # ttc can be negative if already closed; treat as "very close"
        if ttc > seven_days:
            return 1440
        elif ttc > one_day:
            return 60
        else:
            return 1

    out['granularity_ttc'] = out['time_to_close'].apply(gran_from_ttc)

    # Final choice: more granular of the two
    out['granularity_final'] = out[['granularity_phase', 'granularity_ttc']].min(axis=1)

    return out

def add_span_capped_granularity(df, max_days_minute=3, max_days_hour=55):
    """
    Adds:
      - days_since_open
      - granularity_span_cap: granularity_final adjusted so long-open markets
        don't use ultra-fine resolution for the whole span.
    """
    out = df.copy()

    # Days since open (can be negative if not open yet; that’s fine)
    out['days_since_open'] = out['time_since_open'] / pd.Timedelta(days=1)

    # Start from the existing final granularity
    out['granularity_span_cap'] = out['granularity_final']

    # If market has been open longer than max_days_minute, don't allow 1-minute
    cond_minute_too_long = (
        (out['granularity_span_cap'] == 1) &
        (out['days_since_open'] > max_days_minute)
    )
    out.loc[cond_minute_too_long, 'granularity_span_cap'] = 60

    # If market has been open longer than max_days_hour, don't allow hourly
    cond_hour_too_long = (
        (out['granularity_span_cap'] == 60) &
        (out['days_since_open'] > max_days_hour)
    )
    out.loc[cond_hour_too_long, 'granularity_span_cap'] = 1440

    return out

def minutes_to_df(records, local_tz: str = LOCAL_TZ):
    """
    Flatten minute-level prediction market records into a tidy DataFrame.
    Safe against missing keys and None values.
    """
    if not records:
        return pd.DataFrame()

    flat = []
    for r in records:
        price   = (r.get("price") or {})      # nested dict (may be None)
        yes_bid = (r.get("yes_bid") or {})
        yes_ask = (r.get("yes_ask") or {})

        row = {
            "end_period_ts": r.get("end_period_ts"),
            "open_interest": r.get("open_interest"),
            "volume": r.get("volume"),
            # price (in cents)
            "price_open": price.get("open"),
            "price_high": price.get("high"),
            "price_low": price.get("low"),
            "price_close": price.get("close"),
            "price_mean": price.get("mean"),
            "price_previous": price.get("previous"),
            # top-of-book bids/asks (in cents)
            "yes_bid_open": yes_bid.get("open"),
            "yes_bid_high": yes_bid.get("high"),
            "yes_bid_low": yes_bid.get("low"),
            "yes_bid_close": yes_bid.get("close"),
            "yes_ask_open": yes_ask.get("open"),
            "yes_ask_high": yes_ask.get("high"),
            "yes_ask_low": yes_ask.get("low"),
            "yes_ask_close": yes_ask.get("close"),
        }
        flat.append(row)

    df = pd.DataFrame(flat)

    # Cast numerics
    num_cols = [c for c in df.columns if c not in ("end_period_ts",)]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Time columns
    df["end_period_utc"] = pd.to_datetime(df["end_period_ts"], unit="s", utc=True)

    df["end_period_local"] = df["end_period_utc"].dt.tz_convert(local_tz).dt.tz_localize(None)


    # Derived metrics (in cents)
    bid = df["yes_bid_close"]
    ask = df["yes_ask_close"]
    df["mid_cents"] = np.where(bid.notna() & ask.notna(), (bid + ask) / 2.0, np.nan)
    df["spread_cents"] = np.where(bid.notna() & ask.notna(), ask - bid, np.nan)

    # Dollar versions
    to_dollars = lambda x: x / 100.0 if pd.notna(x) else np.nan
    cents_cols = [
        "price_open","price_high","price_low","price_close","price_mean","price_previous",
        "yes_bid_open","yes_bid_high","yes_bid_low","yes_bid_close",
        "yes_ask_open","yes_ask_high","yes_ask_low","yes_ask_close",
        "mid_cents","spread_cents"
    ]
    for c in cents_cols:
        if c in df.columns:
            df[c.replace("_cents","").replace("price_","price_") + "_dollars"] = df[c].apply(to_dollars)

    # Sort and tidy
    df = df.sort_values("end_period_ts").reset_index(drop=True)

    # Nice column order
    front = ["end_period_ts","end_period_utc","end_period_local","open_interest","volume"]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest]


def get_event_markets(event_ticker: str, client: KalshiClient) -> pd.DataFrame:
    payload = client.get_event(event_ticker)
    eventinfo = payload.get("event") or {}
    eventmarkets = payload.get("markets") or []
    if not eventmarkets:
        return pd.DataFrame()

    om = pd.DataFrame(eventmarkets)
    om["open_time"] = pd.to_datetime(om["open_time"], utc=True)
    om["close_time"] = pd.to_datetime(om["expected_expiration_time"], utc=True)
    om["start_ts"] = om["open_time"].apply(lambda x: int(x.timestamp()))
    om["end_ts"] = om["close_time"].apply(lambda x: int(x.timestamp()))
    om["local_open_time"] = om["open_time"].dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    om["local_close_time"] = om["close_time"].dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)

    om["series_ticker"] = (eventinfo.get("series_ticker") or "").upper()
    om["category"] = eventinfo.get("category")
    om["event_title"] = eventinfo.get("title")
    om["event_sub_title"] = eventinfo.get("sub_title")
    om["event_ticker"] = event_ticker.upper()
    om["team_name"] = om["yes_sub_title"]

    ticker_lo = om[
        [
            "category",
            "event_title",
            "event_sub_title",
            "team_name",
            "series_ticker",
            "event_ticker",
            "ticker",
            "start_ts",
            "open_time",
            "close_time",
            "local_open_time",
            "local_close_time",
            "end_ts",
        ]
    ].drop_duplicates()

    ticker_lo["start_date"] = ticker_lo["local_open_time"].dt.date
    ticker_lo["end_date"] = ticker_lo["local_close_time"].dt.date
    return ticker_lo


def build_times_df(markets_df: pd.DataFrame, current_time_utc: datetime) -> pd.DataFrame:
    if markets_df.empty:
        return markets_df

    times_df = markets_df[
        [
            "team_name",
            "event_title",
            "ticker",
            "event_ticker",
            "series_ticker",
            "start_ts",
            "end_ts",
            "open_time",
            "close_time",
        ]
    ].copy()
    times_df["current_time"] = current_time_utc
    times_df["current_ts"] = int(current_time_utc.timestamp())

    times_df = add_time_features(df=times_df)
    times_df = add_phase_and_granularity(times_df)
    times_df = add_span_capped_granularity(times_df, max_days_minute=3, max_days_hour=7)
    return times_df


def fetch_all_candlesticks(
    times_df: pd.DataFrame,
    client: KalshiClient,
    override_start_ts: Optional[int] = None,
    override_end_ts: Optional[int] = None,
    override_granularity: Optional[int] = None,
) -> pd.DataFrame:
    if times_df.empty:
        return pd.DataFrame()

    all_ticker_data: List[pd.DataFrame] = []
    for record in times_df.to_dict("records"):
        start_ts = override_start_ts or record["start_ts"]
        end_ts = override_end_ts or record["current_ts"]
        minutes = override_granularity or int(record["granularity_span_cap"])

        candlesticks = client.get_candlesticks(
            series_ticker=record["series_ticker"],
            market_ticker=record["ticker"],
            start_ts=start_ts,
            end_ts=end_ts,
            minutes=minutes,
        ).get("candlesticks")

        if not candlesticks:
            continue

        dfa = minutes_to_df(candlesticks, local_tz=LOCAL_TZ)
        if dfa.empty:
            continue

        dfa["team_name"] = record["team_name"]
        dfa["event_title"] = record["event_title"]
        dfa["event_ticker"] = record["event_ticker"]
        dfa["ticker"] = record["ticker"]
        dfa["series_ticker"] = record["series_ticker"]
        all_ticker_data.append(dfa)
        print(record["team_name"], end=",")

    if not all_ticker_data:
        return pd.DataFrame()

    return pd.concat(all_ticker_data).copy()


def build_ranking(ticker_df: pd.DataFrame) -> pd.DataFrame:
    if ticker_df.empty:
        return pd.DataFrame()

    ranking = (
        ticker_df[
            ["team_name", "end_period_local", "event_title", "ticker", "series_ticker", "yes_bid_open"]
        ]
        .groupby(["team_name"])
        .agg(avg_chance=("yes_bid_open", "mean"))
        .reset_index()
        .assign(avg_chance=lambda df: df["avg_chance"].round(2))
        .sort_values(by="avg_chance", ascending=False)
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={"index": "rank"})
        .assign(rank=lambda df: df["rank"] + 1)
    )
    return ranking


def _normalize_team_name(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    return name.strip().lower()


def load_team_lookup(session: Session) -> Dict[str, int]:
    rows = session.exec(select(FifaTeam.name, FifaTeam.id)).all()
    return {_normalize_team_name(name): team_id for name, team_id in rows}


def attach_team_ids(df: pd.DataFrame, team_map: Dict[str, int]) -> pd.DataFrame:
    out = df.copy()
    out["team_id"] = out["team_name"].apply(lambda name: team_map.get(_normalize_team_name(name)))
    return out


def _clean_value(value):
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def save_rankings(session: Session, ranking_df: pd.DataFrame, event_ticker: str, as_of: datetime) -> None:
    if ranking_df.empty:
        return

    session.connection().exec_driver_sql(
        "DELETE FROM kalshi_team_rankings WHERE event_ticker = :event_ticker",
        {"event_ticker": event_ticker.upper()},
    )
    rows = []
    for record in ranking_df.to_dict("records"):
        rows.append(
            KalshiTeamRanking(
                team_id=record.get("team_id"),
                team_name=record.get("team_name"),
                event_ticker=event_ticker.upper(),
                series_ticker=record.get("series_ticker"),
                avg_yes_bid_open=_clean_value(record.get("avg_chance")),
                rank=int(record.get("rank")),
                as_of=as_of,
            )
        )
    session.add_all(rows)
    session.commit()


def save_chances(session: Session, ticker_df: pd.DataFrame, event_ticker: str) -> None:
    if ticker_df.empty:
        return

    insert_sql = """
        INSERT OR IGNORE INTO kalshi_team_chances (
            team_id, team_name, event_ticker, series_ticker, market_ticker,
            end_period_ts, end_period_utc, yes_bid_open, yes_ask_close,
            mid_cents, volume, open_interest, created_at
        ) VALUES (
            :team_id, :team_name, :event_ticker, :series_ticker, :market_ticker,
            :end_period_ts, :end_period_utc, :yes_bid_open, :yes_ask_close,
            :mid_cents, :volume, :open_interest, :created_at
        )
        """

    payload = []
    for record in ticker_df.to_dict("records"):
        payload.append(
            {
                "team_id": record.get("team_id"),
                "team_name": record.get("team_name"),
                "event_ticker": event_ticker.upper(),
                "series_ticker": record.get("series_ticker"),
                "market_ticker": record.get("ticker"),
                "end_period_ts": record.get("end_period_ts"),
                "end_period_utc": _clean_value(record.get("end_period_utc")),
                "yes_bid_open": _clean_value(record.get("yes_bid_open")),
                "yes_ask_close": _clean_value(record.get("yes_ask_close")),
                "mid_cents": _clean_value(record.get("mid_cents")),
                "volume": _clean_value(record.get("volume")),
                "open_interest": _clean_value(record.get("open_interest")),
                "created_at": datetime.now(timezone.utc),
            }
        )

    session.connection().exec_driver_sql(insert_sql, payload)
    session.commit()

def local_to_utc_epoch_range(start_year, start_month, start_day, start_hour,end_year, end_month, end_day, end_hour,start_minute=0, end_minute=0):
    """
    Convert two local New York datetimes (possibly on different days)
    to UTC epoch timestamps.

    Parameters:
        start_year, start_month, start_day, start_hour (int): Start date/time components (NY local)
        end_year, end_month, end_day, end_hour (int): End date/time components (NY local)
        start_minute, end_minute (int): Optional minute values

    Returns:
        tuple[int, int]: (start_t, end_t) as UTC epoch timestamps
    """
    ny_tz = ZoneInfo("America/New_York")

    # Local NY datetime objects
    start_local = datetime(start_year, start_month, start_day, start_hour, start_minute, tzinfo=ny_tz)
    end_local   = datetime(end_year, end_month, end_day, end_hour, end_minute, tzinfo=ny_tz)

    # Convert to UTC epoch
    start_t = int(start_local.timestamp())
    end_t   = int(end_local.timestamp())

    return start_t, end_t

def run(
    event_ticker: str = DEFAULT_EVENT_TICKER,
    now_utc: Optional[datetime] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    granularity: Optional[int] = None,
) -> None:
    now_utc = now_utc or datetime.now(timezone.utc)
    client = KalshiClient()

    markets_df = get_event_markets(event_ticker, client)
    if markets_df.empty:
        print("No markets found.")
        return

    times_df = build_times_df(markets_df, now_utc)
    ticker_df = fetch_all_candlesticks(
        times_df,
        client,
        override_start_ts=start_ts,
        override_end_ts=end_ts,
        override_granularity=granularity,
    )
    if ticker_df.empty:
        print("No candlesticks found.")
        return

    ranking_df = build_ranking(ticker_df)

    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        team_map = load_team_lookup(session)
        ticker_df = attach_team_ids(ticker_df, team_map)
        ranking_df = attach_team_ids(ranking_df, team_map)

        save_chances(session, ticker_df, event_ticker=event_ticker)
        save_rankings(session, ranking_df, event_ticker=event_ticker, as_of=now_utc)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch Kalshi data and store in worldcup.db")
    parser.add_argument("--event-ticker", default=DEFAULT_EVENT_TICKER)
    parser.add_argument("--start-ts", type=int, default=None, help="UTC epoch start timestamp")
    parser.add_argument("--end-ts", type=int, default=None, help="UTC epoch end timestamp")
    parser.add_argument("--granularity", type=int, default=None, help="Candlestick interval in minutes")
    args = parser.parse_args()

    start_t_, end_t_ = local_to_utc_epoch_range(
    2025, 12, 1, 0,   # start: Nov 11, 2025 7 PM NY time
    2026, 1, 16, 21    # end:   Nov 12, 2025 1 AM NY time
    )

    run(
        event_ticker=args.event_ticker,
        start_ts=start_t_,
        end_ts=end_t_,
        granularity=args.granularity,
    )

    # run(
    #     event_ticker=args.event_ticker,
    #     start_ts=args.start_ts,
    #     end_ts=args.end_ts,
    #     granularity=args.granularity,
    # )
