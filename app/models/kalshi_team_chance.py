from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class KalshiTeamChance(SQLModel, table=True):
    __tablename__ = "kalshi_team_chances"
    __table_args__ = (
        UniqueConstraint("market_ticker", "end_period_ts", name="uniq_kalshi_market_time"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: Optional[int] = Field(default=None, foreign_key="fifa_teams.id", index=True)
    team_name: str = Field(index=True)
    event_ticker: str = Field(index=True)
    series_ticker: Optional[str] = Field(default=None, index=True)
    market_ticker: str = Field(index=True)
    end_period_ts: int = Field(index=True)
    end_period_utc: datetime
    yes_bid_open: Optional[float] = Field(default=None)
    yes_ask_close: Optional[float] = Field(default=None)
    mid_cents: Optional[float] = Field(default=None)
    volume: Optional[float] = Field(default=None)
    open_interest: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
