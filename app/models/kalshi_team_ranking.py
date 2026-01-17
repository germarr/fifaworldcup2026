from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field


class KalshiTeamRanking(SQLModel, table=True):
    __tablename__ = "kalshi_team_rankings"

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: Optional[int] = Field(default=None, foreign_key="fifa_teams.id", index=True)
    team_name: str = Field(index=True)
    event_ticker: str = Field(index=True)
    series_ticker: Optional[str] = Field(default=None)
    avg_yes_bid_open: float = Field(default=0.0)
    rank: int = Field(index=True)
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
