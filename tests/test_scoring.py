from app.models import Match, Prediction
from app.scoring import calculate_match_points, calculate_knockout_points

def test_calculate_match_points_exact_score():
    match = Match(actual_team1_score=2, actual_team2_score=1, team1_id=1, team2_id=2)
    prediction = Prediction(predicted_team1_score=2, predicted_team2_score=1)
    
    result = calculate_match_points(prediction, match)
    
    # 1 point for outcome + 2 points for exact score = 3
    assert result["points"] == 3
    assert result["score_correct"] is True
    assert result["outcome_correct"] is True
    assert "Exact Score (+2)" in result["breakdown"]

def test_calculate_match_points_correct_outcome_only():
    match = Match(actual_team1_score=2, actual_team2_score=1, team1_id=1, team2_id=2)
    prediction = Prediction(predicted_team1_score=3, predicted_team2_score=0)
    
    result = calculate_match_points(prediction, match)
    
    # 1 point for outcome (Team 1 wins)
    assert result["points"] == 1
    assert result["score_correct"] is False
    assert result["outcome_correct"] is True
    assert "Correct Outcome (+1)" in result["breakdown"]

def test_calculate_match_points_draw_correct():
    match = Match(actual_team1_score=1, actual_team2_score=1, team1_id=1, team2_id=2)
    prediction = Prediction(predicted_team1_score=1, predicted_team2_score=1)
    
    result = calculate_match_points(prediction, match)
    
    # 1 outcome (Draw) + 2 exact score = 3
    assert result["points"] == 3
    assert result["score_correct"] is True
    assert result["outcome_correct"] is True

def test_calculate_match_points_draw_outcome_only():
    match = Match(actual_team1_score=1, actual_team2_score=1, team1_id=1, team2_id=2)
    prediction = Prediction(predicted_team1_score=2, predicted_team2_score=2)
    
    result = calculate_match_points(prediction, match)
    
    # 1 outcome (Draw)
    assert result["points"] == 1
    assert result["score_correct"] is False
    assert result["outcome_correct"] is True

def test_calculate_match_points_incorrect():
    match = Match(actual_team1_score=2, actual_team2_score=1, team1_id=1, team2_id=2)
    prediction = Prediction(predicted_team1_score=0, predicted_team2_score=1)
    
    result = calculate_match_points(prediction, match)
    
    assert result["points"] == 0
    assert result["score_correct"] is False
    assert result["outcome_correct"] is False

def test_calculate_knockout_points_full_match():
    # Predicted teams match actual teams
    match = Match(actual_team1_score=2, actual_team2_score=1, team1_id=1, team2_id=2)
    prediction = Prediction(predicted_team1_score=2, predicted_team2_score=1)
    
    # User predicted Team 1 vs Team 2 correctly
    result = calculate_knockout_points(prediction, match, predicted_team1_id=1, predicted_team2_id=2)
    
    # Base points 3 * 2 multiplier = 6
    assert result["points"] == 6
    assert any("x2" in b for b in result["breakdown"])

def test_calculate_knockout_points_mismatch_but_winner_correct():
    # Actual match: Team 1 vs Team 2. Team 1 wins.
    match = Match(actual_team1_score=2, actual_team2_score=1, team1_id=1, team2_id=2)
    
    # User predicted: Team 1 vs Team 3. Team 1 wins.
    prediction = Prediction(predicted_team1_score=2, predicted_team2_score=0)
    
    # One team matches (Team 1), and the predicted winner (Team 1) is the actual winner (Team 1)
    result = calculate_knockout_points(prediction, match, predicted_team1_id=1, predicted_team2_id=3)
    
    # Logic in knockout.py:
    # if actual_winner_id in predicted_ids and predicted_winner_id == actual_winner_id: points += 1
    # Multiplied by 2
    
    # Actual winner: 1. Predicted IDs: {1, 3}. Winner 1 is in predicted.
    # Predicted winner: 1. Actual winner: 1. Match!
    # Points = 1 * 2 = 2
    assert result["points"] == 2
    assert result["outcome_correct"] is True

def test_calculate_knockout_points_mismatch_winner_wrong():
    # Actual match: Team 1 vs Team 2. Team 1 wins.
    match = Match(actual_team1_score=2, actual_team2_score=1, team1_id=1, team2_id=2)
    
    # User predicted: Team 2 vs Team 3. Team 2 wins.
    prediction = Prediction(predicted_team1_score=2, predicted_team2_score=0)
    
    # Predicted IDs {2, 3}. Actual Winner 1 is NOT in predicted.
    result = calculate_knockout_points(prediction, match, predicted_team1_id=2, predicted_team2_id=3)
    
    assert result["points"] == 0
