from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class CompetitionTeam(SQLModel, table=True):
    """User-created teams for competing with friends."""
    __tablename__ = "competition_teams"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    admin_user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TeamMembership(SQLModel, table=True):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="unique_team_user"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="competition_teams.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
