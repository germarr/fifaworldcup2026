from sqlmodel import Session, select
from ..models.match import Match
from ..models.prediction import Prediction


def calculate_points(prediction: Prediction, match: Match) -> int:
    """
    Calculate points for a single prediction.

    Scoring:
    - Group stage: 1 point for correct outcome, 3 points for exact score
    - Knockout: 2 points for correct winner, 3 points for exact score
    """
    points = 0
    is_knockout = match.round != "group_stage"

    # Can't calculate if match not completed
    if match.actual_home_score is None or match.actual_away_score is None:
        return 0

    # Determine actual outcome
    if match.actual_home_score > match.actual_away_score:
        actual_outcome = "home_win"
    elif match.actual_home_score < match.actual_away_score:
        actual_outcome = "away_win"
    else:
        actual_outcome = "draw"

    # Check outcome prediction
    outcome_correct = prediction.predicted_outcome == actual_outcome

    if is_knockout:
        # For knockout, check if predicted winner matches actual winner
        if match.actual_winner_team_id:
            winner_correct = prediction.predicted_winner_team_id == match.actual_winner_team_id
            if winner_correct:
                points = 2
    else:
        # Group stage: correct outcome gets 1 point
        if outcome_correct:
            points = 1

    # Exact score bonus (replaces base points with 3)
    if (prediction.predicted_home_score == match.actual_home_score and
        prediction.predicted_away_score == match.actual_away_score):
        points = 3

    return points


def calculate_match_points(db: Session, match: Match) -> None:
    """
    Calculate and update points for all predictions on a match.
    Called when admin inputs match results.
    """
    # Get all predictions for this match
    statement = select(Prediction).where(Prediction.match_id == match.id)
    predictions = db.exec(statement).all()

    for prediction in predictions:
        points = calculate_points(prediction, match)
        prediction.points_earned = points
        db.add(prediction)

    db.commit()