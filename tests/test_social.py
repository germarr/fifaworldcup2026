
import pytest
from sqlmodel import Session, select
from app.models import User, PlayerTeam, UserTeamMembership, Team
from app.auth import hash_password

def test_update_profile(client, session, user_token):
    # Create a favorite team to link to
    fav_team = Team(name="Argentina", code="ARG", group="C")
    session.add(fav_team)
    session.commit()

    client.cookies.set("session_token", user_token)
    
    # Test updating profile
    response = client.post(
        "/settings/profile",
        data={
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "favorite_team_id": fav_team.id
        },
        follow_redirects=False # We expect a redirect
    )
    
    assert response.status_code == 303
    
    # Verify updates in DB
    user = session.exec(select(User).where(User.username == "testuser")).first()
    assert user.email == "test@example.com"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.favorite_team_id == fav_team.id

def test_update_profile_invalid_email(client, user_token):
    client.cookies.set("session_token", user_token)
    
    response = client.post(
        "/settings/profile",
        data={
            "email": "invalid-email",
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "error=invalid_email" in response.headers["location"]

def test_create_team(client, session, user_token):
    client.cookies.set("session_token", user_token)
    
    team_name = "Best Team"
    response = client.post(
        "/settings/team/create",
        data={"team_name": team_name},
        follow_redirects=False
    )
    
    assert response.status_code == 303
    
    # Verify team created
    team = session.exec(select(PlayerTeam).where(PlayerTeam.name == team_name)).first()
    assert team is not None
    assert team.join_code is not None
    
    # Verify user joined team
    user = session.exec(select(User).where(User.username == "testuser")).first()
    membership = session.exec(select(UserTeamMembership).where(
        UserTeamMembership.user_id == user.id,
        UserTeamMembership.player_team_id == team.id
    )).first()
    assert membership is not None

def test_join_team(client, session, user_token):
    # Create a team first (by another user ideally, but we can just insert it)
    team = PlayerTeam(name="Another Team", join_code="ABCDEF")
    session.add(team)
    session.commit()
    
    client.cookies.set("session_token", user_token)
    
    response = client.post(
        "/settings/team/join",
        data={"join_code": "ABCDEF"},
        follow_redirects=False
    )
    
    assert response.status_code == 303
    assert "success=team_joined" in response.headers["location"]
    
    # Verify membership
    user = session.exec(select(User).where(User.username == "testuser")).first()
    membership = session.exec(select(UserTeamMembership).where(
        UserTeamMembership.user_id == user.id,
        UserTeamMembership.player_team_id == team.id
    )).first()
    assert membership is not None

def test_join_team_invalid_code(client, user_token):
    client.cookies.set("session_token", user_token)
    
    response = client.post(
        "/settings/team/join",
        data={"join_code": "INVALID"},
        follow_redirects=False
    )
    
    assert response.status_code == 303
    assert "error=invalid_code" in response.headers["location"]

def test_leave_team(client, session, user_token):
    # Setup user in a team
    team = PlayerTeam(name="Leavers Team", join_code="LEAVE1")
    session.add(team)
    session.commit()
    
    user = session.exec(select(User).where(User.username == "testuser")).first()
    membership = UserTeamMembership(user_id=user.id, player_team_id=team.id)
    session.add(membership)
    session.commit()
    
    client.cookies.set("session_token", user_token)
    
    response = client.post(
        f"/settings/team/leave/{team.id}",
        follow_redirects=False
    )
    
    assert response.status_code == 303
    assert "success=left_team" in response.headers["location"]
    
    # Verify membership removed
    membership = session.exec(select(UserTeamMembership).where(
        UserTeamMembership.user_id == user.id,
        UserTeamMembership.player_team_id == team.id
    )).first()
    assert membership is None

def test_team_scoring(session):
    # Create users
    user1 = User(username="u1", password_hash="hash", total_points=10)
    user2 = User(username="u2", password_hash="hash", total_points=20)
    user3 = User(username="u3", password_hash="hash", total_points=5) # Not in team
    session.add_all([user1, user2, user3])
    session.commit()
    
    # Create team
    team = PlayerTeam(name="Scoring Team", join_code="SCORE1")
    session.add(team)
    session.commit()
    
    # Add members
    m1 = UserTeamMembership(user_id=user1.id, player_team_id=team.id)
    m2 = UserTeamMembership(user_id=user2.id, player_team_id=team.id)
    session.add_all([m1, m2])
    session.commit()
    
    session.refresh(team)
    
    # Check total points (10 + 20 = 30)
    assert team.total_points == 30
