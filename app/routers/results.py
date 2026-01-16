from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..dependencies import require_user
from ..models.user import User
from ..models.match import Match
from ..models.prediction import Prediction
from ..models.fifa_team import FifaTeam

router = APIRouter(prefix="/results", tags=["results"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Round display order and labels (must match database values)
ROUND_ORDER: List[Tuple[str, str]] = [
    ("group_stage", "Group Stage"),
    ("knockout_stage_roundof32", "Round of 32"),
    ("knockout_stage_roundof16", "Round of 16"),
    ("knockout_stage_quarterfinal", "Quarter Finals"),
    ("knockout_stage_semifinal", "Semi Finals"),
    ("knockout_stage_thirdplace", "Third Place"),
    ("knockout_stage_final", "Final")
]


def get_actual_outcome(match: Match) -> Optional[str]:
    """Get the actual outcome string from match scores."""
    if match.actual_home_score is None or match.actual_away_score is None:
        return None
    if match.actual_home_score > match.actual_away_score:
        return "home_win"
    elif match.actual_home_score < match.actual_away_score:
        return "away_win"
    return "draw"


def determine_result_status(
    match: Match,
    prediction: Prediction,
    is_completed: bool,
    is_knockout: bool
) -> str:
    """
    Determine visual status for a result.
    Returns: "correct", "partial", "incorrect", "pending"
    """
    if not is_completed:
        return "pending"

    points = prediction.points_earned

    if points == 3:
        return "correct"  # Exact score
    elif points > 0:
        return "partial"  # Outcome/winner correct
    else:
        return "incorrect"  # Nothing correct


def get_points_display(points: int, is_completed: bool, is_knockout: bool) -> Dict[str, str]:
    """Get display info for points badge."""
    if not is_completed:
        return {
            "display": "Pending",
            "breakdown": "Awaiting result",
            "class": "text-gray-400 italic"
        }

    if points == 3:
        return {
            "display": "+3",
            "breakdown": "Exact score!",
            "class": "bg-green-100 text-green-700"
        }
    elif points == 2 and is_knockout:
        return {
            "display": "+2",
            "breakdown": "Correct winner",
            "class": "bg-yellow-100 text-yellow-700"
        }
    elif points == 1:
        return {
            "display": "+1",
            "breakdown": "Correct outcome",
            "class": "bg-yellow-100 text-yellow-700"
        }
    else:
        return {
            "display": "0",
            "breakdown": "Incorrect",
            "class": "bg-gray-100 text-gray-500"
        }


def build_result_entry(
    match: Match,
    prediction: Prediction,
    home_team: Optional[FifaTeam],
    away_team: Optional[FifaTeam],
    winner_team: Optional[FifaTeam],
    predicted_winner: Optional[FifaTeam]
) -> Dict[str, Any]:
    """Build a single result entry with all display data."""
    is_completed = match.status == "completed"
    is_knockout = match.round != "group_stage"

    result_status = determine_result_status(match, prediction, is_completed, is_knockout)
    points_info = get_points_display(prediction.points_earned, is_completed, is_knockout)

    return {
        "match_id": match.id,
        "match_number": match.match_number,
        "round": match.round,
        "group_letter": match.group_letter,
        "scheduled_datetime": match.scheduled_datetime,
        "status": match.status,

        # Teams
        "home_team": {
            "id": home_team.id,
            "name": home_team.name,
            "country_code": home_team.country_code
        } if home_team else None,
        "away_team": {
            "id": away_team.id,
            "name": away_team.name,
            "country_code": away_team.country_code
        } if away_team else None,

        # Prediction
        "predicted_outcome": prediction.predicted_outcome,
        "predicted_home_score": prediction.predicted_home_score,
        "predicted_away_score": prediction.predicted_away_score,
        "predicted_winner": {
            "id": predicted_winner.id,
            "name": predicted_winner.name
        } if predicted_winner else None,

        # Actual Result
        "actual_home_score": match.actual_home_score,
        "actual_away_score": match.actual_away_score,
        "actual_winner": {
            "id": winner_team.id,
            "name": winner_team.name
        } if winner_team else None,
        "actual_outcome": get_actual_outcome(match) if is_completed else None,

        # Points & Status
        "points_earned": prediction.points_earned if is_completed else None,
        "result_status": result_status,
        "points_display": points_info["display"],
        "points_breakdown": points_info["breakdown"],
        "points_class": points_info["class"],
        "is_completed": is_completed,
        "is_knockout": is_knockout
    }


def get_user_results(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Fetch all predictions for a user with associated match and team data.
    Returns structured data for display.
    """
    # Get all predictions for user
    query = select(Prediction).where(Prediction.user_id == user_id)
    predictions = db.exec(query).all()

    results_by_round: Dict[str, List[Dict[str, Any]]] = {}
    summary = {
        "total_points": 0,
        "total_predictions": 0,
        "correct_outcomes": 0,
        "exact_scores": 0,
        "pending_matches": 0,
        "points_by_round": {round_key: 0 for round_key, _ in ROUND_ORDER}
    }

    for prediction in predictions:
        match = db.get(Match, prediction.match_id)
        if not match:
            continue

        # Get team information
        home_team = db.get(FifaTeam, match.home_team_id) if match.home_team_id else None
        away_team = db.get(FifaTeam, match.away_team_id) if match.away_team_id else None
        winner_team = db.get(FifaTeam, match.actual_winner_team_id) if match.actual_winner_team_id else None
        predicted_winner = db.get(FifaTeam, prediction.predicted_winner_team_id) if prediction.predicted_winner_team_id else None

        # Build result entry
        result_entry = build_result_entry(
            match, prediction, home_team, away_team, winner_team, predicted_winner
        )

        # Group by round
        round_name = match.round
        if round_name not in results_by_round:
            results_by_round[round_name] = []
        results_by_round[round_name].append(result_entry)

        # Update summary
        summary["total_predictions"] += 1

        if match.status == "completed":
            points = prediction.points_earned
            summary["total_points"] += points
            summary["points_by_round"][round_name] += points

            if points == 3:
                summary["exact_scores"] += 1
            elif points > 0:
                summary["correct_outcomes"] += 1
        else:
            summary["pending_matches"] += 1

    # Sort results within each round by match number
    for round_name in results_by_round:
        results_by_round[round_name].sort(key=lambda x: x["match_number"])

    return {
        "summary": summary,
        "results_by_round": results_by_round,
        "round_order": ROUND_ORDER
    }


@router.get("", response_class=HTMLResponse)
async def results_page(
    request: Request,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    """Main results page showing user's predictions vs actual results."""
    data = get_user_results(db, current_user.id)

    return templates.TemplateResponse("results/index.html", {
        "request": request,
        "current_user": current_user,
        "summary": data["summary"],
        "results_by_round": data["results_by_round"],
        "round_order": data["round_order"]
    })
