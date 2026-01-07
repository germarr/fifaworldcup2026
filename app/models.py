from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class UserTeamMembership(SQLModel, table=True):
    """Junction table for many-to-many relationship between users and player teams."""
    __tablename__ = "user_team_memberships"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    player_team_id: int = Field(foreign_key="player_teams.id", index=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="team_memberships")
    player_team: Optional["PlayerTeam"] = Relationship(back_populates="memberships")


class PlayerTeam(SQLModel, table=True):
    """Team for players (users) to join and compete."""
    __tablename__ = "player_teams"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    join_code: str = Field(unique=True, index=True, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    members: List["User"] = Relationship(back_populates="player_team")  # DEPRECATED: Keep for backward compatibility
    memberships: List["UserTeamMembership"] = Relationship(back_populates="player_team")  # NEW: Many-to-many

    @property
    def total_points(self) -> int:
        """Sum of all members' points."""
        # Use new memberships relationship if it has data, fallback to old members
        if self.memberships:
            return sum(membership.user.total_points for membership in self.memberships)
        return sum(member.total_points for member in self.members)


class User(SQLModel, table=True):
    """User model for authentication and profile."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    password_hash: str = Field(max_length=255)

    # NEW: Profile fields
    email: Optional[str] = Field(default=None, unique=True, index=True, max_length=255)  # Will be required after migration
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)

    # DEPRECATED: Keep for backward compatibility during migration
    favorite_team: Optional[str] = Field(default=None, max_length=100)

    # NEW: Favorite team as FK to Team table
    favorite_team_id: Optional[int] = Field(default=None, foreign_key="teams.id")

    cookie_consent: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Avatar and scoring
    avatar_seed: str = Field(default="adventurer", max_length=50) # For DiceBear avatar
    total_points: int = Field(default=0)

    # DEPRECATED: Player Team (single team - keep for backward compatibility)
    player_team_id: Optional[int] = Field(default=None, foreign_key="player_teams.id")
    player_team: Optional[PlayerTeam] = Relationship(back_populates="members")

    # Relationships
    predictions: list["Prediction"] = Relationship(back_populates="user")
    sessions: list["Session"] = Relationship(back_populates="user")
    team_memberships: List["UserTeamMembership"] = Relationship(back_populates="user")  # NEW: Many-to-many
    favorite_team_obj: Optional["Team"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[User.favorite_team_id]", "uselist": False}
    )


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
    group_standings: list["GroupStanding"] = Relationship(back_populates="team")


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


class GroupStanding(SQLModel, table=True):
    """Actual group standings data (seeded for now)."""
    __tablename__ = "group_standings"

    id: Optional[int] = Field(default=None, primary_key=True)
    group_letter: str = Field(max_length=1)
    team_id: int = Field(foreign_key="teams.id")
    played: int = Field(default=0)
    won: int = Field(default=0)
    drawn: int = Field(default=0)
    lost: int = Field(default=0)
    goals_for: int = Field(default=0)
    goals_against: int = Field(default=0)
    goal_difference: int = Field(default=0)
    points: int = Field(default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    team: Optional[Team] = Relationship(back_populates="group_standings")


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