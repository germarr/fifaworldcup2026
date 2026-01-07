"""
Knockout team resolution based on group standings and match predictions.
"""

from typing import Dict, Optional
from sqlmodel import Session, select
from app.models import Match, Prediction, Team
from app.standings import get_group_winner, get_group_runner_up


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
    resolution: Dict[str, Optional[Team]] = {}

    # Resolve group winners and runners-up
    for group in "ABCDEFGH":
        winner = get_group_winner(group, user_id, db)
        runner_up = get_group_runner_up(group, user_id, db)

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

    # Resolve match winners and losers based on predictions
    for match in knockout_matches:
        prediction = predictions_map.get(match.id)

        if prediction:
            # First, resolve the teams in this match
            team1, team2 = resolve_match_teams(match, user_id, db)

            # Determine winner and loser based on predicted scores
            if prediction.predicted_team1_score > prediction.predicted_team2_score:
                winner_team = team1
                loser_team = team2
            elif prediction.predicted_team2_score > prediction.predicted_team1_score:
                winner_team = team2
                loser_team = team1
            else:
                # Tie - check penalty shootout winner
                if prediction.penalty_shootout_winner_id:
                    # Get the penalty winner team
                    penalty_winner_statement = select(Team).where(Team.id == prediction.penalty_shootout_winner_id)
                    penalty_winner = db.exec(penalty_winner_statement).first()

                    if penalty_winner:
                        winner_team = penalty_winner
                        loser_team = team2 if winner_team == team1 else team1
                    else:
                        # Fallback if penalty winner not found
                        winner_team = team1
                        loser_team = team2
                else:
                    # No penalty shootout prediction - default to team1
                    winner_team = team1
                    loser_team = team2

            resolution[f"W{match.match_number}"] = winner_team
            resolution[f"L{match.match_number}"] = loser_team
        else:
            # No prediction yet - team is TBD
            resolution[f"W{match.match_number}"] = None
            resolution[f"L{match.match_number}"] = None

    return resolution


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
        team1_statement = select(Team).where(Team.id == match.team1_id)
        team2_statement = select(Team).where(Team.id == match.team2_id)

        team1 = db.exec(team1_statement).first()
        team2 = db.exec(team2_statement).first()

        return team1, team2

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
