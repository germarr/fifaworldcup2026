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


def calculate_total_user_score(user_id: int, db) -> int:
    """
    Calculate total score across all matches (group stage + knockout).
    
    This is the centralized scoring function used by all endpoints.
    Ensures consistent score calculation across the application.
    
    Args:
        user_id: User ID to calculate score for
        db: Database session
        
    Returns:
        Total points earned by user
    """
    from sqlmodel import Session, select
    
    total_score = 0
    
    # Score group stage predictions
    group_statement = (
        select(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id)
        .where(
            Prediction.user_id == user_id,
            Match.round.like("Group Stage%")
        )
    )
    group_results = db.exec(group_statement).all()
    for prediction, match in group_results:
        total_score += calculate_match_points(prediction, match)["points"]
    
    # Score knockout predictions
    from app.knockout import resolve_match_teams
    
    knockout_statement = select(Match).where(~Match.round.like("Group Stage%")).order_by(Match.match_number)
    knockout_matches = db.exec(knockout_statement).all()
    
    pred_statement = select(Prediction).where(Prediction.user_id == user_id)
    predictions = db.exec(pred_statement).all()
    predictions_dict = {pred.match_id: pred for pred in predictions}
    
    for match in knockout_matches:
        team1, team2 = resolve_match_teams(match, user_id, db)
        prediction = predictions_dict.get(match.id)
        
        if prediction:
            scoring_result = calculate_knockout_points(
                prediction,
                match,
                team1.id if team1 else None,
                team2.id if team2 else None
            )
            total_score += scoring_result["points"]
    
    return total_score


def get_champion_prediction(user_id: int, db) -> tuple[Team | None, str | None]:
    """
    Get the predicted champion from the user's final match prediction.
    
    Resolves the final match teams using group stage predictions,
    then determines the winner based on the prediction scores.
    
    Args:
        user_id: User ID to get champion for
        db: Database session
        
    Returns:
        Tuple of (champion_team, champion_flag_url) or (None, None) if invalid
    """
    from sqlmodel import Session, select
    from app.knockout import resolve_match_teams
    from app.flags import flag_url
    
    # Get final match
    final_statement = select(Match).where(Match.round == "Final")
    final_match = db.exec(final_statement).first()
    
    if not final_match:
        return None, None
    
    # Get prediction for final match
    pred_statement = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.match_id == final_match.id
    )
    prediction = db.exec(pred_statement).first()
    
    if not prediction:
        return None, None
    
    # Resolve teams for final match
    team1, team2 = resolve_match_teams(final_match, user_id, db)
    
    if not team1 or not team2:
        return None, None
    
    # Determine champion based on prediction
    champion = None
    if prediction.predicted_team1_score > prediction.predicted_team2_score:
        champion = team1
    elif prediction.predicted_team2_score > prediction.predicted_team1_score:
        champion = team2
    elif prediction.penalty_shootout_winner_id:
        champ_statement = select(Team).where(Team.id == prediction.penalty_shootout_winner_id)
        champion = db.exec(champ_statement).first()
    
    if not champion:
        return None, None
    
    champion_flag_url = flag_url(champion.code, 80)
    return champion, champion_flag_url
