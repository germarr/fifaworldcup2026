from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.models import User, Match, Prediction, Team
from app.database import get_session
from app.dependencies import get_current_user
from app.knockout import resolve_knockout_teams, resolve_match_teams

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
        
        matches_with_teams.append({
            "match": match,
            "team1": team1,
            "team2": team2
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
    """View all user predictions."""
    # Get all user predictions with match and team data
    statement = (
        select(Prediction, Match, Team)
        .join(Match, Prediction.match_id == Match.id)
        .join(Team, Match.team1_id == Team.id)
        .where(Prediction.user_id == current_user.id)
        .order_by(Match.match_number)
    )

    results = db.exec(statement).all()

    # Also get team2 data separately since we can't double join easily
    predictions_with_teams = []
    for prediction, match, team1 in results:
        team2_statement = select(Team).where(Team.id == match.team2_id)
        team2 = db.exec(team2_statement).first()

        predictions_with_teams.append({
            "prediction": prediction,
            "match": match,
            "team1": team1,
            "team2": team2
        })

    return templates.TemplateResponse(
        "bracket_view.html",
        {
            "request": request,
            "user": current_user,
            "predictions": predictions_with_teams
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

    # Get group standings
    from app.standings import calculate_group_standings
    standings = calculate_group_standings(current_user.id, db)

    return templates.TemplateResponse(
        "knockout_bracket.html",
        {
            "request": request,
            "user": current_user,
            "matches": matches,
            "champion": champion,
            "standings": standings
        }
    )
