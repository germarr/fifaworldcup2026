from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    display_name: str
    is_admin: bool = Field(default=False)
    cookie_consent: bool = Field(default=False)
    favorite_team_id: Optional[int] = Field(default=None, foreign_key="fifa_teams.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
