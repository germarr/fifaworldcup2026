from datetime import datetime, UTC
from app.models.match import Match
from app.models.prediction import Prediction
from app.services.scoring import calculate_points

def test_calculate_points_group_stage_exact_score():
    match = Match(
        match_number=1,
        round="group_stage",
        scheduled_datetime=datetime.now(UTC),
        actual_home_score=2,
        actual_away_score=1
    )
    prediction = Prediction(
        user_id=1,
        match_id=1,
        predicted_outcome="home_win",
        predicted_home_score=2,
        predicted_away_score=1
    )
    points = calculate_points(prediction, match)
    assert points == 3

def test_calculate_points_group_stage_correct_outcome():
    match = Match(
        match_number=1,
        round="group_stage",
        scheduled_datetime=datetime.now(UTC),
        actual_home_score=2,
        actual_away_score=1
    )
    prediction = Prediction(
        user_id=1,
        match_id=1,
        predicted_outcome="home_win",
        predicted_home_score=1,  # Not exact
        predicted_away_score=0   # Not exact
    )
    points = calculate_points(prediction, match)
    assert points == 1

def test_calculate_points_group_stage_wrong_outcome():
    match = Match(
        match_number=1,
        round="group_stage",
        scheduled_datetime=datetime.now(UTC),
        actual_home_score=2,
        actual_away_score=1
    )
    prediction = Prediction(
        user_id=1,
        match_id=1,
        predicted_outcome="draw",
        predicted_home_score=1,
        predicted_away_score=1
    )
    points = calculate_points(prediction, match)
    assert points == 0

def test_calculate_points_knockout_exact_score():
    match = Match(
        match_number=100,
        round="round_of_16",
        scheduled_datetime=datetime.now(UTC),
        actual_home_score=1,
        actual_away_score=1,
        actual_winner_team_id=10
    )
    prediction = Prediction(
        user_id=1,
        match_id=100,
        predicted_outcome="draw",
        predicted_home_score=1,
        predicted_away_score=1,
        predicted_winner_team_id=10
    )
    points = calculate_points(prediction, match)
    assert points == 3

def test_calculate_points_knockout_correct_winner():
    match = Match(
        match_number=100,
        round="round_of_16",
        scheduled_datetime=datetime.now(UTC),
        actual_home_score=1,
        actual_away_score=1,
        actual_winner_team_id=10
    )
    # Predicted draw 0-0 but correct winner
    prediction = Prediction(
        user_id=1,
        match_id=100,
        predicted_outcome="draw",
        predicted_home_score=0,
        predicted_away_score=0,
        predicted_winner_team_id=10
    )
    points = calculate_points(prediction, match)
    assert points == 2

def test_calculate_points_knockout_wrong_winner():
    match = Match(
        match_number=100,
        round="round_of_16",
        scheduled_datetime=datetime.now(UTC),
        actual_home_score=1,
        actual_away_score=1,
        actual_winner_team_id=10
    )
    prediction = Prediction(
        user_id=1,
        match_id=100,
        predicted_outcome="draw",
        predicted_home_score=2,
        predicted_away_score=2,
        predicted_winner_team_id=11 # Wrong winner
    )
    points = calculate_points(prediction, match)
    assert points == 0

def test_calculate_points_incomplete_match():
    match = Match(
        match_number=1,
        round="group_stage",
        scheduled_datetime=datetime.now(UTC),
        # No actual scores
    )
    prediction = Prediction(
        user_id=1,
        match_id=1,
        predicted_outcome="home_win",
        predicted_home_score=2,
        predicted_away_score=1
    )
    points = calculate_points(prediction, match)
    assert points == 0
