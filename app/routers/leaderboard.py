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

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def leaderboard_page(
    request: Request,
    page: int = 1,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    per_page = 20
    offset = (page - 1) * per_page

    # Get leaderboard
    leaderboard_query = (
        select(
            User.id,
            User.display_name,
            func.sum(Prediction.points_earned).label("total_points"),
            func.count(Prediction.id).label("predictions_count")
        )
        .outerjoin(Prediction, Prediction.user_id == User.id)
        .where(User.is_admin == False)
        .group_by(User.id)
        .order_by(func.sum(Prediction.points_earned).desc())
        .offset(offset)
        .limit(per_page)
    )
    results = db.exec(leaderboard_query).all()

    leaderboard = []
    for i, row in enumerate(results):
        leaderboard.append({
            "rank": offset + i + 1,
            "user_id": row[0],
            "display_name": row[1],
            "total_points": row[2] or 0,
            "predictions_count": row[3]
        })

    # Get total count for pagination
    total_count = db.exec(
        select(func.count(User.id)).where(User.is_admin == False)
    ).first() or 0

    total_pages = (total_count + per_page - 1) // per_page

    # Get current user's rank
    user_rank = None
    if current_user:
        user_points = db.exec(
            select(func.sum(Prediction.points_earned))
            .where(Prediction.user_id == current_user.id)
        ).first() or 0

        users_above = db.exec(
            select(func.count(User.id))
            .outerjoin(Prediction, Prediction.user_id == User.id)
            .where(User.is_admin == False)
            .group_by(User.id)
            .having(func.sum(Prediction.points_earned) > user_points)
        ).all()
        user_rank = len(users_above) + 1

    return templates.TemplateResponse("leaderboard/global.html", {
        "request": request,
        "current_user": current_user,
        "leaderboard": leaderboard,
        "page": page,
        "total_pages": total_pages,
        "user_rank": user_rank
    })


@router.get("/api")
async def leaderboard_api(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_session)
):
    """API endpoint for leaderboard data."""
    offset = (page - 1) * per_page

    leaderboard_query = (
        select(
            User.id,
            User.display_name,
            func.sum(Prediction.points_earned).label("total_points")
        )
        .outerjoin(Prediction, Prediction.user_id == User.id)
        .where(User.is_admin == False)
        .group_by(User.id)
        .order_by(func.sum(Prediction.points_earned).desc())
        .offset(offset)
        .limit(per_page)
    )
    results = db.exec(leaderboard_query).all()

    return [
        {
            "rank": offset + i + 1,
            "user_id": row[0],
            "display_name": row[1],
            "total_points": row[2] or 0
        }
        for i, row in enumerate(results)
    ]
