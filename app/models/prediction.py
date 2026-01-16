from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class Prediction(SQLModel, table=True):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="unique_user_match"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    bracket_id: Optional[int] = Field(default=None, foreign_key="brackets.id", index=True)
    match_id: int = Field(foreign_key="matches.id", index=True)

    # Prediction
    predicted_outcome: str  # home_win, away_win, draw
    predicted_winner_team_id: Optional[int] = Field(default=None, foreign_key="fifa_teams.id")  # For knockout
    predicted_home_score: Optional[int] = Field(default=None)
    predicted_away_score: Optional[int] = Field(default=None)

    # Points (calculated after match completes)
    points_earned: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
