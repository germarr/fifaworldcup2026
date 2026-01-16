from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field


class Bracket(SQLModel, table=True):
    __tablename__ = "bracket_states"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    is_complete: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
