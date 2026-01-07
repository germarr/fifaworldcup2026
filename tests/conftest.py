import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app
from app.database import get_session
from app.models import User, Team, Match

# Create in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="user_token")
def user_token_fixture(session: Session):
    """Create a test user and return a valid session token."""
    from app.auth import hash_password
    from app.models import Session as UserSession
    from datetime import datetime, timedelta, timezone
    import secrets

    user = User(
        username="testuser",
        password_hash=hash_password("password123"),
        favorite_team="Brazil",
        cookie_consent=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = secrets.token_urlsafe(32)
    user_session = UserSession(
        user_id=user.id,
        session_token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    session.add(user_session)
    session.commit()

    return token
