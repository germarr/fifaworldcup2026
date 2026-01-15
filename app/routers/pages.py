from typing import Optional
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..models.prediction import Prediction
from ..models.match import Match
from ..models.competition_team import CompetitionTeam, TeamMembership

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    context = {
        "request": request,
        "current_user": current_user,
        "group_predictions_count": 0,
        "knockout_predictions_count": 0,
        "total_points": 0,
        "leaderboard": [],
        "user_teams": []
    }

    if current_user:
        # Get prediction counts
        group_count = db.exec(
            select(func.count(Prediction.id))
            .join(Match)
            .where(
                Prediction.user_id == current_user.id,
                Match.round == "group_stage"
            )
        ).first() or 0

        knockout_count = db.exec(
            select(func.count(Prediction.id))
            .join(Match)
            .where(
                Prediction.user_id == current_user.id,
                Match.round != "group_stage"
            )
        ).first() or 0

        # Get total points
        total_points = db.exec(
            select(func.sum(Prediction.points_earned))
            .where(Prediction.user_id == current_user.id)
        ).first() or 0

        context["group_predictions_count"] = group_count
        context["knockout_predictions_count"] = knockout_count
        context["total_points"] = total_points

        # Get user's teams
        user_teams_query = (
            select(CompetitionTeam)
            .join(TeamMembership)
            .where(TeamMembership.user_id == current_user.id)
        )
        user_teams = db.exec(user_teams_query).all()

        teams_with_count = []
        for team in user_teams:
            member_count = db.exec(
                select(func.count(TeamMembership.id))
                .where(TeamMembership.team_id == team.id)
            ).first() or 0
            teams_with_count.append({
                "id": team.id,
                "name": team.name,
                "member_count": member_count
            })
        context["user_teams"] = teams_with_count

    # Get leaderboard (top 5)
    leaderboard_query = (
        select(User.display_name, func.sum(Prediction.points_earned).label("total_points"))
        .join(Prediction, Prediction.user_id == User.id)
        .group_by(User.id)
        .order_by(func.sum(Prediction.points_earned).desc())
        .limit(5)
    )
    leaderboard = db.exec(leaderboard_query).all()
    context["leaderboard"] = [
        {"display_name": row[0], "total_points": row[1] or 0}
        for row in leaderboard
    ]

    return templates.TemplateResponse("index.html", context)
