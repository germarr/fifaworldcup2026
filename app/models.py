from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship


class User(SQLModel, table=True):
    """User model for authentication and profile."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    password_hash: str = Field(max_length=255)
    favorite_team: str = Field(max_length=100)
    cookie_consent: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    predictions: list["Prediction"] = Relationship(back_populates="user")
    sessions: list["Session"] = Relationship(back_populates="user")


class Session(SQLModel, table=True):
    """Session model for user authentication."""
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    session_token: str = Field(unique=True, index=True, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

    # Relationships
    user: Optional[User] = Relationship(back_populates="sessions")


class Team(SQLModel, table=True):
    """Team model for World Cup teams."""
    __tablename__ = "teams"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=100)
    code: str = Field(unique=True, max_length=3)  # e.g., "BRA", "ARG"
    group: Optional[str] = Field(default=None, max_length=1)  # e.g., "A", "B", etc.
    flag_url: Optional[str] = Field(default=None, max_length=255)

    # Relationships
    home_matches: list["Match"] = Relationship(
        back_populates="team1",
        sa_relationship_kwargs={"foreign_keys": "Match.team1_id"}
    )
    away_matches: list["Match"] = Relationship(
        back_populates="team2",
        sa_relationship_kwargs={"foreign_keys": "Match.team2_id"}
    )


class Match(SQLModel, table=True):
    """Match model for World Cup matches."""
    __tablename__ = "matches"

    id: Optional[int] = Field(default=None, primary_key=True)
    round: str = Field(max_length=50)  # "Group Stage", "Round of 16", etc.
    match_number: int
    team1_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    team2_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    team1_placeholder: Optional[str] = Field(default=None, max_length=10)  # e.g., "1A", "W49"
    team2_placeholder: Optional[str] = Field(default=None, max_length=10)  # e.g., "2B", "W50"
    match_date: datetime
    actual_team1_score: Optional[int] = Field(default=None)
    actual_team2_score: Optional[int] = Field(default=None)
    is_finished: bool = Field(default=False)

    # Relationships
    team1: Optional[Team] = Relationship(
        back_populates="home_matches",
        sa_relationship_kwargs={"foreign_keys": "Match.team1_id"}
    )
    team2: Optional[Team] = Relationship(
        back_populates="away_matches",
        sa_relationship_kwargs={"foreign_keys": "Match.team2_id"}
    )
    predictions: list["Prediction"] = Relationship(back_populates="match")


class Prediction(SQLModel, table=True):
    """Prediction model for user match predictions."""
    __tablename__ = "predictions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    match_id: int = Field(foreign_key="matches.id")
    predicted_team1_score: int
    predicted_team2_score: int
    predicted_winner_id: Optional[int] = Field(default=None, foreign_key="teams.id")
    penalty_shootout_winner_id: Optional[int] = Field(default=None, foreign_key="teams.id")  # For tied knockout matches
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional[User] = Relationship(back_populates="predictions")
    match: Optional[Match] = Relationship(back_populates="predictions")
