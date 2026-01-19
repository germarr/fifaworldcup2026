import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..models.match import Match
from ..models.fifa_team import FifaTeam
from ..models.stadium import Stadium

router = APIRouter(prefix="/bracket", tags=["bracket"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request, db: Session = Depends(get_session)):
    """Display group stage matches. State is managed client-side."""
    groups = {}

    # Get all group letters that have teams
    teams = db.exec(select(FifaTeam).where(FifaTeam.group_letter.isnot(None))).all()
    group_letters = sorted(set(t.group_letter for t in teams if t.group_letter))

    # Build match data for JavaScript
    match_data_js = {}

    for group_letter in group_letters:
        # Get matches for this group
        matches_query = select(Match).where(
            Match.round == "group_stage",
            Match.group_letter == group_letter
        ).order_by(Match.scheduled_datetime)
        matches = db.exec(matches_query).all()

        # Get teams for this group
        group_teams = db.exec(
            select(FifaTeam).where(FifaTeam.group_letter == group_letter)
        ).all()

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
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "scheduled_datetime": match.scheduled_datetime,
                "stadium": {
                    "name": stadium.name,
                    "city": stadium.city
                } if stadium else None
            })

            # Add to JS match data
            if match.match_number:
                match_data_js[match.match_number] = {
                    "id": match.id,
                    "group": group_letter,
                    "homeTeamId": match.home_team_id,
                    "awayTeamId": match.away_team_id
                }

        groups[group_letter] = {
            "matches": matches_data,
            "teams": [
                {
                    "id": t.id,
                    "name": t.name,
                    "country_code": t.country_code
                }
                for t in group_teams
            ]
        }

    return templates.TemplateResponse("bracket/groups.html", {
        "request": request,
        "groups": groups,
        "match_data_json": json.dumps(match_data_js)
    })


@router.get("", response_class=HTMLResponse)
async def bracket_page(request: Request, db: Session = Depends(get_session)):
    """Display full bracket page with groups, third-place ranking, and knockouts."""
    groups = {}

    # Get all group letters that have teams
    teams = db.exec(select(FifaTeam).where(FifaTeam.group_letter.isnot(None))).all()
    group_letters = sorted(set(t.group_letter for t in teams if t.group_letter))

    # Build match data and all teams for JavaScript
    match_data_js = {}
    all_teams = {}

    for team in teams:
        all_teams[team.id] = {
            "id": team.id,
            "name": team.name,
            "country_code": team.country_code,
            "group": team.group_letter
        }

    for group_letter in group_letters:
        # Get matches for this group
        matches = db.exec(
            select(Match).where(
                Match.round == "group_stage",
                Match.group_letter == group_letter
            ).order_by(Match.scheduled_datetime)
        ).all()

        # Get teams for this group
        group_teams = db.exec(
            select(FifaTeam).where(FifaTeam.group_letter == group_letter)
        ).all()

        # Build match data
        matches_data = []
        for match in matches:
            home_team = db.get(FifaTeam, match.home_team_id) if match.home_team_id else None
            away_team = db.get(FifaTeam, match.away_team_id) if match.away_team_id else None

            matches_data.append({
                "match_number": match.match_number,
                "home_team": home_team,
                "away_team": away_team,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
            })

            if match.match_number:
                match_data_js[match.match_number] = {
                    "group": group_letter,
                    "homeTeamId": match.home_team_id,
                    "awayTeamId": match.away_team_id,
                    "status": match.status,
                    "actualHomeScore": match.actual_home_score,
                    "actualAwayScore": match.actual_away_score
                }

        groups[group_letter] = {
            "matches": matches_data,
            "teams": [{"id": t.id, "name": t.name, "country_code": t.country_code} for t in group_teams]
        }

    # Add knockout matches to match_data_js
    knockout_matches = db.exec(
        select(Match).where(Match.round != "group_stage")
    ).all()
    for match in knockout_matches:
        if match.match_number:
            match_data_js[match.match_number] = {
                "round": match.round,
                "homeTeamId": match.home_team_id,
                "awayTeamId": match.away_team_id,
                "status": match.status,
                "actualHomeScore": match.actual_home_score,
                "actualAwayScore": match.actual_away_score,
                "actualWinnerTeamId": match.actual_winner_team_id
            }

    return templates.TemplateResponse("bracket/full.html", {
        "request": request,
        "groups": groups,
        "match_data_json": json.dumps(match_data_js),
        "all_teams_json": json.dumps(all_teams)
    })


@router.get("/print", response_class=HTMLResponse)
async def print_bracket(request: Request, db: Session = Depends(get_session)):
    """Print-friendly view. State comes from URL query parameter."""
    # Load all teams for reference
    teams = db.exec(select(FifaTeam)).all()
    teams_by_id = {t.id: {"id": t.id, "name": t.name, "country_code": t.country_code} for t in teams}

    return templates.TemplateResponse("bracket/print.html", {
        "request": request,
        "teams_json": json.dumps(teams_by_id)
    })
