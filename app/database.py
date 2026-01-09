import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

# Get the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Use absolute path for the SQLite database
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'worldcup.db')}"

# Create engine with check_same_thread=False for SQLite
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    """Create database tables."""
    # Import all models to ensure they are registered with SQLModel
    from app.models import User, Team, Match, Prediction, GroupStanding
    from app.models import Session as SessionModel
    from app.models import PlayerTeam, UserTeamMembership  # NEW: Many-to-many team membership
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session
