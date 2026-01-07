from datetime import datetime, timezone
from app.models import Team, Match, Prediction
from app.standings import calculate_group_standings

def test_calculate_group_standings(session):
    # Setup Teams for Group A
    qatar = Team(name="Qatar", code="QAT", group="A")
    ecuador = Team(name="Ecuador", code="ECU", group="A")
    senegal = Team(name="Senegal", code="SEN", group="A")
    netherlands = Team(name="Netherlands", code="NED", group="A")
    
    session.add_all([qatar, ecuador, senegal, netherlands])
    session.commit()
    
    # Setup Matches
    match1 = Match(round="Group Stage - Group A", match_number=1, team1_id=qatar.id, team2_id=ecuador.id, match_date=datetime.now(timezone.utc))
    match2 = Match(round="Group Stage - Group A", match_number=2, team1_id=senegal.id, team2_id=netherlands.id, match_date=datetime.now(timezone.utc))
    
    session.add_all([match1, match2])
    session.commit()
    
    # Create a user ID (arbitrary for this unit test as we mock the DB)
    user_id = 1
    
    # Scenario: Qatar beats Ecuador 2-0, Senegal draws Netherlands 1-1
    pred1 = Prediction(user_id=user_id, match_id=match1.id, predicted_team1_score=2, predicted_team2_score=0, predicted_winner_id=qatar.id)
    pred2 = Prediction(user_id=user_id, match_id=match2.id, predicted_team1_score=1, predicted_team2_score=1)
    
    session.add_all([pred1, pred2])
    session.commit()
    
    # Calculate standings
    standings = calculate_group_standings(user_id, session)
    
    group_a = standings["A"]
    assert len(group_a) == 4
    
    # Check Qatar: 3 points, GD +2
    team_qatar = next(t for t in group_a if t.team.id == qatar.id)
    assert team_qatar.points == 3
    assert team_qatar.goal_difference == 2
    assert team_qatar.won == 1
    
    # Check Ecuador: 0 points, GD -2
    team_ecuador = next(t for t in group_a if t.team.id == ecuador.id)
    assert team_ecuador.points == 0
    assert team_ecuador.goal_difference == -2
    assert team_ecuador.lost == 1
    
    # Check Senegal: 1 point, GD 0
    team_senegal = next(t for t in group_a if t.team.id == senegal.id)
    assert team_senegal.points == 1
    assert team_senegal.goal_difference == 0
    assert team_senegal.drawn == 1
    
    # Check Netherlands: 1 point, GD 0
    team_netherlands = next(t for t in group_a if t.team.id == netherlands.id)
    assert team_netherlands.points == 1
    assert team_netherlands.drawn == 1

    # Verify order: Qatar first
    assert group_a[0].team.id == qatar.id
