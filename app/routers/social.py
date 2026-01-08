from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from app.models import User, PlayerTeam, Match, Prediction, Team, UserTeamMembership
from app.database import get_session
from app.dependencies import get_current_user
from app.scoring import (
    calculate_match_points,
    calculate_knockout_points,
    calculate_total_user_score,
    get_tournament_champion
)
from app.knockout import resolve_match_teams
from app.flags import flag_url
import random
import string
import re

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
    users = db.exec(select(User)).all()
    
    for user in users:
        # Use centralized scoring function that handles group + knockout
        total_points = calculate_total_user_score(user.id, db)
        
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


def get_user_team_ids(db: Session, user_id: int) -> list[int]:
    memberships = db.exec(
        select(UserTeamMembership).where(UserTeamMembership.user_id == user_id)
    ).all()
    return [membership.player_team_id for membership in memberships]


def get_team_members(db: Session, team_id: int) -> list[User]:
    statement = (
        select(User)
        .join(UserTeamMembership, UserTeamMembership.user_id == User.id)
        .where(UserTeamMembership.player_team_id == team_id)
        .order_by(User.total_points.desc())
    )
    return db.exec(statement).all()


@router.get("/api/teams/{team_id}/members")
async def team_members(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    members = [member for member in get_team_members(db, team_id) if member.id != current_user.id]
    return [
        {
            "id": member.id,
            "username": member.username,
            "total_points": member.total_points
        }
        for member in members
    ]


@router.get("/leaderboard/compare", response_class=HTMLResponse)
async def leaderboard_compare(
    request: Request,
    team_id: int | None = None,
    player_id: int | None = None,
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Compare your predictions against another player."""
    sync_user_scores(db)

    teams = db.exec(select(PlayerTeam).order_by(PlayerTeam.name)).all()
    my_team_ids = set(get_user_team_ids(db, current_user.id))

    selected_team_id = team_id
    if selected_team_id is None and my_team_ids:
        selected_team_id = next(iter(my_team_ids))

    team_members = []
    if selected_team_id:
        team_members = [member for member in get_team_members(db, selected_team_id) if member.id != current_user.id]

    selected_player_id = player_id
    if selected_player_id is None and team_members:
        selected_player_id = team_members[0].id

    other_user = None
    if selected_player_id:
        other_user = db.exec(select(User).where(User.id == selected_player_id)).first()
        if other_user and other_user.id == current_user.id:
            other_user = None

    search_results = []
    search_query = q.strip()
    if search_query:
        search_statement = (
            select(User)
            .where(User.username.contains(search_query))
            .where(User.id != current_user.id)
            .order_by(User.total_points.desc())
            .limit(20)
        )
        search_results = db.exec(search_statement).all()

    match_cards = []
    total_points_current = calculate_total_user_score(current_user.id, db)
    total_points_other = None
    current_champion = None
    current_champion_flag = None
    other_champion = None
    other_champion_flag = None

    if other_user:
        total_points_other = calculate_total_user_score(other_user.id, db)
        current_champion, current_champion_flag, _ = get_tournament_champion(current_user.id, db)
        other_champion, other_champion_flag, _ = get_tournament_champion(other_user.id, db)

        all_teams = db.exec(select(Team)).all()
        teams_map = {team.id: team for team in all_teams}
        matches = db.exec(select(Match).order_by(Match.match_number)).all()
        current_predictions = db.exec(
            select(Prediction).where(Prediction.user_id == current_user.id)
        ).all()
        other_predictions = db.exec(
            select(Prediction).where(Prediction.user_id == other_user.id)
        ).all()
        current_predictions_map = {pred.match_id: pred for pred in current_predictions}
        other_predictions_map = {pred.match_id: pred for pred in other_predictions}

        for match in matches:
            current_team1, current_team2 = resolve_match_teams(match, current_user.id, db)
            other_team1, other_team2 = resolve_match_teams(match, other_user.id, db)
            actual_team1 = teams_map.get(match.team1_id)
            actual_team2 = teams_map.get(match.team2_id)
            current_prediction = current_predictions_map.get(match.id)
            other_prediction = other_predictions_map.get(match.id)

            actual_available = match.actual_team1_score is not None and match.actual_team2_score is not None
            current_scoring = {"points": 0, "status": "pending", "breakdown": []}
            other_scoring = {"points": 0, "status": "pending", "breakdown": []}

            if actual_available:
                if match.round.startswith("Group Stage"):
                    if current_prediction:
                        current_scoring = calculate_match_points(current_prediction, match)
                    if other_prediction:
                        other_scoring = calculate_match_points(other_prediction, match)
                else:
                    if current_prediction:
                        current_scoring = calculate_knockout_points(
                            current_prediction,
                            match,
                            current_team1.id if current_team1 else None,
                            current_team2.id if current_team2 else None
                        )
                    if other_prediction:
                        other_scoring = calculate_knockout_points(
                            other_prediction,
                            match,
                            other_team1.id if other_team1 else None,
                            other_team2.id if other_team2 else None
                        )

            match_cards.append({
                "match": match,
                "current_prediction": current_prediction,
                "other_prediction": other_prediction,
                "current_team1": current_team1,
                "current_team2": current_team2,
                "other_team1": other_team1,
                "other_team2": other_team2,
                "current_team1_flag_url": flag_url((current_team1 or actual_team1).code, 80) if (current_team1 or actual_team1) else None,
                "current_team2_flag_url": flag_url((current_team2 or actual_team2).code, 80) if (current_team2 or actual_team2) else None,
                "other_team1_flag_url": flag_url((other_team1 or actual_team1).code, 80) if (other_team1 or actual_team1) else None,
                "other_team2_flag_url": flag_url((other_team2 or actual_team2).code, 80) if (other_team2 or actual_team2) else None,
                "current_scoring": current_scoring,
                "other_scoring": other_scoring,
                "actual_available": actual_available
            })

    winner_label = None
    if other_user and total_points_other is not None:
        if total_points_current > total_points_other:
            winner_label = "You"
        elif total_points_other > total_points_current:
            winner_label = other_user.username
        else:
            winner_label = "Tied"

    return templates.TemplateResponse(
        "leaderboard_compare.html",
        {
            "request": request,
            "user": current_user,
            "teams": teams,
            "my_team_ids": my_team_ids,
            "selected_team_id": selected_team_id,
            "team_members": team_members,
            "selected_player_id": selected_player_id,
            "search_query": search_query,
            "search_results": search_results,
            "other_user": other_user,
            "total_points_current": total_points_current,
            "total_points_other": total_points_other,
            "winner_label": winner_label,
            "current_champion": current_champion,
            "current_champion_flag": current_champion_flag,
            "other_champion": other_champion,
            "other_champion_flag": other_champion_flag,
            "match_cards": match_cards
        }
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Settings page."""
    # Fetch all teams for favorite team dropdown
    all_teams = db.exec(select(Team).order_by(Team.name)).all()

    # Fetch user's team memberships
    user_teams = db.exec(select(UserTeamMembership).where(
        UserTeamMembership.user_id == current_user.id
    )).all()

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": current_user,
            "all_teams": all_teams,
            "user_teams": user_teams
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

@router.post("/settings/profile")
async def update_profile(
    email: str = Form(...),
    first_name: str = Form(None),
    last_name: str = Form(None),
    favorite_team_id: int = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Update user profile information."""
    # Validate email uniqueness (excluding current user)
    existing = db.exec(select(User).where(
        User.email == email,
        User.id != current_user.id
    )).first()

    if existing:
        return RedirectResponse(url="/settings?error=email_exists", status_code=303)

    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return RedirectResponse(url="/settings?error=invalid_email", status_code=303)

    # Update fields
    current_user.email = email
    current_user.first_name = first_name if first_name else None
    current_user.last_name = last_name if last_name else None
    current_user.favorite_team_id = favorite_team_id if favorite_team_id else None

    db.add(current_user)
    db.commit()

    return RedirectResponse(url="/settings?success=profile_updated", status_code=303)

@router.post("/settings/team/create")
async def create_team(
    team_name: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Create a new player team."""
    # Check if team name already exists
    existing_team = db.exec(select(PlayerTeam).where(PlayerTeam.name == team_name)).first()
    if existing_team:
        return RedirectResponse(url="/settings?error=team_exists", status_code=303)

    # Create team
    join_code = generate_join_code()
    new_team = PlayerTeam(name=team_name, join_code=join_code)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    # Add user as member via junction table
    membership = UserTeamMembership(
        user_id=current_user.id,
        player_team_id=new_team.id
    )
    db.add(membership)
    db.commit()

    return RedirectResponse(url="/settings?success=team_created", status_code=303)

@router.post("/settings/team/join")
async def join_team(
    join_code: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Join an existing player team via code."""
    team = db.exec(select(PlayerTeam).where(PlayerTeam.join_code == join_code)).first()
    if not team:
        return RedirectResponse(url="/settings?error=invalid_code", status_code=303)

    # Check if already a member
    existing = db.exec(select(UserTeamMembership).where(
        UserTeamMembership.user_id == current_user.id,
        UserTeamMembership.player_team_id == team.id
    )).first()

    if existing:
        return RedirectResponse(url="/settings?error=already_member", status_code=303)

    # Add membership
    membership = UserTeamMembership(
        user_id=current_user.id,
        player_team_id=team.id
    )
    db.add(membership)
    db.commit()

    return RedirectResponse(url="/settings?success=team_joined", status_code=303)

@router.post("/settings/team/leave/{team_id}")
async def leave_specific_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Leave a specific team."""
    membership = db.exec(select(UserTeamMembership).where(
        UserTeamMembership.user_id == current_user.id,
        UserTeamMembership.player_team_id == team_id
    )).first()

    if not membership:
        return RedirectResponse(url="/settings", status_code=303)

    db.delete(membership)
    db.commit()

    return RedirectResponse(url="/settings?success=left_team", status_code=303)

@router.get("/api/teams/search")
async def search_teams(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Search for teams (returns all teams, filtered by query)."""
    query = select(PlayerTeam)

    if q:
        query = query.where(PlayerTeam.name.contains(q))

    teams = db.exec(query.limit(20)).all()

    return [
        {
            "id": team.id,
            "name": team.name,
            "join_code": team.join_code,
            "member_count": len(team.memberships) if team.memberships else len(team.members),
            "total_points": team.total_points
        }
        for team in teams
    ]
