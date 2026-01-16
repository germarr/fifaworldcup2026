from sqlmodel import SQLModel, Session, create_engine
from .config import DATABASE_URL

# Create engine with SQLite
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)
    _ensure_prediction_bracket_id()


def _ensure_prediction_bracket_id():
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info(predictions)").fetchall()
        columns = {row[1] for row in result}
        if "bracket_id" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE predictions ADD COLUMN bracket_id INTEGER REFERENCES brackets(id)"
            )


def get_session():
    """Dependency for getting database sessions."""
    with Session(engine) as session:
        yield session
