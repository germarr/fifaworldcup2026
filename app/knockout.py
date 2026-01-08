"""
Knockout team resolution based on group standings and match predictions.
"""

from typing import Dict, Optional
from sqlmodel import Session, select
from app.models import Match, Prediction, Team


def resolve_knockout_teams(user_id: int, db: Session) -> Dict[str, Optional[Team]]:
    """
    Resolve team placeholders for knockout matches.

    Args:
        user_id: User ID to resolve teams for
        db: Database session

    Returns:
        Dictionary mapping placeholder codes to Team objects
        Example: {'1A': Team(Brazil), '2B': Team(Senegal), 'W49': Team(Netherlands)}
    """
    from app.standings import calculate_group_standings
    
    resolution: Dict[str, Optional[Team]] = {}

    # Calculate standings once and reuse (instead of calling get_group_winner/runner_up 16 times)
    standings = calculate_group_standings(user_id, db)

    # Resolve group winners and runners-up
    for group in "ABCDEFGH":
        group_standings = standings.get(group, [])
        
        winner = group_standings[0].team if len(group_standings) > 0 else None
        runner_up = group_standings[1].team if len(group_standings) > 1 else None

        resolution[f"1{group}"] = winner
        resolution[f"2{group}"] = runner_up

    # Resolve match winners (for quarters, semis, etc.)
    # Get all knockout matches in order
    knockout_matches_statement = select(Match).where(
        ~Match.round.like("Group Stage%")
    ).order_by(Match.match_number)

    knockout_matches = db.exec(knockout_matches_statement).all()

    # Get user predictions for knockout matches
    knockout_match_ids = [m.id for m in knockout_matches]
    predictions_statement = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.match_id.in_(knockout_match_ids)
    )
    predictions = db.exec(predictions_statement).all()

    predictions_map = {p.match_id: p for p in predictions}

    # Get all teams once to avoid repeated queries
    teams_statement = select(Team)
    teams_map = {t.id: t for t in db.exec(teams_statement).all()}

    # Resolve match winners and losers based on predictions AND actual results
    for match in knockout_matches:
        prediction = predictions_map.get(match.id)
        
        # First, resolve the teams in this match
        # We need to pass the current state of resolution to resolve this match's participants
        team1, team2 = resolve_match_teams_with_cache(match, resolution, teams_map, user_id, db)

        # Determine winner and loser
        winner_team = None
        loser_team = None

        # 1. Check ACTUAL result first (Visual consistency with finished matches)
        if match.is_finished:
            if match.actual_team1_score > match.actual_team2_score:
                winner_team = team1
                loser_team = team2
            elif match.actual_team2_score > match.actual_team1_score:
                winner_team = team2
                loser_team = team1
            elif match.penalty_winner_id:
                # Penalty shootout result
                p_winner = teams_map.get(match.penalty_winner_id)
                if p_winner:
                    winner_team = p_winner
                    loser_team = team2 if winner_team == team1 else team1
        
        # 2. If no actual result (or not finished), use PREDICTION
        if not winner_team and prediction:
            if prediction.predicted_team1_score > prediction.predicted_team2_score:
                winner_team = team1
                loser_team = team2
            elif prediction.predicted_team2_score > prediction.predicted_team1_score:
                winner_team = team2
                loser_team = team1
            else:
                # Tie - check penalty shootout winner
                if prediction.penalty_shootout_winner_id:
                    penalty_winner = teams_map.get(prediction.penalty_shootout_winner_id)
                    if penalty_winner:
                        winner_team = penalty_winner
                        loser_team = team2 if winner_team == team1 else team1
                    else:
                        winner_team = team1
                        loser_team = team2
                else:
                    winner_team = team1
                    loser_team = team2

        resolution[f"W{match.match_number}"] = winner_team
        resolution[f"L{match.match_number}"] = loser_team

    return resolution


def resolve_match_teams_with_cache(match: Match, resolution: Dict[str, Optional[Team]], teams_map: Dict[int, Team], user_id: int, db: Session) -> tuple[Optional[Team], Optional[Team]]:
    """
    Resolve the actual teams for a match using cached data.

    Args:
        match: Match object with potential placeholders
        resolution: Pre-built resolution dictionary
        teams_map: Pre-fetched teams map
        user_id: User ID to resolve for
        db: Database session

    Returns:
        Tuple of (team1, team2) - resolved Team objects or None if not determined
    """
    # If match has direct team IDs (group stage), use those
    if match.team1_id and match.team2_id and not match.team1_placeholder and not match.team2_placeholder:
        team1 = teams_map.get(match.team1_id)
        team2 = teams_map.get(match.team2_id)
        return team1, team2

    # Otherwise, resolve using placeholders from pre-built resolution
    team1 = None
    team2 = None

    # Helper to resolve a single placeholder
    def resolve_placeholder(ph):
        if not ph:
            return None
        
        # Check cache first (contains prediction-based or group-based resolution)
        team = resolution.get(ph)
        if team:
            return team

        # If not in cache, and it's a W/L placeholder, check if the previous match is ACTUALLY finished
        if ph.startswith('W') or ph.startswith('L'):
            try:
                prev_match_num = int(ph[1:])
                # Find match in DB (or pass matches map if optimization needed)
                # For now, we query DB or assume resolution map should have handled it if we wanted strictly prediction logic.
                # BUT, to fix "Teams that lost go to next round" visually, we should check ACTUAL results if prediction logic failed/wasn't populated.
                # However, resolution map is built from predictions. 
                
                # BETTER APPROACH: The resolution map construction in resolve_knockout_teams should have handled this.
                # If we are here, it means resolution[ph] is None.
                pass 
            except ValueError:
                pass
        return None

    if match.team1_placeholder:
        team1 = resolution.get(match.team1_placeholder)

    if match.team2_placeholder:
        team2 = resolution.get(match.team2_placeholder)

    # Fallback to direct IDs if placeholders didn't resolve OR if the match is actually set in DB
    # This is critical: if the simulation/admin set the actual teams, we should use them
    if match.team1_id:
        team1 = teams_map.get(match.team1_id)

    if match.team2_id:
        team2 = teams_map.get(match.team2_id)

    return team1, team2


def resolve_match_teams(match: Match, user_id: int, db: Session) -> tuple[Optional[Team], Optional[Team]]:
    """
    Resolve the actual teams for a match based on placeholders.

    Args:
        match: Match object with potential placeholders
        user_id: User ID to resolve for
        db: Database session

    Returns:
        Tuple of (team1, team2) - resolved Team objects or None if not determined
    """
    # If match has direct team IDs (group stage), use those
    if match.team1_id and match.team2_id and not match.team1_placeholder and not match.team2_placeholder:
        teams_statement = select(Team).where(Team.id.in_([match.team1_id, match.team2_id]))
        teams = {t.id: t for t in db.exec(teams_statement).all()}
        
        return teams.get(match.team1_id), teams.get(match.team2_id)

    # Otherwise, resolve using placeholders
    resolution = resolve_knockout_teams(user_id, db)

    team1 = None
    team2 = None

    if match.team1_placeholder:
        team1 = resolution.get(match.team1_placeholder)

    if match.team2_placeholder:
        team2 = resolution.get(match.team2_placeholder)

    # Fallback to direct IDs if placeholders didn't resolve
    if not team1 and match.team1_id:
        team1_statement = select(Team).where(Team.id == match.team1_id)
        team1 = db.exec(team1_statement).first()

    if not team2 and match.team2_id:
        team2_statement = select(Team).where(Team.id == match.team2_id)
        team2 = db.exec(team2_statement).first()

    return team1, team2


def get_match_winner(match_id: int, user_id: int, db: Session) -> Optional[Team]:
    """
    Get the predicted winner of a specific match.

    Args:
        match_id: Match ID
        user_id: User ID
        db: Database session

    Returns:
        Team object of the predicted winner, or None if no prediction
    """
    prediction_statement = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.match_id == match_id
    )
    prediction = db.exec(prediction_statement).first()

    if not prediction:
        return None

    match_statement = select(Match).where(Match.id == match_id)
    match = db.exec(match_statement).first()

    if not match:
        return None

    # Determine winner
    if prediction.predicted_team1_score > prediction.predicted_team2_score:
        winner_id = match.team1_id
    elif prediction.predicted_team2_score > prediction.predicted_team1_score:
        winner_id = match.team2_id
    else:
        # Tie - use predicted_winner_id if available
        winner_id = prediction.predicted_winner_id

    if winner_id:
        team_statement = select(Team).where(Team.id == winner_id)
        return db.exec(team_statement).first()

    return None
