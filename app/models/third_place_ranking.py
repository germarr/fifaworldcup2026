from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class UserThirdPlaceRanking(SQLModel, table=True):
    __tablename__ = "user_third_place_rankings"
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="unique_user_team_ranking"),
        UniqueConstraint("user_id", "rank_position", name="unique_user_rank_position"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    team_id: int = Field(foreign_key="fifa_teams.id")
    rank_position: int  # 1-12, where 1-8 qualify for knockout

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
