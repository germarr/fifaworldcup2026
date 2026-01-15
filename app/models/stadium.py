from typing import Optional
from sqlmodel import SQLModel, Field


class Stadium(SQLModel, table=True):
    __tablename__ = "stadiums"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    city: str
    country: str
