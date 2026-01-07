from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.models import User, Match, Prediction, Team, GroupStanding
from app.database import get_session
from app.dependencies import get_current_user
from app.knockout import resolve_knockout_teams, resolve_match_teams
from app.scoring import calculate_match_points, calculate_knockout_points

router = APIRouter()
templates = Jinja2Templates(directory="templates")

FIFA_TO_FLAGCDN = {
    "ARG": "ar",
    "AUS": "au",
    "BEL": "be",
    "BRA": "br",
    "CAN": "ca",
    "CMR": "cm",
    "CRC": "cr",
    "CRO": "hr",
    "DEN": "dk",
    "ECU": "ec",
    "ENG": "gb-eng",
    "ESP": "es",
    "FRA": "fr",
    "GER": "de",
    "GHA": "gh",
    "IRN": "ir",
    "JPN": "jp",
    "KOR": "kr",
    "KSA": "sa",
    "MAR": "ma",
    "MEX": "mx",
    "NED": "nl",
    "POL": "pl",
    "POR": "pt",
    "QAT": "qa",
    "SEN": "sn",
    "SRB": "rs",
    "SUI": "ch",
    "TUN": "tn",
    "URU": "uy",
    "USA": "us",
    "WAL": "gb-wls",
}


@router.get("/bracket", response_class=HTMLResponse)
async def bracket_select(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Bracket selection page - both 'all at once' and 'individual' modes."""
    # Get all matches
    statement = select(Match).order_by(Match.match_number)
    matches = db.exec(statement).all()

    # Get user's existing predictions
    pred_statement = select(Prediction).where(Prediction.user_id == current_user.id)
    predictions = db.exec(pred_statement).all()

    # Create a dict of predictions by match_id for easy lookup
    predictions_dict = {pred.match_id: pred for pred in predictions}

    # Resolve knockout team placeholders and create matches_with_teams list
    matches_with_teams = []
    for match in matches:
        if match.team1_placeholder or match.team2_placeholder:
            # This is a knockout match with placeholders - resolve the actual teams
            team1, team2 = resolve_match_teams(match, current_user.id, db)
        else:
            team1 = match.team1
            team2 = match.team2
        
        team1_flag_code = FIFA_TO_FLAGCDN.get(team1.code) if team1 else None
        team2_flag_code = FIFA_TO_FLAGCDN.get(team2.code) if team2 else None

        matches_with_teams.append({
            "match": match,
            "team1": team1,
            "team2": team2,
            "team1_flag_url": f"https://flagcdn.com/w80/{team1_flag_code}.png" if team1_flag_code else None,
            "team2_flag_url": f"https://flagcdn.com/w80/{team2_flag_code}.png" if team2_flag_code else None,
        })

    return templates.TemplateResponse(
        "bracket_select.html",
        {
            "request": request,
            "user": current_user,
            "matches_with_teams": matches_with_teams,
            "predictions": predictions_dict
        }
    )


@router.get("/bracket/view", response_class=HTMLResponse)
async def bracket_view(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """View all user predictions with scoring."""
    # Get all user predictions with match and team data
    statement = (
        select(Prediction, Match, Team)
        .join(Match, Prediction.match_id == Match.id)
        .join(Team, Match.team1_id == Team.id)
        .where(Prediction.user_id == current_user.id)
        .order_by(Match.match_number)
    )

    results = db.exec(statement).all()

    predictions_with_teams = []
    total_score = 0
    
    for prediction, match, team1 in results:
        team2_statement = select(Team).where(Team.id == match.team2_id)
        team2 = db.exec(team2_statement).first()
        team1_flag = FIFA_TO_FLAGCDN.get(team1.code) if team1 else None
        team2_flag = FIFA_TO_FLAGCDN.get(team2.code) if team2 else None

        # Calculate points
        scoring_result = calculate_match_points(prediction, match)
        total_score += scoring_result["points"]

        predictions_with_teams.append({
            "prediction": prediction,
            "match": match,
            "team1": team1,
            "team2": team2,
            "scoring": scoring_result,
            "team1_flag_url": f"https://flagcdn.com/w80/{team1_flag}.png" if team1_flag else None,
            "team2_flag_url": f"https://flagcdn.com/w80/{team2_flag}.png" if team2_flag else None,
        })

    knockout_statement = select(Match).where(~Match.round.like("Group Stage%")).order_by(Match.match_number)
    knockout_matches = db.exec(knockout_statement).all()
    knockout_predictions_statement = select(Prediction).where(Prediction.user_id == current_user.id)
    knockout_predictions = db.exec(knockout_predictions_statement).all()
    knockout_predictions_dict = {pred.match_id: pred for pred in knockout_predictions}

    knockout_with_teams = []
    for match in knockout_matches:
        predicted_team1, predicted_team2 = resolve_match_teams(match, current_user.id, db)
        actual_team1 = match.team1 if match.team1_id else None
        actual_team2 = match.team2 if match.team2_id else None
        prediction = knockout_predictions_dict.get(match.id)
        scoring_result = {"points": 0, "breakdown": [], "status": "pending"}
        if prediction:
            scoring_result = calculate_knockout_points(
                prediction,
                match,
                predicted_team1.id if predicted_team1 else None,
                predicted_team2.id if predicted_team2 else None
            )
        predicted_team1_flag = FIFA_TO_FLAGCDN.get(predicted_team1.code) if predicted_team1 else None
        predicted_team2_flag = FIFA_TO_FLAGCDN.get(predicted_team2.code) if predicted_team2 else None
        actual_team1_flag = FIFA_TO_FLAGCDN.get(actual_team1.code) if actual_team1 else None
        actual_team2_flag = FIFA_TO_FLAGCDN.get(actual_team2.code) if actual_team2 else None
        knockout_with_teams.append({
            "match": match,
            "predicted_team1": predicted_team1,
            "predicted_team2": predicted_team2,
            "actual_team1": actual_team1,
            "actual_team2": actual_team2,
            "prediction": prediction,
            "scoring": scoring_result,
            "predicted_team1_flag_url": f"https://flagcdn.com/w40/{predicted_team1_flag}.png" if predicted_team1_flag else None,
            "predicted_team2_flag_url": f"https://flagcdn.com/w40/{predicted_team2_flag}.png" if predicted_team2_flag else None,
            "actual_team1_flag_url": f"https://flagcdn.com/w40/{actual_team1_flag}.png" if actual_team1_flag else None,
            "actual_team2_flag_url": f"https://flagcdn.com/w40/{actual_team2_flag}.png" if actual_team2_flag else None,
        })

    standings_statement = (
        select(GroupStanding, Team)
        .join(Team, GroupStanding.team_id == Team.id)
    )
    standings_results = db.exec(standings_statement).all()
    standings_by_group = {}

    for standing, team in standings_results:
        group_letter = standing.group_letter or team.group
        if not group_letter:
            continue

        standings_by_group.setdefault(group_letter, []).append({
            "team_name": team.name,
            "team_code": team.code,
            "played": standing.played,
            "won": standing.won,
            "drawn": standing.drawn,
            "lost": standing.lost,
            "goals_for": standing.goals_for,
            "goals_against": standing.goals_against,
            "goal_difference": standing.goal_difference,
            "points": standing.points,
        })

    for group_letter, standings_list in standings_by_group.items():
        standings_list.sort(
            key=lambda x: (x["points"], x["goal_difference"], x["goals_for"], x["team_name"]),
            reverse=True
        )

    return templates.TemplateResponse(
        "bracket_view.html",
        {
            "request": request,
            "user": current_user,
            "predictions": predictions_with_teams,
            "total_score": total_score,
            "knockout_matches": knockout_with_teams,
            "standings": standings_by_group
        }
    )


@router.get("/bracket/knockout", response_class=HTMLResponse)
async def knockout_bracket(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Visual knockout bracket tree with predictions."""
    # Get all knockout matches (not group stage)
    statement = select(Match).where(~Match.round.like("Group Stage%")).order_by(Match.match_number)
    knockout_matches = db.exec(statement).all()

    # Get user predictions for knockout matches
    pred_statement = select(Prediction).where(Prediction.user_id == current_user.id)
    predictions = db.exec(pred_statement).all()
    predictions_dict = {pred.match_id: pred for pred in predictions}

    # Resolve teams for each match
    matches = []
    for match in knockout_matches:
        team1, team2 = resolve_match_teams(match, current_user.id, db)

        # Get prediction if exists
        prediction = predictions_dict.get(match.id)

        matches.append({
            "match": match,
            "team1": team1,
            "team2": team2,
            "prediction": prediction
        })

    # Get the predicted champion (winner of the final)
    final_item = next((m for m in matches if m["match"].round == "Final"), None)
    champion = None
    if final_item and final_item["prediction"]:
        prediction = final_item["prediction"]
        if prediction.predicted_team1_score > prediction.predicted_team2_score:
            champion = final_item["team1"]
        elif prediction.predicted_team2_score > prediction.predicted_team1_score:
            champion = final_item["team2"]
        elif prediction.penalty_shootout_winner_id:
            champ_statement = select(Team).where(Team.id == prediction.penalty_shootout_winner_id)
            champion = db.exec(champ_statement).first()

    # Get group standings (Actual)
    standings_statement = (
        select(GroupStanding, Team)
        .join(Team, GroupStanding.team_id == Team.id)
    )
    standings_results = db.exec(standings_statement).all()
    standings_by_group = {}

    # Helper class to match the template structure expected by calculate_group_standings
    class StandingWrapper:
        def __init__(self, standing, team):
            self.team = team
            self.points = standing.points
            # Add other fields if needed by the template, but 'team' and 'points' are the main ones used in the simple list

    for standing, team in standings_results:
        group_letter = standing.group_letter or team.group
        if not group_letter:
            continue
        
        # Create a wrapper object that matches the structure expected by the template
        # The template expects an object with .team and .points attributes
        wrapper = StandingWrapper(standing, team)
        standings_by_group.setdefault(group_letter, []).append(wrapper)

    # Sort standings
    for group_letter, standings_list in standings_by_group.items():
        # Sort by points DESC
        standings_list.sort(key=lambda x: x.points, reverse=True)

    return templates.TemplateResponse(
        "knockout_bracket.html",
        {
            "request": request,
            "user": current_user,
            "matches": matches,
            "champion": champion,
            "standings": standings_by_group
        }
    )
