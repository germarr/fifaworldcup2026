from typing import List, Tuple, Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..models.match import Match
from ..models.fifa_team import FifaTeam
from ..models.stadium import Stadium

router = APIRouter(prefix="/results", tags=["results"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Round display order and labels
ROUND_ORDER: List[Tuple[str, str]] = [
    ("group_stage", "Group Stage"),
    ("round_of_32", "Round of 32"),
    ("round_of_16", "Round of 16"),
    ("quarter_final", "Quarter Finals"),
    ("semi_final", "Semi Finals"),
    ("third_place", "Third Place"),
    ("final", "Final")
]


@router.get("", response_class=HTMLResponse)
async def results_page(
    request: Request,
    db: Session = Depends(get_session)
):
    """Main results page showing actual match results."""
    # Get all matches with results
    matches = db.exec(
        select(Match).order_by(Match.scheduled_datetime)
    ).all()

    results_by_round: Dict[str, List[Dict[str, Any]]] = {}

    for match in matches:
        home_team = db.get(FifaTeam, match.home_team_id) if match.home_team_id else None
        away_team = db.get(FifaTeam, match.away_team_id) if match.away_team_id else None
        stadium = db.get(Stadium, match.stadium_id) if match.stadium_id else None

        result_entry = {
            "match_id": match.id,
            "match_number": match.match_number,
            "round": match.round,
            "group_letter": match.group_letter,
            "scheduled_datetime": match.scheduled_datetime,
            "status": match.status,
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
            "actual_home_score": match.actual_home_score,
            "actual_away_score": match.actual_away_score,
            "is_completed": match.status == "completed",
            "stadium": {
                "name": stadium.name,
                "city": stadium.city
            } if stadium else None
        }

        round_name = match.round
        if round_name not in results_by_round:
            results_by_round[round_name] = []
        results_by_round[round_name].append(result_entry)

    # Sort results within each round by match number
    for round_name in results_by_round:
        results_by_round[round_name].sort(key=lambda x: x["match_number"] or 0)

    return templates.TemplateResponse("results/index.html", {
        "request": request,
        "results_by_round": results_by_round,
        "round_order": ROUND_ORDER
    })
