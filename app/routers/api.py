from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models import User, Match, Prediction, Team
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
    """Get group standings based on user predictions."""
    standings = calculate_group_standings(current_user.id, db)

    # Convert to JSON-serializable format
    response = {}
    for group_letter, standings_list in standings.items():
        response[group_letter] = [ts.to_dict() for ts in standings_list]

    return response


@router.post("/simulate-tournament")
async def simulate_tournament(
    current_user: User = Depends(get_current_user)
):
    """Simulate the full tournament and persist official results."""
    try:
        from simulate_full_tournament import simulate_full_tournament
        simulate_full_tournament()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {exc}"
        ) from exc

    return {"status": "success"}
