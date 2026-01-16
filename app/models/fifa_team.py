from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field


class FifaTeam(SQLModel, table=True):
    __tablename__ = "fifa_teams"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    country_code: Optional[str] = Field(default=None)  # ISO 3166-1 alpha-3
    flag_emoji: Optional[str] = Field(default=None)
    group_letter: Optional[str] = Field(default=None, index=True)  # A-L
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
