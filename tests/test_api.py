from datetime import datetime, timezone
from app.models import Team, Match, Prediction

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_read_matches_empty(client, user_token):
    client.cookies.set("session_token", user_token)
    response = client.get("/api/matches")
    assert response.status_code == 200
    assert response.json() == []

def test_create_and_read_prediction(client, session, user_token):
    # Seed teams and match
    team1 = Team(name="Brazil", code="BRA", group="G")
    team2 = Team(name="Serbia", code="SRB", group="G")
    session.add(team1)
    session.add(team2)
    session.commit()

    match = Match(
        round="Group Stage - Group G",
        match_number=1,
        team1_id=team1.id,
        team2_id=team2.id,
        match_date=datetime.now(timezone.utc),
        is_finished=False
    )
    session.add(match)
    session.commit()

    # Create prediction
    client.cookies.set("session_token", user_token)
    payload = {
        "match_id": match.id,
        "predicted_team1_score": 2,
        "predicted_team2_score": 1
    }
    response = client.post("/api/predictions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_team1_score"] == 2
    assert data["predicted_team2_score"] == 1
    assert data["match_id"] == match.id

    # Read predictions
    response = client.get("/api/predictions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["predicted_team1_score"] == 2

def test_unauthorized_access(client):
    response = client.get("/api/predictions")
    # Should redirect to login or return 401 depending on implementation
    # Based on auth.py, get_current_user might raise HTTPException(401)
    assert response.status_code in [401, 403, 303, 307] 
