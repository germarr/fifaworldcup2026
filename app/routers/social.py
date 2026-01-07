from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from app.models import User, PlayerTeam, Match, Prediction
from app.database import get_session
from app.dependencies import get_current_user
from app.scoring import calculate_match_points
import random
import string

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def generate_join_code(length=6):
    """Generate a random alphanumeric join code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def sync_user_scores(db: Session):
    """
    Recalculate and update total_points for all users based on current finished matches.
    This ensures the leaderboard is always up to date.
    """
    # optimization: fetch all finished matches once
    finished_matches = db.exec(select(Match).where(Match.is_finished == True)).all()
    match_map = {m.id: m for m in finished_matches}
    
    if not match_map:
        return

    users = db.exec(select(User)).all()
    
    for user in users:
        total_points = 0
        # Get user predictions for finished matches
        predictions = db.exec(select(Prediction).where(
            Prediction.user_id == user.id,
            Prediction.match_id.in_(match_map.keys())
        )).all()
        
        for pred in predictions:
            match = match_map.get(pred.match_id)
            if match:
                result = calculate_match_points(pred, match)
                total_points += result["points"]
        
        if user.total_points != total_points:
            user.total_points = total_points
            db.add(user)
    
    db.commit()

@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Leaderboard page."""
    
    # Sync scores before displaying to ensure accuracy
    sync_user_scores(db)
    
    # 1. Global Player Leaderboard (Top 50)
    global_players = db.exec(select(User).order_by(User.total_points.desc()).limit(50)).all()
    
    # 2. Team Leaderboard (Ranked by average points per member or total points)
    # Using total points for now
    teams = db.exec(select(PlayerTeam)).all()
    # Sort teams by total points in python as property isn't a DB column
    teams_ranked = sorted(teams, key=lambda t: t.total_points, reverse=True)
    
    # 3. My Team Leaderboard
    my_team_members = []
    if current_user.player_team:
        my_team_members = sorted(current_user.player_team.members, key=lambda u: u.total_points, reverse=True)

    return templates.TemplateResponse(
        "leaderboard.html",
        {
            "request": request,
            "user": current_user,
            "global_players": global_players,
            "teams": teams_ranked,
            "my_team_members": my_team_members
        }
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Settings page."""
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": current_user
        }
    )

@router.post("/settings/avatar")
async def update_avatar(
    seed: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Update user avatar seed."""
    current_user.avatar_seed = seed
    db.add(current_user)
    db.commit()
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/team/create")
async def create_team(
    team_name: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Create a new player team."""
    if current_user.player_team_id:
        # User already in a team
        return RedirectResponse(url="/settings?error=already_in_team", status_code=303)
        
    join_code = generate_join_code()
    new_team = PlayerTeam(name=team_name, join_code=join_code)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    
    # Add user to team
    current_user.player_team_id = new_team.id
    db.add(current_user)
    db.commit()
    
    return RedirectResponse(url="/settings?success=team_created", status_code=303)

@router.post("/settings/team/join")
async def join_team(
    join_code: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Join an existing player team."""
    if current_user.player_team_id:
        return RedirectResponse(url="/settings?error=already_in_team", status_code=303)
        
    team = db.exec(select(PlayerTeam).where(PlayerTeam.join_code == join_code)).first()
    if not team:
        return RedirectResponse(url="/settings?error=invalid_code", status_code=303)
        
    current_user.player_team_id = team.id
    db.add(current_user)
    db.commit()
    
    return RedirectResponse(url="/settings?success=team_joined", status_code=303)

@router.post("/settings/team/leave")
async def leave_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Leave current team."""
    if not current_user.player_team_id:
        return RedirectResponse(url="/settings", status_code=303)
        
    current_user.player_team_id = None
    db.add(current_user)
    db.commit()
    
    return RedirectResponse(url="/settings?success=left_team", status_code=303)
