from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import datetime
import secrets
import string
from typing import Dict, List, Any, Optional
from app.models import User, Match, Team, QuickGame, QuickGameMatch, QuickGameGroupTiebreaker
from app.database import get_session
from app.dependencies import get_current_user_optional
from app.flags import flag_url

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def generate_game_code() -> str:
    """Generate a unique 8-character game code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


@router.get("/quickgame", response_class=HTMLResponse)
async def quickgame_start(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Quick game landing page - start a new game or view existing games."""
    # Get user's recent quick games (if logged in)
    recent_games = []
    if current_user:
        statement = (
            select(QuickGame)
            .where(QuickGame.user_id == current_user.id)
            .order_by(QuickGame.created_at.desc())
            .limit(10)
        )
        recent_games = db.exec(statement).all()

    # Get champion names for completed games
    games_with_champions = []
    for game in recent_games:
        champion_name = None
        if game.champion_team_id:
            champion_team = db.get(Team, game.champion_team_id)
            if champion_team:
                champion_name = champion_team.name

        games_with_champions.append({
            "game": game,
            "champion_name": champion_name
        })

    return templates.TemplateResponse(
        "quickgame_start.html",
        {
            "request": request,
            "user": current_user,
            "recent_games": games_with_champions
        }
    )


@router.post("/quickgame/new")
async def create_new_quickgame(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Create a new quick game instance."""
    # Generate unique game code
    game_code = generate_game_code()

    # Ensure uniqueness
    while db.exec(select(QuickGame).where(QuickGame.game_code == game_code)).first():
        game_code = generate_game_code()

    # Create new quick game (user_id can be NULL for anonymous)
    quick_game = QuickGame(
        user_id=current_user.id if current_user else None,
        game_code=game_code,
        is_completed=False
    )

    db.add(quick_game)
    db.commit()
    db.refresh(quick_game)

    return {"game_id": quick_game.id, "game_code": quick_game.game_code}


@router.get("/quickgame/{game_code}/groups", response_class=HTMLResponse)
async def quickgame_groups(
    request: Request,
    game_code: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Group stage selection page."""
    # Get the quick game
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    # Allow access if: 1) game is anonymous, 2) user owns the game, or 3) viewing completed game
    if quick_game.user_id is not None and current_user and quick_game.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this game")

    # Get all group stage matches
    matches_statement = (
        select(Match)
        .where(Match.round.like("Group Stage%"))
        .order_by(Match.match_number)
    )
    matches = db.exec(matches_statement).all()

    # Get existing selections for this game
    existing_selections = {}
    for qgm in quick_game.matches:
        existing_selections[qgm.match_id] = qgm.result

    # Organize matches by group
    groups = {}
    for match in matches:
        # Extract group letter from round (e.g., "Group Stage - Group A" -> "A")
        group_letter = match.round.split("Group ")[-1] if "Group " in match.round else "?"

        if group_letter not in groups:
            groups[group_letter] = []

        match_data = {
            "match": match,
            "team1": match.team1,
            "team2": match.team2,
            "team1_flag": flag_url(match.team1.code, 80) if match.team1 else None,
            "team2_flag": flag_url(match.team2.code, 80) if match.team2 else None,
            "selected_result": existing_selections.get(match.id)
        }
        groups[group_letter].append(match_data)

    # Sort groups by letter
    sorted_groups = dict(sorted(groups.items()))

    tiebreakers_statement = select(QuickGameGroupTiebreaker).where(
        QuickGameGroupTiebreaker.quick_game_id == quick_game.id
    )
    tiebreakers = db.exec(tiebreakers_statement).all()
    tiebreakers_map = {
        tb.group_letter: {
            "first_team_id": tb.first_team_id,
            "second_team_id": tb.second_team_id
        }
        for tb in tiebreakers
    }

    return templates.TemplateResponse(
        "quickgame_groups.html",
        {
            "request": request,
            "user": current_user,
            "game_code": game_code,
            "groups": sorted_groups,
            "tiebreakers": tiebreakers_map,
            "quick_game": quick_game
        }
    )


@router.post("/quickgame/{game_code}/match/{match_id}")
async def save_match_result(
    game_code: str,
    match_id: int,
    result: Dict[str, str],
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Save a match result (team1, team2, or draw)."""
    # Get the quick game
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    # Allow editing if: 1) game is anonymous, or 2) user owns the game
    if quick_game.user_id is not None and (not current_user or quick_game.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate match exists
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Validate result value
    result_value = result.get("result")
    if result_value not in ["team1", "team2", "draw"]:
        raise HTTPException(status_code=400, detail="Invalid result value")

    # Check if result already exists
    existing = db.exec(
        select(QuickGameMatch)
        .where(QuickGameMatch.quick_game_id == quick_game.id)
        .where(QuickGameMatch.match_id == match_id)
    ).first()

    if existing:
        # Update existing
        existing.result = result_value
        db.add(existing)
    else:
        # Create new
        quick_game_match = QuickGameMatch(
            quick_game_id=quick_game.id,
            match_id=match_id,
            result=result_value
        )
        db.add(quick_game_match)

    db.commit()

    return {"status": "success", "match_id": match_id, "result": result_value}


@router.get("/quickgame/{game_code}/standings")
async def get_group_standings(
    game_code: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Calculate and return group standings based on quick game results."""
    # Get the quick game
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    # Calculate standings (implemented in next function)
    standings = calculate_quick_game_standings(quick_game, db)

    return standings


def calculate_quick_game_standings(quick_game: QuickGame, db: Session) -> Dict:
    """Calculate group standings from quick game match results."""
    # Get all group stage match results for this game
    results_statement = (
        select(QuickGameMatch, Match)
        .join(Match, QuickGameMatch.match_id == Match.id)
        .where(QuickGameMatch.quick_game_id == quick_game.id)
        .where(Match.round.like("Group Stage%"))
    )
    results = db.exec(results_statement).all()

    # Initialize standings for each group
    groups_standings = {}

    for qgm, match in results:
        # Extract group letter
        group_letter = match.round.split("Group ")[-1] if "Group " in match.round else "?"

        if group_letter not in groups_standings:
            groups_standings[group_letter] = {}

        # Initialize team stats if not exists
        for team in [match.team1, match.team2]:
            if not team:
                continue

            if team.id not in groups_standings[group_letter]:
                groups_standings[group_letter][team.id] = {
                    "team_id": team.id,
                    "team_name": team.name,
                    "team_code": team.code,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "points": 0
                }

        # Update stats based on result
        if match.team1 and match.team2:
            team1_stats = groups_standings[group_letter][match.team1.id]
            team2_stats = groups_standings[group_letter][match.team2.id]

            team1_stats["played"] += 1
            team2_stats["played"] += 1

            if qgm.result == "team1":
                team1_stats["won"] += 1
                team1_stats["points"] += 3
                team2_stats["lost"] += 1
            elif qgm.result == "team2":
                team2_stats["won"] += 1
                team2_stats["points"] += 3
                team1_stats["lost"] += 1
            else:  # draw
                team1_stats["drawn"] += 1
                team1_stats["points"] += 1
                team2_stats["drawn"] += 1
                team2_stats["points"] += 1

    tiebreakers_statement = select(QuickGameGroupTiebreaker).where(
        QuickGameGroupTiebreaker.quick_game_id == quick_game.id
    )
    tiebreakers = {
        tb.group_letter: tb for tb in db.exec(tiebreakers_statement).all()
    }

    # Sort each group by points (desc), then wins (desc)
    sorted_standings = {}
    for group, teams in groups_standings.items():
        sorted_teams = sorted(
            teams.values(),
            key=lambda x: (x["points"], x["won"]),
            reverse=True
        )
        sorted_teams = apply_group_tiebreaker(sorted_teams, tiebreakers.get(group))
        sorted_standings[group] = sorted_teams

    return sorted_standings


def build_quickgame_placeholder_resolution(quick_game: QuickGame, standings: Dict[str, List[Dict[str, Any]]], db: Session) -> Dict[str, Optional[Team]]:
    placeholder_resolution: Dict[str, Optional[Team]] = {}

    for group, teams in standings.items():
        if teams:
            first_team = db.get(Team, teams[0]["team_id"])
            if first_team:
                placeholder_resolution[f"1{group}"] = first_team

        if len(teams) > 1:
            second_team = db.get(Team, teams[1]["team_id"])
            if second_team:
                placeholder_resolution[f"2{group}"] = second_team

    existing_selections = {
        qgm.match_id: {
            "result": qgm.result,
            "advancing_team_id": qgm.advancing_team_id
        }
        for qgm in quick_game.matches
    }

    knockout_matches_statement = (
        select(Match)
        .where(~Match.round.like("Group Stage%"))
        .order_by(Match.match_number)
    )
    knockout_matches = db.exec(knockout_matches_statement).all()

    for match in knockout_matches:
        team1 = placeholder_resolution.get(match.team1_placeholder) if match.team1_placeholder else None
        team2 = placeholder_resolution.get(match.team2_placeholder) if match.team2_placeholder else None

        selection = existing_selections.get(match.id)
        if not selection:
            continue

        winner_team = None
        winner_team_id = selection.get("advancing_team_id")

        if winner_team_id:
            winner_team = db.get(Team, winner_team_id)
        elif selection.get("result") == "team1":
            winner_team = team1
        elif selection.get("result") == "team2":
            winner_team = team2

        placeholder_resolution[f"W{match.match_number}"] = winner_team

        loser_team = None
        if team1 and team2 and winner_team:
            loser_team = team2 if winner_team.id == team1.id else team1
        elif selection.get("result") == "team1" and team2:
            loser_team = team2
        elif selection.get("result") == "team2" and team1:
            loser_team = team1

        placeholder_resolution[f"L{match.match_number}"] = loser_team

    return placeholder_resolution


def apply_group_tiebreaker(teams: List[Dict[str, Any]], tiebreaker: Optional[QuickGameGroupTiebreaker]) -> List[Dict[str, Any]]:
    if not tiebreaker or len(teams) < 2:
        return teams

    ordered = list(teams)
    team_map = {team["team_id"]: team for team in ordered}

    def move_to_index(team_id: Optional[int], index: int) -> None:
        if team_id is None:
            return
        team = team_map.get(team_id)
        if not team:
            return
        current_index = next((i for i, item in enumerate(ordered) if item["team_id"] == team_id), None)
        if current_index is None or current_index == index:
            return
        if ordered[index]["points"] != team["points"]:
            return
        ordered.pop(current_index)
        ordered.insert(index, team)

    if ordered[0]["points"] == ordered[1]["points"]:
        move_to_index(tiebreaker.first_team_id, 0)
        if tiebreaker.second_team_id != tiebreaker.first_team_id:
            move_to_index(tiebreaker.second_team_id, 1)
    elif len(ordered) >= 3 and ordered[1]["points"] == ordered[2]["points"]:
        move_to_index(tiebreaker.second_team_id, 1)

    return ordered


@router.post("/quickgame/{game_code}/tiebreaker")
async def save_group_tiebreaker(
    game_code: str,
    payload: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Save group tie-breaker selection for a quick game."""
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    if quick_game.user_id is not None and (not current_user or quick_game.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    group = payload.get("group")
    first_team_id = payload.get("first_team_id")
    second_team_id = payload.get("second_team_id")

    if not group or len(group) != 1:
        raise HTTPException(status_code=400, detail="Invalid group")

    existing = db.exec(
        select(QuickGameGroupTiebreaker)
        .where(QuickGameGroupTiebreaker.quick_game_id == quick_game.id)
        .where(QuickGameGroupTiebreaker.group_letter == group)
    ).first()

    if existing:
        existing.first_team_id = first_team_id
        existing.second_team_id = second_team_id
        db.add(existing)
    else:
        db.add(QuickGameGroupTiebreaker(
            quick_game_id=quick_game.id,
            group_letter=group,
            first_team_id=first_team_id,
            second_team_id=second_team_id
        ))

    db.commit()

    return {"status": "success", "group": group}


@router.get("/quickgame/{game_code}/knockout", response_class=HTMLResponse)
async def quickgame_knockout(
    request: Request,
    game_code: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Knockout stage selection page."""
    # Get the quick game
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    # Get group standings to determine knockout teams
    standings = calculate_quick_game_standings(quick_game, db)

    # Get knockout matches
    knockout_matches_statement = (
        select(Match)
        .where(~Match.round.like("Group Stage%"))
        .order_by(Match.match_number)
    )
    knockout_matches = db.exec(knockout_matches_statement).all()

    # Resolve knockout bracket teams based on group standings and quick game selections
    placeholder_resolution = build_quickgame_placeholder_resolution(quick_game, standings, db)

    existing_selections = {
        qgm.match_id: {
            "result": qgm.result,
            "advancing_team_id": qgm.advancing_team_id
        }
        for qgm in quick_game.matches
    }

    knockout_data = []
    for match in knockout_matches:
        team1 = placeholder_resolution.get(match.team1_placeholder) if match.team1_placeholder else None
        team2 = placeholder_resolution.get(match.team2_placeholder) if match.team2_placeholder else None

        match_info = {
            "match": match,
            "team1": team1,
            "team2": team2,
            "team1_flag": flag_url(team1.code, 80) if team1 else None,
            "team2_flag": flag_url(team2.code, 80) if team2 else None,
            "selected_result": existing_selections.get(match.id)
        }

        knockout_data.append(match_info)

    return templates.TemplateResponse(
        "quickgame_knockout.html",
        {
            "request": request,
            "user": current_user,
            "game_code": game_code,
            "knockout_matches": knockout_data,
            "standings": standings,
            "quick_game": quick_game
        }
    )


@router.post("/quickgame/{game_code}/knockout/{match_id}")
async def save_knockout_result(
    game_code: str,
    match_id: int,
    result: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Save knockout match result with advancing team."""
    # Get the quick game
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    # Allow editing if: 1) game is anonymous, or 2) user owns the game
    if quick_game.user_id is not None and (not current_user or quick_game.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate match exists
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    result_value = result.get("result")
    advancing_team_id = result.get("advancing_team_id")

    if result_value not in ["team1", "team2", "draw"]:
        raise HTTPException(status_code=400, detail="Invalid result value")

    # For knockout, if draw, must specify advancing team
    if result_value == "draw" and not advancing_team_id:
        raise HTTPException(status_code=400, detail="Must specify advancing team for draw")

    # Check if result already exists
    existing = db.exec(
        select(QuickGameMatch)
        .where(QuickGameMatch.quick_game_id == quick_game.id)
        .where(QuickGameMatch.match_id == match_id)
    ).first()

    if existing:
        existing.result = result_value
        existing.advancing_team_id = advancing_team_id
        db.add(existing)
    else:
        quick_game_match = QuickGameMatch(
            quick_game_id=quick_game.id,
            match_id=match_id,
            result=result_value,
            advancing_team_id=advancing_team_id
        )
        db.add(quick_game_match)

    db.commit()

    return {"status": "success", "match_id": match_id, "result": result_value}


@router.post("/quickgame/{game_code}/complete")
async def complete_quickgame(
    game_code: str,
    payload: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Mark quick game as completed with the champion."""
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    # Allow completing if: 1) game is anonymous, or 2) user owns the game
    if quick_game.user_id is not None and (not current_user or quick_game.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    champion_team_id = payload.get("champion_team_id")
    if not champion_team_id:
        raise HTTPException(status_code=400, detail="Missing champion_team_id")

    quick_game.is_completed = True
    quick_game.champion_team_id = champion_team_id
    quick_game.completed_at = datetime.utcnow()

    db.add(quick_game)
    db.commit()

    return {"status": "success", "game_code": game_code}


@router.get("/quickgame/{game_code}/results", response_class=HTMLResponse)
async def quickgame_results(
    request: Request,
    game_code: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Printable results page."""
    statement = select(QuickGame).where(QuickGame.game_code == game_code)
    quick_game = db.exec(statement).first()

    if not quick_game:
        raise HTTPException(status_code=404, detail="Quick game not found")

    # Get group standings
    standings = calculate_quick_game_standings(quick_game, db)

    # Get all match results
    results_statement = (
        select(QuickGameMatch, Match)
        .join(Match, QuickGameMatch.match_id == Match.id)
        .where(QuickGameMatch.quick_game_id == quick_game.id)
        .order_by(Match.match_number)
    )
    results = db.exec(results_statement).all()

    placeholder_resolution = build_quickgame_placeholder_resolution(quick_game, standings, db)

    final_winner_id = None
    for qgm, match in results:
        if match.round == "Final":
            if qgm.advancing_team_id:
                final_winner_id = qgm.advancing_team_id
            elif qgm.result == "team1" and match.team1_id:
                final_team = placeholder_resolution.get(match.team1_placeholder) if match.team1_placeholder else match.team1
                final_winner_id = final_team.id if final_team else None
            elif qgm.result == "team2" and match.team2_id:
                final_team = placeholder_resolution.get(match.team2_placeholder) if match.team2_placeholder else match.team2
                final_winner_id = final_team.id if final_team else None
            break

    champion_team_id = final_winner_id or quick_game.champion_team_id
    champion = db.get(Team, champion_team_id) if champion_team_id else None

    # Organize by round
    rounds = {}
    for qgm, match in results:
        advancing_team = db.get(Team, qgm.advancing_team_id) if qgm.advancing_team_id else None
        round_name = match.round
        if round_name not in rounds:
            rounds[round_name] = []

        team1 = match.team1
        team2 = match.team2
        if not match.round.startswith("Group Stage"):
            team1 = placeholder_resolution.get(match.team1_placeholder) if match.team1_placeholder else None
            team2 = placeholder_resolution.get(match.team2_placeholder) if match.team2_placeholder else None

        rounds[round_name].append({
            "match": match,
            "result": qgm.result,
            "team1": team1,
            "team2": team2,
            "advancing_team": advancing_team
        })

    return templates.TemplateResponse(
        "quickgame_results.html",
        {
            "request": request,
            "user": current_user,
            "game_code": game_code,
            "quick_game": quick_game,
            "champion": champion,
            "champion_flag": flag_url(champion.code, 160) if champion else None,
            "standings": standings,
            "rounds": rounds,
            "flag_url": flag_url
        }
    )
