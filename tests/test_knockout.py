from datetime import datetime
from app.models import Team, Match, Prediction
from app.knockout import resolve_knockout_teams

def test_resolve_knockout_teams_progression(session):
    # Setup Teams
    team_a = Team(name="Team A", code="AAA", group="A")
    team_b = Team(name="Team B", code="BBB", group="B")
    team_c = Team(name="Team C", code="CCC", group="C")
    team_d = Team(name="Team D", code="DDD", group="D")
    
    session.add_all([team_a, team_b, team_c, team_d])
    session.commit()
    
    # Setup Matches
    # Match 1: A vs B (Semis)
    match1 = Match(
        round="Semi-Final", 
        match_number=1, 
        team1_id=team_a.id, 
        team2_id=team_b.id,
        match_date=datetime.now()
    )
    # Match 2: C vs D (Semis)
    match2 = Match(
        round="Semi-Final", 
        match_number=2, 
        team1_id=team_c.id, 
        team2_id=team_d.id,
        match_date=datetime.now()
    )
    # Match 3: W1 vs W2 (Final) - using placeholders
    match3 = Match(
        round="Final", 
        match_number=3, 
        team1_placeholder="W1", 
        team2_placeholder="W2",
        match_date=datetime.now()
    )
    
    session.add_all([match1, match2, match3])
    session.commit()
    
    user_id = 999
    
    # User Predictions
    # Predict A beats B
    pred1 = Prediction(
        user_id=user_id, 
        match_id=match1.id, 
        predicted_team1_score=2, 
        predicted_team2_score=1
    )
    # Predict C beats D
    pred2 = Prediction(
        user_id=user_id, 
        match_id=match2.id, 
        predicted_team1_score=1, 
        predicted_team2_score=0
    )
    
    session.add_all([pred1, pred2])
    session.commit()
    
    # Resolve
    resolution = resolve_knockout_teams(user_id, session)
    
    # Check if W1 resolves to Team A
    assert resolution["W1"].id == team_a.id
    # Check if W2 resolves to Team C
    assert resolution["W2"].id == team_c.id
    
    # Check Losers
    assert resolution["L1"].id == team_b.id
    assert resolution["L2"].id == team_d.id

def test_resolve_knockout_teams_penalty_winner(session):
    # Setup Teams
    team_e = Team(name="Team E", code="EEE", group="E")
    team_f = Team(name="Team F", code="FFF", group="F")
    
    session.add_all([team_e, team_f])
    session.commit()
    
    match4 = Match(
        round="Quarter", 
        match_number=4, 
        team1_id=team_e.id, 
        team2_id=team_f.id,
        match_date=datetime.now()
    )
    session.add(match4)
    session.commit()
    
    user_id = 888
    
    # Predict Draw 1-1, but Team F wins penalties
    pred4 = Prediction(
        user_id=user_id, 
        match_id=match4.id, 
        predicted_team1_score=1, 
        predicted_team2_score=1,
        penalty_shootout_winner_id=team_f.id
    )
    session.add(pred4)
    session.commit()
    
    resolution = resolve_knockout_teams(user_id, session)
    
    assert resolution["W4"].id == team_f.id
    assert resolution["L4"].id == team_e.id

def test_resolve_knockout_teams_no_prediction(session):
    # Setup Teams
    team_g = Team(name="Team G", code="GGG", group="G")
    team_h = Team(name="Team H", code="HHH", group="H")
    session.add_all([team_g, team_h])
    session.commit()
    
    match5 = Match(
        round="Round 16", 
        match_number=5, 
        team1_id=team_g.id, 
        team2_id=team_h.id,
        match_date=datetime.now()
    )
    session.add(match5)
    session.commit()
    
    user_id = 777
    # No prediction for match 5
    
    resolution = resolve_knockout_teams(user_id, session)
    
    # Should be None if not predicted
    assert resolution["W5"] is None
    assert resolution["L5"] is None
