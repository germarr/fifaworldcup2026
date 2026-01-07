from app.models import Match, Prediction, Team

def calculate_match_points(prediction: Prediction, match: Match) -> dict:
    """
    Calculate points earned for a single match prediction.
    
    Rules:
    - Correct Outcome (Winner/Draw): 1 point
    - Exact Score: +2 points (Total 3)
    - Penalty Winner (if applicable): +1 point
    """
    if match.actual_team1_score is None or match.actual_team2_score is None:
        return {"points": 0, "breakdown": [], "status": "pending"}

    points = 0
    breakdown = []

    # 1. Determine Actual Outcome
    actual_winner_id = None # None means Draw
    if match.actual_team1_score > match.actual_team2_score:
        actual_winner_id = match.team1_id
    elif match.actual_team2_score > match.actual_team1_score:
        actual_winner_id = match.team2_id
    
    # 2. Determine Predicted Outcome
    predicted_winner_id = None
    if prediction.predicted_team1_score > prediction.predicted_team2_score:
        predicted_winner_id = match.team1_id
    elif prediction.predicted_team2_score > prediction.predicted_team1_score:
        predicted_winner_id = match.team2_id

    # Check Outcome
    outcome_correct = False
    if actual_winner_id == predicted_winner_id:
        outcome_correct = True
        points += 1
        breakdown.append("Correct Outcome (+1)")

    # Check Exact Score
    score_correct = False
    if (prediction.predicted_team1_score == match.actual_team1_score and 
        prediction.predicted_team2_score == match.actual_team2_score):
        score_correct = True
        points += 2
        breakdown.append("Exact Score (+2)")

    return {
        "points": points,
        "breakdown": breakdown,
        "status": "complete",
        "outcome_correct": outcome_correct,
        "score_correct": score_correct
    }


def calculate_knockout_points(
    prediction: Prediction,
    match: Match,
    predicted_team1_id: int | None,
    predicted_team2_id: int | None
) -> dict:
    """
    Calculate points for knockout matches with team mismatch handling.
    - Full scoring only when the predicted teams match the actual teams.
    - If at least one predicted team matches, allow outcome points when winner aligns.
    """
    if match.actual_team1_score is None or match.actual_team2_score is None:
        return {"points": 0, "breakdown": [], "status": "pending"}

    if not predicted_team1_id or not predicted_team2_id:
        return {"points": 0, "breakdown": [], "status": "pending"}

    predicted_ids = {predicted_team1_id, predicted_team2_id}
    actual_ids = {match.team1_id, match.team2_id} if match.team1_id and match.team2_id else set()

    if predicted_ids and actual_ids and predicted_ids == actual_ids:
        full = calculate_match_points(prediction, match)
        full["points"] *= 2
        if full["breakdown"]:
            full["breakdown"] = [f"{b} x2" for b in full["breakdown"]]
        return full

    points = 0
    breakdown = []

    actual_winner_id = None
    if match.actual_team1_score > match.actual_team2_score:
        actual_winner_id = match.team1_id
    elif match.actual_team2_score > match.actual_team1_score:
        actual_winner_id = match.team2_id

    predicted_winner_id = None
    if prediction.predicted_team1_score > prediction.predicted_team2_score:
        predicted_winner_id = predicted_team1_id
    elif prediction.predicted_team2_score > prediction.predicted_team1_score:
        predicted_winner_id = predicted_team2_id

    if actual_winner_id in predicted_ids and predicted_winner_id == actual_winner_id:
        points += 1
        breakdown.append("Correct Outcome (+1)")

    if points > 0:
        points *= 2
        breakdown = [f"{b} x2" for b in breakdown]

    return {
        "points": points,
        "breakdown": breakdown,
        "status": "complete" if points > 0 else "pending",
        "outcome_correct": points > 0,
        "score_correct": False
    }
