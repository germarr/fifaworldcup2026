from datetime import datetime
from sqlmodel import Session, select

from ..models.bracket import Bracket
from ..models.prediction import Prediction


def get_or_create_user_bracket(db: Session, user_id: int) -> Bracket:
    bracket = db.exec(select(Bracket).where(Bracket.user_id == user_id)).first()
    if not bracket:
        bracket = Bracket(user_id=user_id)
        db.add(bracket)
        db.commit()
        db.refresh(bracket)

    missing_predictions = db.exec(
        select(Prediction).where(
            Prediction.user_id == user_id,
            Prediction.bracket_id.is_(None)
        )
    ).all()
    if missing_predictions:
        for prediction in missing_predictions:
            prediction.bracket_id = bracket.id
            prediction.updated_at = datetime.utcnow()
            db.add(prediction)
        db.commit()

    return bracket
