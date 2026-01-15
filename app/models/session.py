from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_token: str = Field(unique=True, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
