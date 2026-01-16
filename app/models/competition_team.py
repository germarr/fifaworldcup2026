from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field


class CompetitionTeam(SQLModel, table=True):
    __tablename__ = "competition_teams"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    admin_user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TeamMembership(SQLModel, table=True):
    __tablename__ = "team_memberships"

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="competition_teams.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
