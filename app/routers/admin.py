from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..dependencies import require_admin
from ..models.user import User
from ..models.fifa_team import FifaTeam
from ..models.stadium import Stadium
from ..models.match import Match
from ..models.prediction import Prediction
from ..services.scoring import calculate_match_points

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    # Get counts
    teams_count = db.exec(select(func.count(FifaTeam.id))).first() or 0
    matches_count = db.exec(select(func.count(Match.id))).first() or 0
    users_count = db.exec(select(func.count(User.id)).where(User.is_admin == False)).first() or 0
    predictions_count = db.exec(select(func.count(Prediction.id))).first() or 0

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "teams_count": teams_count,
        "matches_count": matches_count,
        "users_count": users_count,
        "predictions_count": predictions_count
    })


# FIFA Teams Management
@router.get("/teams", response_class=HTMLResponse)
async def admin_teams(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    teams = db.exec(select(FifaTeam).order_by(FifaTeam.group_letter, FifaTeam.name)).all()

    return templates.TemplateResponse("admin/teams.html", {
        "request": request,
        "current_user": current_user,
        "teams": teams
    })


@router.post("/teams")
async def create_fifa_team(
    request: Request,
    name: str = Form(...),
    country_code: str = Form(None),
    flag_emoji: str = Form(None),
    group_letter: str = Form(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    team = FifaTeam(
        name=name,
        country_code=country_code or None,
        flag_emoji=flag_emoji or None,
        group_letter=group_letter or None
    )
    db.add(team)
    db.commit()

    return RedirectResponse(url="/admin/teams", status_code=303)


@router.post("/teams/{team_id}/update")
async def update_fifa_team(
    team_id: int,
    name: str = Form(...),
    country_code: str = Form(None),
    flag_emoji: str = Form(None),
    group_letter: str = Form(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    team = db.get(FifaTeam, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    team.name = name
    team.country_code = country_code or None
    team.flag_emoji = flag_emoji or None
    team.group_letter = group_letter or None
    team.updated_at = datetime.utcnow()

    db.add(team)
    db.commit()

    return RedirectResponse(url="/admin/teams", status_code=303)


@router.post("/teams/{team_id}/delete")
async def delete_fifa_team(
    team_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    team = db.get(FifaTeam, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    db.delete(team)
    db.commit()

    return RedirectResponse(url="/admin/teams", status_code=303)


# Matches Management
@router.get("/matches", response_class=HTMLResponse)
async def admin_matches(
    request: Request,
    round_filter: str = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    query = select(Match).order_by(Match.scheduled_datetime)
    if round_filter:
        query = query.where(Match.round == round_filter)

    matches = db.exec(query).all()

    # Get teams for dropdown
    teams = db.exec(select(FifaTeam).order_by(FifaTeam.name)).all()
    stadiums = db.exec(select(Stadium)).all()

    # Enrich matches with team names
    matches_data = []
    for match in matches:
        home_team = db.get(FifaTeam, match.home_team_id) if match.home_team_id else None
        away_team = db.get(FifaTeam, match.away_team_id) if match.away_team_id else None
        stadium = db.get(Stadium, match.stadium_id) if match.stadium_id else None

        matches_data.append({
            "match": match,
            "home_team": home_team,
            "away_team": away_team,
            "stadium": stadium
        })

    return templates.TemplateResponse("admin/matches.html", {
        "request": request,
        "current_user": current_user,
        "matches": matches_data,
        "teams": teams,
        "stadiums": stadiums,
        "round_filter": round_filter
    })


@router.post("/matches/{match_id}/score")
async def update_match_score(
    match_id: int,
    home_score: int = Form(...),
    away_score: int = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.actual_home_score = home_score
    match.actual_away_score = away_score
    match.status = "completed"
    match.updated_at = datetime.utcnow()

    # Determine winner for knockout matches
    if match.round != "group_stage":
        if home_score > away_score:
            match.actual_winner_team_id = match.home_team_id
        elif away_score > home_score:
            match.actual_winner_team_id = match.away_team_id
        # If draw, admin needs to set winner separately (penalties)

    db.add(match)
    db.commit()

    # Calculate points for all predictions
    calculate_match_points(db, match)

    return RedirectResponse(url="/admin/matches", status_code=303)


@router.post("/matches/{match_id}/winner")
async def set_match_winner(
    match_id: int,
    winner_team_id: int = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """Set winner for knockout matches that went to penalties."""
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.actual_winner_team_id = winner_team_id
    match.updated_at = datetime.utcnow()

    db.add(match)
    db.commit()

    # Recalculate points
    calculate_match_points(db, match)

    return RedirectResponse(url="/admin/matches", status_code=303)


# Users Management
@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    users_query = (
        select(
            User.id,
            User.email,
            User.display_name,
            User.created_at,
            func.sum(Prediction.points_earned).label("total_points"),
            func.count(Prediction.id).label("predictions_count")
        )
        .outerjoin(Prediction, Prediction.user_id == User.id)
        .where(User.is_admin == False)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    results = db.exec(users_query).all()

    users = [
        {
            "id": r[0],
            "email": r[1],
            "display_name": r[2],
            "created_at": r[3],
            "total_points": r[4] or 0,
            "predictions_count": r[5]
        }
        for r in results
    ]

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "current_user": current_user,
        "users": users
    })
