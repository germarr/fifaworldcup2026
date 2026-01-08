from app.models import Match, Prediction, Team

def calculate_match_points(prediction: Prediction, match: Match) -> dict:
    """
    Calculate points earned for a single match prediction.
    
    Rules:
    - Correct Outcome (Winner/Draw): 1 point
    - Exact Score: +2 points (Total 3)
    - Handles penalty shootout outcomes
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
    elif match.actual_team1_score == match.actual_team2_score and match.penalty_winner_id:
        # Tie with penalty shootout
        actual_winner_id = match.penalty_winner_id
    
    # 2. Determine Predicted Outcome
    predicted_winner_id = None
    if prediction.predicted_team1_score > prediction.predicted_team2_score:
        predicted_winner_id = match.team1_id
    elif prediction.predicted_team2_score > prediction.predicted_team1_score:
        predicted_winner_id = match.team2_id
    elif prediction.predicted_team1_score == prediction.predicted_team2_score and prediction.penalty_shootout_winner_id:
        # Tie with penalty shootout prediction
        predicted_winner_id = prediction.penalty_shootout_winner_id

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
    Calculate points for knockout matches.
    
    Rules:
    - Points are ONLY awarded if predicted teams match actual teams
    - When teams match, use full scoring rules (outcome + score x2 multiplier)
    - If teams don't match, return 0 points (pending status)
    """
    if match.actual_team1_score is None or match.actual_team2_score is None:
        return {"points": 0, "breakdown": [], "status": "pending"}

    if not predicted_team1_id or not predicted_team2_id:
        return {"points": 0, "breakdown": [], "status": "pending"}

    predicted_ids = {predicted_team1_id, predicted_team2_id}
    actual_ids = {match.team1_id, match.team2_id} if match.team1_id and match.team2_id else set()

    # Teams must match for any points to be awarded
    if not (predicted_ids and actual_ids and predicted_ids == actual_ids):
        # Teams don't match - no points awarded
        return {
            "points": 0,
            "breakdown": [],
            "status": "pending",
            "outcome_correct": False,
            "score_correct": False
        }
    
    # Teams match - use full scoring with 2x multiplier
    full = calculate_match_points(prediction, match)
    full["points"] *= 2
    if full["breakdown"]:
        full["breakdown"] = [f"{b} x2" for b in full["breakdown"]]
    return full


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


def get_tournament_champion(user_id: int, db) -> tuple[Team | None, str | None, bool]:
    """
    Get the tournament champion (actual if finished, otherwise predicted).
    
    Args:
        user_id: User ID to get champion for
        db: Database session
        
    Returns:
        Tuple of (champion_team, champion_flag_url, is_actual)
    """
    from sqlmodel import Session, select
    from app.knockout import resolve_match_teams
    from app.flags import flag_url
    
    # Get final match
    final_statement = select(Match).where(Match.round == "Final")
    final_match = db.exec(final_statement).first()
    
    if not final_match:
        return None, None, False
        
    # 1. Check Prediction First (User's Bracket View)
    pred_statement = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.match_id == final_match.id
    )
    prediction = db.exec(pred_statement).first()
    
    if prediction:
        # Resolve teams for final match
        team1, team2 = resolve_match_teams(final_match, user_id, db)
        
        if team1 and team2:
            # Determine champion based on prediction
            champion = None
            
            # Prioritize explicit winner ID if available (handles swapped teams)
            if prediction.predicted_winner_id:
                if team1.id == prediction.predicted_winner_id:
                    champion = team1
                elif team2.id == prediction.predicted_winner_id:
                    champion = team2
            
            # Fallback to scores if no winner ID or mismatch
            if not champion:
                if prediction.predicted_team1_score > prediction.predicted_team2_score:
                    champion = team1
                elif prediction.predicted_team2_score > prediction.predicted_team1_score:
                    champion = team2
                elif prediction.penalty_shootout_winner_id:
                    # Check if penalty winner matches resolved teams
                    if team1 and prediction.penalty_shootout_winner_id == team1.id:
                        champion = team1
                    elif team2 and prediction.penalty_shootout_winner_id == team2.id:
                        champion = team2
                    else:
                        # Fallback if IDs mismatch
                        champ_statement = select(Team).where(Team.id == prediction.penalty_shootout_winner_id)
                        champion = db.exec(champ_statement).first()
            
            if champion:
                champion_flag_url = flag_url(champion.code, 80)
                return champion, champion_flag_url, False

    # 2. Fallback to Actual Champion (if finished and no prediction/resolution failed)
    if final_match.is_finished:
        winner = None
        if final_match.actual_team1_score > final_match.actual_team2_score:
            winner = final_match.team1
        elif final_match.actual_team2_score > final_match.actual_team1_score:
            winner = final_match.team2
        elif final_match.penalty_winner_id:
             winner_statement = select(Team).where(Team.id == final_match.penalty_winner_id)
             winner = db.exec(winner_statement).first()
             
        if winner:
            return winner, flag_url(winner.code, 80), True
    
    return None, None, False
