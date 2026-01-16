from datetime import datetime
from sqlmodel import Session
from app.models.fifa_team import FifaTeam
from app.models.match import Match
from app.models.prediction import Prediction
from app.services.standings import calculate_group_standings

def create_team(session: Session, name: str, group: str) -> FifaTeam:
    team = FifaTeam(name=name, group_letter=group)
    session.add(team)
    session.commit()
    session.refresh(team)
    return team

def create_match(session: Session, team1_id: int, team2_id: int, group: str) -> Match:
    match = Match(
        match_number=1, # simplified
        round="group_stage",
        group_letter=group,
        home_team_id=team1_id,
        away_team_id=team2_id,
        scheduled_datetime=datetime.utcnow()
    )
    # Dirty hack for match number unique constraint if creating multiple matches
    # Since I might create multiple matches, I should let the caller handle match_number or autoincrement it
    # But for this test, I will handle it in the test function
    return match

def test_calculate_group_standings(session: Session):
    # Setup Teams
    team_a = create_team(session, "Team A", "A")
    team_b = create_team(session, "Team B", "A")
    team_c = create_team(session, "Team C", "A")
    team_d = create_team(session, "Team D", "A")

    # Setup Matches
    # A vs B
    m1 = Match(match_number=1, round="group_stage", group_letter="A", home_team_id=team_a.id, away_team_id=team_b.id, scheduled_datetime=datetime.utcnow())
    # C vs D
    m2 = Match(match_number=2, round="group_stage", group_letter="A", home_team_id=team_c.id, away_team_id=team_d.id, scheduled_datetime=datetime.utcnow())
    session.add(m1)
    session.add(m2)
    session.commit()

    user_id = 1

    # Setup Predictions
    # User predicts A wins 2-0 against B
    p1 = Prediction(user_id=user_id, match_id=m1.id, predicted_outcome="home_win", predicted_home_score=2, predicted_away_score=0)
    # User predicts C draws 1-1 with D
    p2 = Prediction(user_id=user_id, match_id=m2.id, predicted_outcome="draw", predicted_home_score=1, predicted_away_score=1)
    session.add(p1)
    session.add(p2)
    session.commit()

    standings = calculate_group_standings(session, user_id, "A")

    # Check length
    assert len(standings) == 4

    # Team A should be first: 3 points, +2 GD
    assert standings[0]["team_id"] == team_a.id
    assert standings[0]["points"] == 3
    assert standings[0]["goal_diff"] == 2
    assert standings[0]["position"] == 1

    # Team C and D share 2nd/3rd: 1 point, 0 GD. C has 1 GF, D has 1 GF.
    # Order between C and D depends on alphabetical or insertion if stats are identical (logic says points > gd > gf)
    # Since all stats are equal, the sort is stable or determined by implementation detail, but points should be 1.
    assert standings[1]["points"] == 1
    assert standings[2]["points"] == 1

    # Team B last: 0 points, -2 GD
    assert standings[3]["team_id"] == team_b.id
    assert standings[3]["points"] == 0
    assert standings[3]["goal_diff"] == -2

def test_calculate_group_standings_no_matches(session: Session):
    standings = calculate_group_standings(session, user_id=1, group_letter="Z")
    assert standings == []
