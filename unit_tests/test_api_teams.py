import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.user import User
from app.models.competition_team import CompetitionTeam
from app.dependencies import get_current_user, require_user
from main import app

def create_user(session: Session, email: str = "test@example.com") -> User:
    user = User(
        email=email,
        display_name="Test User",
        password_hash="hashed_secret",
        is_admin=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def test_create_team(client: TestClient, session: Session):
    user = create_user(session)

    # Override dependency to return this user
    app.dependency_overrides[require_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(
        "/teams/create",
        data={"name": "My New Team"},
        follow_redirects=False
    )

    assert response.status_code == 303
    
    # Check if team was created in DB
    from sqlmodel import select
    from app.models.competition_team import CompetitionTeam
    statement = select(CompetitionTeam).where(CompetitionTeam.name == "My New Team")
    team = session.exec(statement).first()
    
    assert team is not None
    assert team.admin_user_id == user.id

    # Check membership
    from app.models.competition_team import TeamMembership
    statement = select(TeamMembership).where(
        TeamMembership.team_id == team.id,
        TeamMembership.user_id == user.id
    )
    membership = session.exec(statement).first()
    assert membership is not None

def test_join_team(client: TestClient, session: Session):
    owner = create_user(session, "owner@example.com")
    joiner = create_user(session, "joiner@example.com")

    # Create team
    team = CompetitionTeam(name="Open Team", admin_user_id=owner.id)
    session.add(team)
    session.commit()
    session.refresh(team)

    # Override dependency to return joiner
    app.dependency_overrides[require_user] = lambda: joiner
    app.dependency_overrides[get_current_user] = lambda: joiner

    response = client.post(
        f"/teams/{team.id}/join",
        follow_redirects=False
    )

    assert response.status_code == 303

    # Check membership
    from app.models.competition_team import TeamMembership
    from sqlmodel import select
    statement = select(TeamMembership).where(
        TeamMembership.team_id == team.id,
        TeamMembership.user_id == joiner.id
    )
    membership = session.exec(statement).first()
    assert membership is not None
