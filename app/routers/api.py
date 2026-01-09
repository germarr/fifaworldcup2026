from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models import User, Match, Prediction, Team, GroupStanding
from app.database import get_session
from app.dependencies import get_current_user
from app.standings import calculate_group_standings
from app.knockout import resolve_match_teams

router = APIRouter(prefix="/api")


class PredictionCreate(BaseModel):
    """Schema for creating a prediction."""
    match_id: int
    predicted_team1_score: int
    predicted_team2_score: int
    penalty_shootout_winner_id: Optional[int] = None


class PredictionBulkCreate(BaseModel):
    """Schema for creating multiple predictions at once."""
    predictions: List[PredictionCreate]


class MatchResponse(BaseModel):
    """Schema for match response."""
    id: int
    round: str
    match_number: int
    team1_id: Optional[int]
    team1_name: str
    team1_code: str
    team1_placeholder: Optional[str]
    team2_id: Optional[int]
    team2_name: str
    team2_code: str
    team2_placeholder: Optional[str]
    match_date: datetime
    is_finished: bool
    actual_team1_score: Optional[int] = None
    actual_team2_score: Optional[int] = None
    penalty_winner_id: Optional[int] = None


class PredictionResponse(BaseModel):
    """Schema for prediction response."""
    id: int
    match_id: int
    predicted_team1_score: int
    predicted_team2_score: int
    predicted_winner_id: Optional[int]
    penalty_shootout_winner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


@router.get("/matches", response_model=List[MatchResponse])
async def get_matches(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all matches with team information (resolves knockout placeholders)."""
    statement = select(Match).order_by(Match.match_number)
    matches = db.exec(statement).all()

    matches_response = []
    for match in matches:
        # Resolve teams (handles both direct IDs and placeholders)
        team1, team2 = resolve_match_teams(match, current_user.id, db)

        matches_response.append(
            MatchResponse(
                id=match.id,
                round=match.round,
                match_number=match.match_number,
                team1_id=team1.id if team1 else None,
                team1_name=team1.name if team1 else (match.team1_placeholder or "TBD"),
                team1_code=team1.code if team1 else "",
                team1_placeholder=match.team1_placeholder,
                team2_id=team2.id if team2 else None,
                team2_name=team2.name if team2 else (match.team2_placeholder or "TBD"),
                team2_code=team2.code if team2 else "",
                team2_placeholder=match.team2_placeholder,
                match_date=match.match_date,
                is_finished=match.is_finished
            )
        )

    return matches_response


@router.get("/predictions", response_model=List[PredictionResponse])
async def get_user_predictions(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all predictions for the current user."""
    statement = select(Prediction).where(Prediction.user_id == current_user.id)
    predictions = db.exec(statement).all()

    return predictions


@router.post("/predictions", response_model=PredictionResponse)
async def create_prediction(
    prediction_data: PredictionCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create or update a single prediction."""
    # Check if match exists
    match_statement = select(Match).where(Match.id == prediction_data.match_id)
    match = db.exec(match_statement).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    # Determine winner
    predicted_winner_id = None
    if prediction_data.predicted_team1_score > prediction_data.predicted_team2_score:
        predicted_winner_id = match.team1_id
    elif prediction_data.predicted_team2_score > prediction_data.predicted_team1_score:
        predicted_winner_id = match.team2_id
    # else: it's a tie, predicted_winner_id remains None

    # Check if prediction already exists
    existing_pred_statement = select(Prediction).where(
        Prediction.user_id == current_user.id,
        Prediction.match_id == prediction_data.match_id
    )
    existing_prediction = db.exec(existing_pred_statement).first()

    if existing_prediction:
        # Update existing prediction
        existing_prediction.predicted_team1_score = prediction_data.predicted_team1_score
        existing_prediction.predicted_team2_score = prediction_data.predicted_team2_score
        existing_prediction.predicted_winner_id = predicted_winner_id
        existing_prediction.penalty_shootout_winner_id = prediction_data.penalty_shootout_winner_id
        existing_prediction.updated_at = datetime.utcnow()

        db.add(existing_prediction)
        db.commit()
        db.refresh(existing_prediction)

        return existing_prediction
    else:
        # Create new prediction
        new_prediction = Prediction(
            user_id=current_user.id,
            match_id=prediction_data.match_id,
            predicted_team1_score=prediction_data.predicted_team1_score,
            predicted_team2_score=prediction_data.predicted_team2_score,
            predicted_winner_id=predicted_winner_id,
            penalty_shootout_winner_id=prediction_data.penalty_shootout_winner_id
        )

        db.add(new_prediction)
        db.commit()
        db.refresh(new_prediction)

        return new_prediction


@router.post("/predictions/bulk")
async def create_bulk_predictions(
    bulk_data: PredictionBulkCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create or update multiple predictions at once."""
    created_predictions = []

    for prediction_data in bulk_data.predictions:
        # Check if match exists
        match_statement = select(Match).where(Match.id == prediction_data.match_id)
        match = db.exec(match_statement).first()

        if not match:
            continue  # Skip invalid matches

        # Determine winner
        predicted_winner_id = None
        if prediction_data.predicted_team1_score > prediction_data.predicted_team2_score:
            predicted_winner_id = match.team1_id
        elif prediction_data.predicted_team2_score > prediction_data.predicted_team1_score:
            predicted_winner_id = match.team2_id

        # Check if prediction already exists
        existing_pred_statement = select(Prediction).where(
            Prediction.user_id == current_user.id,
            Prediction.match_id == prediction_data.match_id
        )
        existing_prediction = db.exec(existing_pred_statement).first()

        if existing_prediction:
            # Update existing prediction
            existing_prediction.predicted_team1_score = prediction_data.predicted_team1_score
            existing_prediction.predicted_team2_score = prediction_data.predicted_team2_score
            existing_prediction.predicted_winner_id = predicted_winner_id
            existing_prediction.penalty_shootout_winner_id = prediction_data.penalty_shootout_winner_id
            existing_prediction.updated_at = datetime.utcnow()

            db.add(existing_prediction)
            created_predictions.append(existing_prediction)
        else:
            # Create new prediction
            new_prediction = Prediction(
                user_id=current_user.id,
                match_id=prediction_data.match_id,
                predicted_team1_score=prediction_data.predicted_team1_score,
                predicted_team2_score=prediction_data.predicted_team2_score,
                predicted_winner_id=predicted_winner_id,
                penalty_shootout_winner_id=prediction_data.penalty_shootout_winner_id
            )

            db.add(new_prediction)
            created_predictions.append(new_prediction)

    db.commit()

    return {
        "status": "success",
        "count": len(created_predictions),
        "message": f"Created/updated {len(created_predictions)} predictions"
    }


@router.get("/standings")
async def get_standings(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get group standings based on user predictions first, then fallback to actual results if no predictions exist."""
    # Try to get user predictions first
    standings = calculate_group_standings(current_user.id, db)
    
    # If user has made predictions, return those
    if standings and any(len(teams) > 0 for teams in standings.values()):
        response = {}
        for group_letter, standings_list in standings.items():
            response[group_letter] = [ts.to_dict() for ts in standings_list]
        return response
    
    # Fallback to official/simulated standings if user has no predictions yet
    finished_group_matches = db.exec(
        select(Match).where(
            Match.round.like("Group Stage%"),
            Match.is_finished == True
        )
    ).all()
    
    # If there are actual tournament results, use those
    if finished_group_matches:
        official_standings = db.exec(select(GroupStanding)).all()
        if official_standings:
            # Organize by group
            response = {}
            for standing in official_standings:
                group = standing.group_letter
                if group not in response:
                    response[group] = []
                response[group].append({
                    "team_id": standing.team_id,
                    "team_name": standing.team.name,
                    "team_code": standing.team.code,
                    "team_flag_url": f"https://flagcdn.com/w40/{standing.team.code.lower()}.png",
                    "played": standing.played,
                    "won": standing.won,
                    "drawn": standing.drawn,
                    "lost": standing.lost,
                    "goals_for": standing.goals_for,
                    "goals_against": standing.goals_against,
                    "goal_difference": standing.goal_difference,
                    "points": standing.points,
                })
            
            # Sort each group
            for group in response:
                response[group].sort(
                    key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]),
                    reverse=True
                )
            return response
    
    # Return empty standings if nothing available
    return {}


@router.post("/simulate-tournament")
async def simulate_tournament(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Simulate the full tournament with actual results and populate user predictions.
    
    This:
    1. Generates actual match results (stored in matches.actual_*)
    2. Creates random predictions for the user (stored in predictions)
    3. Predictions can differ from actual results, allowing for scoring
    """
    try:
        from simulations.simulate_full_tournament import simulate_full_tournament, create_user_predictions_from_simulation
        simulate_full_tournament(db=db)  # Don't pass user_id - just set actual results
        create_user_predictions_from_simulation(current_user.id, db)  # Create random predictions for user
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {exc}"
        ) from exc

    return {"status": "success"}
