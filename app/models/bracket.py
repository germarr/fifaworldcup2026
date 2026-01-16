from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class Bracket(SQLModel, table=True):
    __tablename__ = "brackets"
    __table_args__ = (UniqueConstraint("user_id", name="unique_user_bracket"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
