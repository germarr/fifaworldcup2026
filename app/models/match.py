from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field


class Match(SQLModel, table=True):
    __tablename__ = "matches"

    id: Optional[int] = Field(default=None, primary_key=True)
    match_number: int = Field(unique=True, index=True)  # 1-104
    round: str = Field(index=True)  # group_stage, round_of_32, round_of_16, quarter_final, semi_final, third_place, final
    group_letter: Optional[str] = Field(default=None, index=True)  # For group stage only

    # Teams (nullable for future knockout matches)
    home_team_id: Optional[int] = Field(default=None, foreign_key="fifa_teams.id")
    away_team_id: Optional[int] = Field(default=None, foreign_key="fifa_teams.id")

    # Bracket slot positions (e.g., "1A", "2B", "3rd_1")
    home_slot: Optional[str] = Field(default=None)
    away_slot: Optional[str] = Field(default=None)

    # Venue
    stadium_id: Optional[int] = Field(default=None, foreign_key="stadiums.id")
    scheduled_datetime: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Actual results (filled by admin)
    actual_home_score: Optional[int] = Field(default=None)
    actual_away_score: Optional[int] = Field(default=None)
    actual_winner_team_id: Optional[int] = Field(default=None, foreign_key="fifa_teams.id")  # For knockout

    # Status
    status: str = Field(default="scheduled")  # scheduled, in_progress, completed

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
