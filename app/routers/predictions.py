import random
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pydantic import BaseModel

from ..config import TEMPLATES_DIR
from ..database import get_session
from ..dependencies import require_user
from ..models.user import User
from ..models.match import Match
from ..models.prediction import Prediction
from ..models.fifa_team import FifaTeam
from ..services.standings import calculate_group_standings

router = APIRouter(prefix="/api/predictions", tags=["predictions"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class PredictionCreate(BaseModel):
    predicted_outcome: str
    predicted_home_score: Optional[int] = None
    predicted_away_score: Optional[int] = None
    predicted_winner_team_id: Optional[int] = None


def generate_random_score(outcome: str) -> tuple[int, int]:
    """Generate a random score based on the outcome."""
    if outcome == "home_win":
        home = random.randint(1, 4)
        away = random.randint(0, home - 1)
    elif outcome == "away_win":
        away = random.randint(1, 4)
        home = random.randint(0, away - 1)
    else:  # draw
        score = random.randint(0, 3)
        home = away = score
    return home, away


@router.post("/match/{match_id}")
async def submit_prediction(
    match_id: int,
    prediction_data: PredictionCreate,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    # Get match
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Check if match has started
    if match.scheduled_datetime <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Match has already started")

    # Generate random scores if not provided
    home_score = prediction_data.predicted_home_score
    away_score = prediction_data.predicted_away_score

    if home_score is None or away_score is None:
        home_score, away_score = generate_random_score(prediction_data.predicted_outcome)

    # Get or create prediction
    statement = select(Prediction).where(
        Prediction.user_id == current_user.id,
        Prediction.match_id == match_id
    )
    prediction = db.exec(statement).first()

    if prediction:
        # Update existing
        prediction.predicted_outcome = prediction_data.predicted_outcome
        prediction.predicted_home_score = home_score
        prediction.predicted_away_score = away_score
        prediction.predicted_winner_team_id = prediction_data.predicted_winner_team_id
        prediction.updated_at = datetime.utcnow()
    else:
        # Create new
        prediction = Prediction(
            user_id=current_user.id,
            match_id=match_id,
            predicted_outcome=prediction_data.predicted_outcome,
            predicted_home_score=home_score,
            predicted_away_score=away_score,
            predicted_winner_team_id=prediction_data.predicted_winner_team_id
        )
        db.add(prediction)

    db.commit()
    db.refresh(prediction)

    return {
        "id": prediction.id,
        "predicted_outcome": prediction.predicted_outcome,
        "predicted_home_score": prediction.predicted_home_score,
        "predicted_away_score": prediction.predicted_away_score
    }


@router.get("/standings/{group_letter}")
async def get_standings(
    group_letter: str,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    """Get calculated group standings based on user's predictions."""
    standings = calculate_group_standings(db, current_user.id, group_letter)
    return standings


@router.get("/match/{match_id}")
async def get_prediction(
    match_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    """Get user's prediction for a specific match."""
    statement = select(Prediction).where(
        Prediction.user_id == current_user.id,
        Prediction.match_id == match_id
    )
    prediction = db.exec(statement).first()

    if not prediction:
        return None

    return {
        "id": prediction.id,
        "predicted_outcome": prediction.predicted_outcome,
        "predicted_home_score": prediction.predicted_home_score,
        "predicted_away_score": prediction.predicted_away_score,
        "predicted_winner_team_id": prediction.predicted_winner_team_id,
        "points_earned": prediction.points_earned
    }


@router.delete("/match/{match_id}")
async def delete_prediction(
    match_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_session)
):
    """Delete a prediction for a specific match."""
    # Get match to verify it exists and hasn't started
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Check if match has started
    if match.scheduled_datetime <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot delete prediction for a match that has started")

    # Find and delete prediction
    statement = select(Prediction).where(
        Prediction.user_id == current_user.id,
        Prediction.match_id == match_id
    )
    prediction = db.exec(statement).first()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    db.delete(prediction)
    db.commit()

    return {"message": "Prediction deleted successfully"}
