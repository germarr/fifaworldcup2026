from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.models import User, Match, Prediction, Team, GroupStanding
from app.database import get_session
from app.dependencies import get_current_user
from app.knockout import resolve_knockout_teams, resolve_match_teams
from app.scoring import calculate_match_points, calculate_knockout_points
from app.flags import flag_url

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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
        
        team1_flag_url = flag_url(team1.code, 80) if team1 else None
        team2_flag_url = flag_url(team2.code, 80) if team2 else None

        matches_with_teams.append({
            "match": match,
            "team1": team1,
            "team2": team2,
            "team1_flag_url": team1_flag_url,
            "team2_flag_url": team2_flag_url,
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
    from app.scoring import calculate_total_user_score
    
    # Use centralized score calculation
    total_score = calculate_total_user_score(current_user.id, db)
    
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
    
    for prediction, match, team1 in results:
        team2_statement = select(Team).where(Team.id == match.team2_id)
        team2 = db.exec(team2_statement).first()
        team1_flag_url = flag_url(team1.code, 80) if team1 else None
        team2_flag_url = flag_url(team2.code, 80) if team2 else None

        # Calculate points
        scoring_result = calculate_match_points(prediction, match)

        predictions_with_teams.append({
            "prediction": prediction,
            "match": match,
            "team1": team1,
            "team2": team2,
            "scoring": scoring_result,
            "team1_flag_url": team1_flag_url,
            "team2_flag_url": team2_flag_url,
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
        predicted_team1_flag_url = flag_url(predicted_team1.code, 40) if predicted_team1 else None
        predicted_team2_flag_url = flag_url(predicted_team2.code, 40) if predicted_team2 else None
        actual_team1_flag_url = flag_url(actual_team1.code, 40) if actual_team1 else None
        actual_team2_flag_url = flag_url(actual_team2.code, 40) if actual_team2 else None
        knockout_with_teams.append({
            "match": match,
            "predicted_team1": predicted_team1,
            "predicted_team2": predicted_team2,
            "actual_team1": actual_team1,
            "actual_team2": actual_team2,
            "prediction": prediction,
            "scoring": scoring_result,
            "predicted_team1_flag_url": predicted_team1_flag_url,
            "predicted_team2_flag_url": predicted_team2_flag_url,
            "actual_team1_flag_url": actual_team1_flag_url,
            "actual_team2_flag_url": actual_team2_flag_url,
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
            "team_flag_url": flag_url(team.code, 40),
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
    from app.scoring import calculate_total_user_score, get_champion_prediction
    
    # Use centralized score calculation
    total_score = calculate_total_user_score(current_user.id, db)
    
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

        scoring_result = {"points": 0}
        if prediction:
            scoring_result = calculate_knockout_points(
                prediction,
                match,
                team1.id if team1 else None,
                team2.id if team2 else None
            )

        matches.append({
            "match": match,
            "team1": team1,
            "team2": team2,
            "team1_flag_url": flag_url(team1.code, 40) if team1 else None,
            "team2_flag_url": flag_url(team2.code, 40) if team2 else None,
            "prediction": prediction,
            "scoring": scoring_result
        })

    # Get the predicted champion (winner of the final)
    champion, champion_flag_url = get_champion_prediction(current_user.id, db)

    return templates.TemplateResponse(
        "knockout_bracket.html",
        {
            "request": request,
            "user": current_user,
            "matches": matches,
            "champion": champion,
            "champion_flag_url": champion_flag_url,
            "total_score": total_score
        }
    )
