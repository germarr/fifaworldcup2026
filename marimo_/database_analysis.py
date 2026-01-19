import marimo

__generated_with = "0.19.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import sqlmodel

    DATABASE_URL = "sqlite:///./worldcup.db"
    engine = sqlmodel.create_engine(DATABASE_URL)
    return (engine,)


@app.cell
def _():
    import pandas as pd
    data_ = pd.read_csv('../app/core_files/matches.csv', index_col=0)
    data_['scheduled_datetime'] = pd.to_datetime(data_['scheduled_datetime'], format='mixed')

    data_.to_csv("../app/core_files/matches.csv")
    return (pd,)


@app.cell
def _(engine, mo):
    df_stadiums = mo.sql(f"""
    SELECT *
    FROM fifa_teams
    """, engine=engine)

    df_stadiums
    return (df_stadiums,)


@app.cell
def _():
    import asyncio
    import requests
    import time
    import duckdb
    import json
    # from user_balance import check_balance
    from sqlmodel import create_engine, Session,select,text,SQLModel
    from typing import Optional, Dict, Any, List
    # from kalshi_scripts import get_all_kalshi_markets
    from datetime import datetime, timedelta, timezone
    import pytz
    from zoneinfo import ZoneInfo

    # from models import Categories, Series, Tags, CatAndTags
    import numpy as np

    import plotly.graph_objects as go
    import altair as alt
    import matplotlib.pyplot as plt
    from itertools import cycle
    import matplotlib.dates as mdates
    return Any, Dict, Optional, ZoneInfo, alt, datetime, np, requests, timezone


@app.cell
def _(Any, Dict, Optional, requests):
    def get_kalshi_markets(limit: Optional[int] = None,cursor: Optional[str] = None,event_ticker: Optional[str] = None,series_ticker: Optional[str] = None,max_close_ts: Optional[int] = None,min_close_ts: Optional[int] = None,status: Optional[str] = None,tickers: Optional[str] = None) -> Dict[str, Any]:
        url = "https://api.elections.kalshi.com/trade-api/v2/markets"
        headers = {"accept": "application/json"}

        params = {
            "limit": limit,
            "cursor": cursor,
            "event_ticker": event_ticker,
            "series_ticker": series_ticker,
            "max_close_ts": max_close_ts,
            "min_close_ts": min_close_ts,
            "status": status,
            "tickers": tickers
        }

        params = {k: v for k, v in params.items() if v is not None}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise RuntimeError(f"API request failed with status {response.status_code}: {response.text}")

        return response.json()

    # aa = get_kalshi_markets()
    return (get_kalshi_markets,)


@app.cell
def get_series_information(pd, requests):
    def get_series_information(nameOfSeries:str = 'kxnflgame'):
        series_ticker=nameOfSeries.upper()
        url = f"https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}"

        response = requests.get(url)

        data_dict = response.json()['series']

        # data_dict = json.loads(json_data)
        # Converting the JSON data into a pandas DataFrame
        additional_prohibitions_df = pd.DataFrame([{"additional_prohibition":" ".join([i for i in data_dict['additional_prohibitions']])}])
        product_metadata_df = pd.json_normalize(data_dict['product_metadata'])
        settlement_sources_df = pd.json_normalize(data_dict['settlement_sources'])

        # Joining the DataFrames into a single DataFrame
        final_df = pd.concat([additional_prohibitions_df,
                              product_metadata_df,
                              settlement_sources_df], axis=1)

        final_df['category'] = data_dict['category']
        final_df['contract_terms_url'] = data_dict['contract_terms_url']
        final_df['contract_url'] = data_dict['contract_url']
        final_df['fee_multiplier'] = data_dict['fee_multiplier']
        final_df['fee_type'] = data_dict['fee_type']
        final_df['frequency'] = data_dict['frequency']
        final_df['series_tags'] = ', '.join(data_dict['tags'])
        final_df['series_ticker'] = data_dict['ticker']
        final_df['series_title'] = data_dict['title']

        return final_df

    # gre = get_series_information(nameOfSeries = 'kxmenworldcup')
    return


@app.cell
def _(ZoneInfo, datetime, np, pd, requests, timezone):
    def add_time_features(df, current_time_utc=None,open_col='open_time', close_col='close_time'):
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

    def add_span_capped_granularity(df,max_days_minute=3, max_days_hour=55):
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

    def minutes_to_df(records, local_tz=None):
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

    def get_exchange_data(start_ts:int, end_ts:int, series_ticker:str, ticker:str, minutes:int=60):
        url = f"https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}/markets/{ticker}/candlesticks?start_ts={start_ts}&end_ts={end_ts}&period_interval={minutes}"

        headers = {"accept": "application/json"}

        responsea = requests.get(url, headers=headers)

        data = responsea.json()

        return data

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
    return (
        add_phase_and_granularity,
        add_span_capped_granularity,
        add_time_features,
        get_exchange_data,
        local_to_utc_epoch_range,
        minutes_to_df,
    )


@app.cell
def _(pd, requests):
    def get_eventmarkets_ticker_lo(event_t: str):
        event_ticker = event_t.upper()
        # series_ticker_upper = series_ticker_upper.upper()

        url = f"https://api.elections.kalshi.com/trade-api/v2/events/{event_ticker}"
        response = requests.get(url).json()

        eventinfo = response.get('event')
        eventmarkets = response.get('markets')

        om = pd.concat([pd.DataFrame([m]) for m in eventmarkets])

        om['open_time'] = pd.to_datetime(om['open_time'])
        om['close_time'] = pd.to_datetime(om['expected_expiration_time'])

        om['start_ts'] = om['open_time'].apply(lambda x: int(x.timestamp()))
        om['end_ts']   = om['close_time'].apply(lambda x: int(x.timestamp()))

        om['local_open_time']  = om['open_time'].dt.tz_convert('America/New_York').dt.tz_localize(None)
        om['local_close_time'] = om['close_time'].dt.tz_convert('America/New_York').dt.tz_localize(None)

        om['series_ticker']   = eventinfo.get('series_ticker').upper()
        om['category']        = eventinfo.get('category')
        om['event_title']     = eventinfo.get('title')
        om['event_sub_title'] = eventinfo.get('sub_title')

        ticker_lo = om[
            [
                'category', 'event_title', 'event_sub_title', 'yes_sub_title',
                'series_ticker', 'event_ticker', 'ticker',
                'start_ts', 'open_time', 'close_time',
                'local_open_time', 'local_close_time', 'end_ts'
            ]
        ].drop_duplicates()

        ticker_lo['start_date'] = ticker_lo['local_open_time'].dt.date
        ticker_lo['end_date']   = ticker_lo['local_close_time'].dt.date

        return ticker_lo

    fr = get_eventmarkets_ticker_lo('kxmenworldcup-26')
    return (get_eventmarkets_ticker_lo,)


@app.cell
def _(
    add_phase_and_granularity,
    add_span_capped_granularity,
    add_time_features,
    datetime,
    get_eventmarkets_ticker_lo,
    timezone,
):
    ## Create Dictionary with times 
    ticker_ = 'kxmenworldcup-26'
    current_time_utc = datetime.now(timezone.utc)
    tickerall_data = get_eventmarkets_ticker_lo(ticker_)

    times_df = tickerall_data[['ticker','event_ticker','series_ticker','start_ts','end_ts','open_time','close_time','yes_sub_title','event_title']].copy()
    times_df['current_time'] = current_time_utc
    times_df['current_ts'] = int(current_time_utc.timestamp())

    times_df = times_df[['yes_sub_title','event_title','ticker','event_ticker','series_ticker','start_ts','end_ts','current_ts','open_time','close_time','current_time']].copy()

    times_df = add_time_features(df = times_df)
    times_df = add_phase_and_granularity(times_df)
    times_df = add_span_capped_granularity(times_df,max_days_minute=3,max_days_hour=7)
    return ticker_, times_df


@app.cell
def _(get_exchange_data, minutes_to_df, times_df):
    ticker_info = times_df.to_dict('records')
    all_ticker_data = []

    for ticker_dict in ticker_info[0:1]:
        exch_data_ = get_exchange_data(start_ts = ticker_dict.get('start_ts'), end_ts = ticker_dict.get('current_ts'), series_ticker = ticker_dict.get('series_ticker'), ticker= ticker_dict.get('ticker'), minutes =ticker_dict.get('granularity_span_cap')) 

        dfa_ = minutes_to_df(exch_data_['candlesticks'], local_tz='America/New_York')
        dfa_['yes_sub_title'] = ticker_dict.get('yes_sub_title')
        dfa_['event_title'] = ticker_dict.get('event_title')
        dfa_['ticker'] = ticker_dict.get('ticker')
        dfa_['series_ticker'] = ticker_dict.get('series_ticker')

        all_ticker_data.append(dfa_)
    return (all_ticker_data,)


@app.cell
def _(all_ticker_data, pd):
    ticker_df = pd.concat(all_ticker_data).copy()
    return


@app.cell
def _(get_exchange_data, minutes_to_df, pd, requests, ticker_):
    def event_ticker_dfv4(startTime:int, endTime:int, graph_minutes:int=1440,event_t:str=ticker_):

        event_ticker = event_t.upper()
        url = f"https://api.elections.kalshi.com/trade-api/v2/events/{event_ticker}"
        response = requests.get(url).json()
        eventinfo = response.get('event')

        eventmarkets = response.get('markets')

        om = pd.concat([pd.DataFrame([i]) for i in eventmarkets])

        om['open_time'] = pd.to_datetime(om['open_time'])
        om['close_time'] = pd.to_datetime(om['expected_expiration_time'])

        om['start_ts'] = om['open_time'].apply(lambda x: int(x.timestamp()))
        om['end_ts'] = om['close_time'].apply(lambda x: int(x.timestamp()))

        om['local_open_time'] = om['open_time'].dt.tz_convert('America/New_York').dt.tz_localize(None)
        om['local_close_time'] = om['close_time'].dt.tz_convert('America/New_York').dt.tz_localize(None)

        om['category'] = eventinfo.get('category')
        om['event_title'] = eventinfo.get('title')
        om['event_sub_title'] = eventinfo.get('sub_title')
        om['series_ticker'] = eventinfo.get('series_ticker').upper()

        ticker_lo = om[['category','event_title','event_sub_title','yes_sub_title','series_ticker','event_ticker','ticker','start_ts','open_time','close_time','local_open_time','local_close_time','end_ts']].drop_duplicates()

        ticker_lo['start_date'] = ticker_lo['local_open_time'].dt.date
        ticker_lo['end_date'] = ticker_lo['local_close_time'].dt.date

        ticker_lo_to_dict = ticker_lo.to_dict('records')

        events_list_ = []

        for eventT in ticker_lo_to_dict:

            exch_data_ = get_exchange_data(start_ts=startTime, end_ts=endTime, series_ticker=eventT['series_ticker'], ticker=eventT['ticker'], minutes=graph_minutes) #1 ,60, 1440

            try:
                dfa_ = minutes_to_df(exch_data_['candlesticks'], local_tz='America/New_York')
                dfa_['yes_sub_title'] = eventT['yes_sub_title']
                events_list_.append(dfa_)
                print(eventT['yes_sub_title']," ",eventT['series_ticker']," ",eventT['ticker'])
            except:
                None



        full_event_results = pd.concat(events_list_).reset_index(drop=True)

        return ticker_lo,full_event_results
    return (event_ticker_dfv4,)


@app.cell
def _(alt, get_exchange_data, local_to_utc_epoch_range, minutes_to_df):
    start_t1_, end_t1_ = local_to_utc_epoch_range(
        2025, 6, 1, 0,   # start: Nov 11, 2025 7 PM NY time
        2026, 1, 16, 21    # end:   Nov 12, 2025 1 AM NY time
    )

    exch_data_0 = get_exchange_data(start_ts=start_t1_, end_ts=end_t1_, series_ticker='KXMENWORLDCUP', ticker='KXMENWORLDCUP-26-FR', minutes=1440)

    dfa_0 = minutes_to_df(exch_data_0['candlesticks'], local_tz='America/New_York')
    dfa_0['yes_sub_title'] = 'France'

    # dfa_0a = dfa_0.query('yes_sub_title == "France"').loc[full_event_results['end_period_local'] >= '2025-11-21T19:00:00.000']

    y_min = dfa_0['yes_bid_close'].min()
    y_max = dfa_0['yes_bid_close'].max()

    chart = alt.Chart(dfa_0).mark_line().encode(
        x='end_period_local:T',
        y=alt.Y('yes_bid_close:Q', scale=alt.Scale(domain=[y_min-1, y_max + (y_max - y_min) * 0.05])),
        tooltip=['end_period_local:T', 'yes_bid_close:Q'],
        color=alt.value('blue')
    ).properties(
        title='Volume Over Time for Above 82',
        width=800,
        height=400
    ).interactive()

    chart
    return (dfa_0,)


@app.cell
def _(dfa_0):
    dfa_0
    return


@app.cell
def _(event_ticker_dfv4, local_to_utc_epoch_range):
    start_t_, end_t_ = local_to_utc_epoch_range(
        2025, 12, 1, 0,   # start: Nov 11, 2025 7 PM NY time
        2026, 1, 16, 21    # end:   Nov 12, 2025 1 AM NY time
    )

    ticker_lo,full_event_results = event_ticker_dfv4(start_t_, end_t_, graph_minutes= 1440)
    return (full_event_results,)


@app.cell
def _(full_event_results):
    full_event_results.query('yes_sub_title == "France"')
    return


@app.cell
def _(alt, full_event_results):
    dfa = full_event_results.query('yes_sub_title == "Memphis"').loc[full_event_results['end_period_local'] >= '2025-11-21T19:00:00.000']

    chart = alt.Chart(dfa).mark_line().encode(
        x='end_period_local:T',
        y='yes_bid_close:Q',
        tooltip=['end_period_local:T', 'yes_bid_close:Q'],
        color=alt.value('blue')
    ).properties(
        title='Volume Over Time for Above 82',
        width=800,
        height=400
    ).interactive()

    chart
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #1. General Information

    This is informal knowldege that I'm gathering while working  with Kalshi's  API.
    There are 3 types of 'tickers' in Kalshi. In order of hierarchy, there are Series, Events and markets.

    A Series is composed of mulitple events and an event is composed of multiple markets. In a practical example all NFL season games are part of the '...' series.

    A particular match is the event and the market is one of the teams.

    When purchasing a contract your purchasing a contract for the market.
    """)
    return


@app.cell
def _(get_kalshi_markets):
    aaa = get_kalshi_markets(series_ticker='kxmenworldcup'.upper())
    #https://kalshi.com/markets/kxwcgroupqual/world-cup-group-qualifiers/kxwcgroupqual-26g

    #https://kalshi.com/markets/kxmenworldcup/mens-world-cup-winner/kxmenworldcup-26

    #https://kalshi.com/sports/soccer/fifa-world-cup/group-winner

    #https://kalshi.com/markets/kxwcgroupwin/world-cup-group-winner/kxwcgroupwin-26c

    return (aaa,)


@app.cell
def _(aaa, pd):
    column_names = ['title', 'ticker', 'yes_sub_title', 'no_sub_title', 'volume','volume_24h','liquidity','liquidity_dollars','open_interest','rules_primary','no_ask_dollars','yes_ask_dollars']

    pd.DataFrame(aaa['markets'])\
        .sort_values('volume',ascending=False)[column_names]
    return


@app.cell
def _(get_eventmarkets_ticker_lo):
    ticker_data = get_eventmarkets_ticker_lo('KXMENWORLDCUP-26-FR')

    ticker_data
    return


@app.cell
def _(aaa, df_stadiums, pd):
    countries_in_k = pd.DataFrame(aaa['markets'])[['yes_sub_title','no_ask']].drop_duplicates()



    countries_in_k\
        .merge(df_stadiums,left_on='yes_sub_title',right_on='name', how='left')
    return


@app.cell
def _(aaa):
    aaa
    return


@app.cell
def _(pd, requests):
    def get_series_information(nameOfSeries:str = 'kxnflgame'):
        series_ticker=nameOfSeries.upper()
        url = f"https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}"

        response = requests.get(url)

        data_dict = response.json()['series']

        # data_dict = json.loads(json_data)
        # Converting the JSON data into a pandas DataFrame
        additional_prohibitions_df = pd.DataFrame([{"additional_prohibition":" ".join([i for i in data_dict['additional_prohibitions']])}])
        product_metadata_df = pd.json_normalize(data_dict['product_metadata'])
        settlement_sources_df = pd.json_normalize(data_dict['settlement_sources'])

        # Joining the DataFrames into a single DataFrame
        final_df = pd.concat([additional_prohibitions_df,
                              product_metadata_df,
                              settlement_sources_df], axis=1)

        final_df['category'] = data_dict['category']
        final_df['contract_terms_url'] = data_dict['contract_terms_url']
        final_df['contract_url'] = data_dict['contract_url']
        final_df['fee_multiplier'] = data_dict['fee_multiplier']
        final_df['fee_type'] = data_dict['fee_type']
        final_df['frequency'] = data_dict['frequency']
        final_df['series_tags'] = ', '.join(data_dict['tags'])
        final_df['series_ticker'] = data_dict['ticker']
        final_df['series_title'] = data_dict['title']

        return final_df

    return


@app.cell
def _(pd):
    pd.read_csv('../data_add/data.csv')\
        .query('yes_sub_title == "France"')\
        .sort_values(by='end_period_local')\
        [['yes_sub_title','end_period_local','event_title','ticker','series_ticker','yes_bid_open']]
    return


@app.cell
def _(pd):
    pd.read_csv('../data_add/data.csv')\
        [['yes_sub_title','end_period_local','event_title','ticker','series_ticker','yes_bid_open']]\
        .groupby(['yes_sub_title'])\
        .agg(avg_chance = ('yes_bid_open','mean'))\
        .reset_index()\
        .assign(avg_chance=lambda df: df['avg_chance'].round(2))\
        .sort_values(by='avg_chance', ascending=False)\
        .reset_index(drop=True)\
        .reset_index()\
        .rename(columns={'index': 'rank'})\
        .assign(rank=lambda df: df['rank'] + 1)
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
