from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pydantic import BaseModel

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..dependencies import get_current_user, require_user
from ..models.user import User
from ..models.match import Match
from ..models.prediction import Prediction
from ..models.fifa_team import FifaTeam
from ..models.stadium import Stadium
from ..models.third_place_ranking import UserThirdPlaceRanking
from ..services.standings import calculate_group_standings, get_third_place_teams
from ..services.bracket import get_user_bracket
from ..services.brackets import get_or_create_user_bracket

router = APIRouter(prefix="/bracket", tags=["bracket"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/groups", response_class=HTMLResponse)
async def groups_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    if not current_user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=303)

    bracket_record = get_or_create_user_bracket(db, current_user.id)

    groups = {}

    # Get all group letters that have teams
    teams = db.exec(select(FifaTeam).where(FifaTeam.group_letter.isnot(None))).all()
    group_letters = sorted(set(t.group_letter for t in teams if t.group_letter))

    for group_letter in group_letters:
        # Get matches for this group
        matches_query = select(Match).where(
            Match.round == "group_stage",
            Match.group_letter == group_letter
        ).order_by(Match.scheduled_datetime)
        matches = db.exec(matches_query).all()

        # Get predictions for these matches
        match_ids = [m.id for m in matches]
        predictions_query = select(Prediction).where(
            Prediction.user_id == current_user.id,
            Prediction.match_id.in_(match_ids)
        )
        predictions = db.exec(predictions_query).all()
        pred_by_match = {p.match_id: p for p in predictions}

        # Build match data
        matches_data = []
        for match in matches:
            home_team = db.get(FifaTeam, match.home_team_id) if match.home_team_id else None
            away_team = db.get(FifaTeam, match.away_team_id) if match.away_team_id else None
            stadium = db.get(Stadium, match.stadium_id) if match.stadium_id else None

            matches_data.append({
                "id": match.id,
                "match_number": match.match_number,
                "home_team": home_team,
                "away_team": away_team,
                "scheduled_datetime": match.scheduled_datetime,
                "stadium": {
                    "name": stadium.name,
                    "city": stadium.city
                } if stadium else None,
                "prediction": pred_by_match.get(match.id),
                "locked": match.scheduled_datetime <= datetime.utcnow() if match.scheduled_datetime else False
            })

        # Calculate standings
        standings = calculate_group_standings(db, current_user.id, group_letter)

        groups[group_letter] = {
            "matches": matches_data,
            "standings": standings,
            "predictions_count": len(predictions)
        }

    # Get third place teams for the ranking section at bottom
    third_place_teams = get_third_place_teams(db, current_user.id)

    return templates.TemplateResponse("bracket/groups.html", {
        "request": request,
        "current_user": current_user,
        "bracket_id": bracket_record.id,
        "groups": groups,
        "third_place_teams": third_place_teams
    })


@router.get("/third-place", response_class=HTMLResponse)
async def third_place_page(
    request: Request,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    third_place_teams = get_third_place_teams(db, current_user.id)

    return templates.TemplateResponse("bracket/third_place.html", {
        "request": request,
        "current_user": current_user,
        "third_place_teams": third_place_teams
    })


class ThirdPlaceRanking(BaseModel):
    team_id: int
    rank_position: int


class ThirdPlaceRankingRequest(BaseModel):
    rankings: List[ThirdPlaceRanking]


@router.post("/api/third-place")
async def save_third_place_ranking(
    data: ThirdPlaceRankingRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    # Delete existing rankings
    existing = db.exec(
        select(UserThirdPlaceRanking).where(UserThirdPlaceRanking.user_id == current_user.id)
    ).all()
    for r in existing:
        db.delete(r)

    # Commit deletion to ensure unique constraints are cleared
    db.commit()

    # Create new rankings
    for ranking in data.rankings:
        new_ranking = UserThirdPlaceRanking(
            user_id=current_user.id,
            team_id=ranking.team_id,
            rank_position=ranking.rank_position
        )
        db.add(new_ranking)

    db.commit()
    return {"status": "ok"}


@router.get("", response_class=HTMLResponse)
async def bracket_page(
    request: Request,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    bracket = get_user_bracket(db, current_user.id)
    return templates.TemplateResponse("bracket/knockout.html", {
        "request": request,
        "current_user": current_user,
        "bracket": bracket
    })


def get_flag_code(country_code: str) -> str:
    code_map = {
        "USA": "us",
        "MEX": "mx",
        "CAN": "ca",
        "BRA": "br",
        "ARG": "ar",
        "COL": "co",
        "GER": "de",
        "FRA": "fr",
        "ESP": "es",
        "ENG": "gb-eng",
        "NED": "nl",
        "BEL": "be",
        "POR": "pt",
        "ITA": "it",
        "CRO": "hr",
        "JPN": "jp",
        "KOR": "kr",
        "AUS": "au",
        "MAR": "ma",
        "SEN": "sn",
        "NGA": "ng",
        "URU": "uy",
        "ECU": "ec",
        "CHI": "cl",
        "SUI": "ch",
        "DEN": "dk",
        "POL": "pl",
        "SRB": "rs",
        "UKR": "ua",
        "AUT": "at",
        "KSA": "sa",
        "IRN": "ir",
        "QAT": "qa",
        "CRC": "cr",
        "PAN": "pa",
        "JAM": "jm",
    }

    return code_map.get(country_code, country_code.lower() if country_code else "xx")


@router.get("/print", response_class=HTMLResponse)
async def print_bracket(
    request: Request,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    bracket = get_user_bracket(db, current_user.id)

    # Extract Champion
    champion = None
    if bracket.get("final") and bracket["final"].get("prediction"):
        pred = bracket["final"]["prediction"]
        winner_id = pred["predicted_winner_team_id"]
        if winner_id:
            if bracket["final"]["home_team"] and bracket["final"]["home_team"]["team_id"] == winner_id:
                champion = bracket["final"]["home_team"]
            elif bracket["final"]["away_team"] and bracket["final"]["away_team"]["team_id"] == winner_id:
                champion = bracket["final"]["away_team"]
            else:
                # Fallback: Fetch from DB if prediction exists but team not in final slots
                team = db.get(FifaTeam, winner_id)
                if team:
                    champion = {
                        "team_id": team.id,
                        "team_name": team.name,
                        "country_code": team.country_code
                    }

    # Extract Third Place Winner
    third_place_winner = None
    if bracket.get("third_place_match") and bracket["third_place_match"].get("prediction"):
        pred = bracket["third_place_match"]["prediction"]
        winner_id = pred["predicted_winner_team_id"]
        if winner_id:
            if (
                bracket["third_place_match"]["home_team"]
                and bracket["third_place_match"]["home_team"]["team_id"] == winner_id
            ):
                third_place_winner = bracket["third_place_match"]["home_team"]
            elif (
                bracket["third_place_match"]["away_team"]
                and bracket["third_place_match"]["away_team"]["team_id"] == winner_id
            ):
                third_place_winner = bracket["third_place_match"]["away_team"]
            else:
                # Fallback: Fetch from DB
                team = db.get(FifaTeam, winner_id)
                if team:
                    third_place_winner = {
                        "team_id": team.id,
                        "team_name": team.name,
                        "country_code": team.country_code
                    }

    return templates.TemplateResponse("bracket/print.html", {
        "request": request,
        "current_user": current_user,
        "bracket": bracket,
        "champion": champion,
        "third_place_winner": third_place_winner,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "flag_code": get_flag_code
    })
