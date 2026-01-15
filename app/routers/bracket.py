from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException
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
from ..models.third_place_ranking import UserThirdPlaceRanking
from ..services.standings import calculate_group_standings, get_third_place_teams
from ..services.bracket import get_user_bracket

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

            matches_data.append({
                "id": match.id,
                "match_number": match.match_number,
                "home_team": home_team,
                "away_team": away_team,
                "scheduled_datetime": match.scheduled_datetime,
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
