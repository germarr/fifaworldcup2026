from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..dependencies import get_current_user, require_user
from ..models.user import User
from ..models.prediction import Prediction
from ..models.competition_team import CompetitionTeam, TeamMembership

router = APIRouter(prefix="/teams", tags=["teams"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def teams_list(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    # Get all teams with member counts
    teams_query = select(CompetitionTeam)
    teams = db.exec(teams_query).all()

    teams_data = []
    for team in teams:
        member_count = db.exec(
            select(func.count(TeamMembership.id))
            .where(TeamMembership.team_id == team.id)
        ).first() or 0

        # Calculate team total score
        total_score = db.exec(
            select(func.sum(Prediction.points_earned))
            .join(TeamMembership, TeamMembership.user_id == Prediction.user_id)
            .where(TeamMembership.team_id == team.id)
        ).first() or 0

        is_member = False
        if current_user:
            membership = db.exec(
                select(TeamMembership)
                .where(
                    TeamMembership.team_id == team.id,
                    TeamMembership.user_id == current_user.id
                )
            ).first()
            is_member = membership is not None

        teams_data.append({
            "id": team.id,
            "name": team.name,
            "member_count": member_count,
            "total_score": total_score,
            "is_member": is_member,
            "is_admin": current_user and team.admin_user_id == current_user.id
        })

    return templates.TemplateResponse("teams/list.html", {
        "request": request,
        "current_user": current_user,
        "teams": teams_data
    })


@router.get("/create", response_class=HTMLResponse)
async def create_team_page(
    request: Request,
    current_user: User = Depends(require_user)
):
    return templates.TemplateResponse("teams/create.html", {
        "request": request,
        "current_user": current_user
    })


@router.post("/create")
async def create_team(
    request: Request,
    name: str = Form(...),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    # Create team
    team = CompetitionTeam(
        name=name,
        admin_user_id=current_user.id
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    # Add creator as member
    membership = TeamMembership(
        team_id=team.id,
        user_id=current_user.id
    )
    db.add(membership)
    db.commit()

    return RedirectResponse(url=f"/teams/{team.id}", status_code=303)


@router.get("/{team_id}", response_class=HTMLResponse)
async def team_detail(
    team_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    team = db.get(CompetitionTeam, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get members with scores
    members_query = (
        select(
            User.id,
            User.display_name,
            func.sum(Prediction.points_earned).label("points")
        )
        .join(TeamMembership, TeamMembership.user_id == User.id)
        .outerjoin(Prediction, Prediction.user_id == User.id)
        .where(TeamMembership.team_id == team_id)
        .group_by(User.id)
        .order_by(func.sum(Prediction.points_earned).desc())
    )
    members = db.exec(members_query).all()

    members_data = [
        {"id": m[0], "display_name": m[1], "points": m[2] or 0}
        for m in members
    ]

    total_score = sum(m["points"] for m in members_data)

    is_member = False
    is_admin = False
    if current_user:
        membership = db.exec(
            select(TeamMembership)
            .where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == current_user.id
            )
        ).first()
        is_member = membership is not None
        is_admin = team.admin_user_id == current_user.id

    return templates.TemplateResponse("teams/detail.html", {
        "request": request,
        "current_user": current_user,
        "team": team,
        "members": members_data,
        "total_score": total_score,
        "is_member": is_member,
        "is_admin": is_admin
    })


@router.post("/{team_id}/join")
async def join_team(
    team_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    team = db.get(CompetitionTeam, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if already member
    existing = db.exec(
        select(TeamMembership)
        .where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == current_user.id
        )
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    membership = TeamMembership(
        team_id=team_id,
        user_id=current_user.id
    )
    db.add(membership)
    db.commit()

    return RedirectResponse(url=f"/teams/{team_id}", status_code=303)


@router.post("/{team_id}/leave")
async def leave_team(
    team_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    team = db.get(CompetitionTeam, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Can't leave if admin
    if team.admin_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Admin cannot leave team")

    membership = db.exec(
        select(TeamMembership)
        .where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == current_user.id
        )
    ).first()

    if membership:
        db.delete(membership)
        db.commit()

    return RedirectResponse(url="/teams", status_code=303)


@router.post("/{team_id}/remove/{user_id}")
async def remove_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    team = db.get(CompetitionTeam, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if current user is admin
    if team.admin_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only team admin can remove members")

    # Can't remove yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Admin cannot remove themselves")

    membership = db.exec(
        select(TeamMembership)
        .where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user_id
        )
    ).first()

    if membership:
        db.delete(membership)
        db.commit()

    return RedirectResponse(url=f"/teams/{team_id}", status_code=303)


@router.get("/compare", response_class=HTMLResponse)
async def compare_teams(
    request: Request,
    team1: int,
    team2: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    team1_obj = db.get(CompetitionTeam, team1)
    team2_obj = db.get(CompetitionTeam, team2)

    if not team1_obj or not team2_obj:
        raise HTTPException(status_code=404, detail="Team not found")

    def get_team_stats(team_id: int):
        members_query = (
            select(
                User.id,
                User.display_name,
                func.sum(Prediction.points_earned).label("points")
            )
            .join(TeamMembership, TeamMembership.user_id == User.id)
            .outerjoin(Prediction, Prediction.user_id == User.id)
            .where(TeamMembership.team_id == team_id)
            .group_by(User.id)
            .order_by(func.sum(Prediction.points_earned).desc())
        )
        members = db.exec(members_query).all()
        return [{"id": m[0], "display_name": m[1], "points": m[2] or 0} for m in members]

    team1_members = get_team_stats(team1)
    team2_members = get_team_stats(team2)

    return templates.TemplateResponse("leaderboard/team_compare.html", {
        "request": request,
        "current_user": current_user,
        "team1": {"team": team1_obj, "members": team1_members, "total": sum(m["points"] for m in team1_members)},
        "team2": {"team": team2_obj, "members": team2_members, "total": sum(m["points"] for m in team2_members)}
    })
