from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_admin_user
from app.flags import flag_url
from app.models import Match, Team, User
from app.scoring import calculate_total_user_score
from simulations.simulate_full_tournament import (
    get_actual_standings,
    resolve_knockout_match,
    update_official_standings,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def recompute_knockout_participants(db: Session) -> None:
    placeholder_map = get_actual_standings(db)
    rounds = ["Round of 16", "Quarter Finals", "Semi Finals", "Third Place", "Final"]

    for round_name in rounds:
        matches = db.exec(select(Match).where(Match.round == round_name)).all()
        for match in matches:
            if resolve_knockout_match(db, match, placeholder_map):
                db.add(match)
    db.commit()


def update_all_user_scores(db: Session) -> None:
    users = db.exec(select(User)).all()
    for user in users:
        user.total_points = calculate_total_user_score(user.id, db)
        db.add(user)
    db.commit()


def format_match_date(value: Optional[datetime]) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%dT%H:%M")


@router.get("/crm", response_class=HTMLResponse)
async def crm_page(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    matches = db.exec(select(Match).order_by(Match.match_number)).all()
    teams = db.exec(select(Team)).all()
    teams_map = {team.id: team for team in teams}

    matches_by_round: Dict[str, List[dict]] = {}
    for match in matches:
        team1 = teams_map.get(match.team1_id)
        team2 = teams_map.get(match.team2_id)

        matches_by_round.setdefault(match.round, []).append({
            "match": match,
            "team1": team1,
            "team2": team2,
            "team1_flag_url": flag_url(team1.code, 28) if team1 else None,
            "team2_flag_url": flag_url(team2.code, 28) if team2 else None,
            "match_date_value": format_match_date(match.match_date),
        })

    return templates.TemplateResponse(
        "crm.html",
        {
            "request": request,
            "user": current_user,
            "matches_by_round": matches_by_round,
        }
    )


@router.post("/crm/match/{match_id}")
async def update_match(
    match_id: int,
    request: Request,
    match_date: Optional[str] = Form(default=None),
    actual_team1_score: Optional[str] = Form(default=None),
    actual_team2_score: Optional[str] = Form(default=None),
    actual_team1_penalty_score: Optional[str] = Form(default=None),
    actual_team2_penalty_score: Optional[str] = Form(default=None),
    penalty_winner: Optional[str] = Form(default=None),
    is_finished: Optional[str] = Form(default=None),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    match = db.exec(select(Match).where(Match.id == match_id)).first()
    if not match:
        return RedirectResponse(url="/crm?error=match_not_found", status_code=303)

    if match_date:
        match.match_date = datetime.fromisoformat(match_date)

    match.actual_team1_score = int(actual_team1_score) if actual_team1_score not in (None, "") else None
    match.actual_team2_score = int(actual_team2_score) if actual_team2_score not in (None, "") else None
    match.actual_team1_penalty_score = (
        int(actual_team1_penalty_score) if actual_team1_penalty_score not in (None, "") else None
    )
    match.actual_team2_penalty_score = (
        int(actual_team2_penalty_score) if actual_team2_penalty_score not in (None, "") else None
    )
    match.is_finished = is_finished == "on"

    if penalty_winner == "team1" and match.team1_id:
        match.penalty_winner_id = match.team1_id
    elif penalty_winner == "team2" and match.team2_id:
        match.penalty_winner_id = match.team2_id
    else:
        match.penalty_winner_id = None

    db.add(match)
    db.commit()

    update_official_standings(db)
    recompute_knockout_participants(db)
    update_all_user_scores(db)

    return RedirectResponse(url="/crm?success=match_updated", status_code=303)


@router.post("/crm/recalculate")
async def recalculate_knockout(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    update_official_standings(db)
    recompute_knockout_participants(db)
    update_all_user_scores(db)
    return RedirectResponse(url="/crm?success=recalculated", status_code=303)
