#!/usr/bin/env python3
"""
Generate Random User Predictions
---------------------------------
This script generates random predictions for all matches for a specific user.
Similar to simulate_full_tournament.py but creates USER PREDICTIONS instead of actual results.

Usage:
    python generate_user_picks.py <username>
    python generate_user_picks.py admin --clear  # Clear existing predictions first
"""

import sys
import random
from datetime import datetime
from sqlmodel import Session, select
from app.database import engine
from app.models import User, Match, Prediction, Team


def clear_user_predictions(user_id: int, db: Session) -> int:
    """
    Clear all existing predictions for a user.

    Args:
        user_id: User ID to clear predictions for
        db: Database session

    Returns:
        Number of predictions deleted
    """
    statement = select(Prediction).where(Prediction.user_id == user_id)
    predictions = db.exec(statement).all()

    count = len(predictions)
    for prediction in predictions:
        db.delete(prediction)

    db.commit()
    print(f"✓ Cleared {count} existing predictions for user")
    return count


def generate_random_score() -> tuple[int, int]:
    """
    Generate random match score.

    Returns:
        Tuple of (team1_score, team2_score) where each is 0-4
    """
    return random.randint(0, 4), random.randint(0, 4)


def generate_knockout_score() -> tuple[int, int]:
    """
    Generate random knockout match score (can be tied).

    Returns:
        Tuple of (team1_score, team2_score)
    """
    return random.randint(0, 3), random.randint(0, 3)


def get_resolved_teams_for_knockout(match: Match, user_id: int, db: Session) -> tuple[int, int]:
    """
    Resolve knockout match teams based on user's own predictions.
    Uses the knockout resolution logic to determine which teams the user predicted.

    Args:
        match: Knockout match with placeholders
        user_id: User ID to resolve predictions for
        db: Database session

    Returns:
        Tuple of (team1_id, team2_id) or (None, None) if can't resolve
    """
    from app.knockout import resolve_match_teams

    team1, team2 = resolve_match_teams(match, user_id, db)

    if team1 and team2:
        return team1.id, team2.id

    return None, None


def generate_user_predictions(username: str, clear_existing: bool = False):
    """
    Generate random predictions for all matches for a specific user.

    Args:
        username: Username to generate predictions for
        clear_existing: If True, clear existing predictions first
    """
    print(f"\n{'='*60}")
    print(f"🎯 Generating Random Predictions for User: {username}")
    print(f"{'='*60}\n")

    with Session(engine) as db:
        # Get or create user
        user_statement = select(User).where(User.username == username)
        user = db.exec(user_statement).first()

        if not user:
            print(f"❌ Error: User '{username}' not found in database")
            print(f"Available users:")
            users = db.exec(select(User)).all()
            for u in users:
                print(f"  - {u.username}")
            return

        print(f"✓ Found user: {user.username} (ID: {user.id})")

        # Clear existing predictions if requested
        if clear_existing:
            clear_user_predictions(user.id, db)

        # Get all matches in order
        matches_statement = select(Match).order_by(Match.match_number)
        matches = db.exec(matches_statement).all()

        print(f"\n{'='*60}")
        print(f"📝 Generating Predictions...")
        print(f"{'='*60}\n")

        predictions_created = 0
        predictions_updated = 0
        predictions_skipped = 0

        # Process matches by round
        for match in matches:
            is_group_stage = match.round.startswith("Group Stage")

            # Generate scores
            if is_group_stage:
                team1_score, team2_score = generate_random_score()
                penalty_winner_id = None
            else:
                # Knockout match - resolve teams based on user's group predictions
                team1_id, team2_id = get_resolved_teams_for_knockout(match, user.id, db)

                if team1_id is None or team2_id is None:
                    print(f"⚠️  Match #{match.match_number} ({match.round}): Teams not yet determined, skipping...")
                    predictions_skipped += 1
                    continue

                team1_score, team2_score = generate_knockout_score()

                # If tied, randomly select penalty winner
                if team1_score == team2_score:
                    penalty_winner_id = random.choice([team1_id, team2_id])
                else:
                    penalty_winner_id = None

            # Determine predicted winner
            if team1_score > team2_score:
                predicted_winner_id = match.team1_id
            elif team2_score > team1_score:
                predicted_winner_id = match.team2_id
            else:
                predicted_winner_id = None

            # Check if prediction already exists
            existing_pred_statement = select(Prediction).where(
                Prediction.user_id == user.id,
                Prediction.match_id == match.id
            )
            existing_prediction = db.exec(existing_pred_statement).first()

            if existing_prediction:
                # Update existing prediction
                existing_prediction.predicted_team1_score = team1_score
                existing_prediction.predicted_team2_score = team2_score
                existing_prediction.predicted_winner_id = predicted_winner_id
                if not is_group_stage:
                    existing_prediction.penalty_shootout_winner_id = penalty_winner_id
                existing_prediction.updated_at = datetime.utcnow()

                db.add(existing_prediction)
                predictions_updated += 1
                action = "Updated"
            else:
                # Create new prediction
                new_prediction = Prediction(
                    user_id=user.id,
                    match_id=match.id,
                    predicted_team1_score=team1_score,
                    predicted_team2_score=team2_score,
                    predicted_winner_id=predicted_winner_id,
                    penalty_shootout_winner_id=penalty_winner_id if not is_group_stage else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                db.add(new_prediction)
                predictions_created += 1
                action = "Created"

            # Get team names for display
            if is_group_stage:
                team1_name = match.team1.name if match.team1 else "TBD"
                team2_name = match.team2.name if match.team2 else "TBD"
            else:
                team1 = db.exec(select(Team).where(Team.id == team1_id)).first()
                team2 = db.exec(select(Team).where(Team.id == team2_id)).first()
                team1_name = team1.name if team1 else "TBD"
                team2_name = team2.name if team2 else "TBD"

            penalty_str = f" (Penalties: {db.exec(select(Team).where(Team.id == penalty_winner_id)).first().name})" if penalty_winner_id else ""

            print(f"{action:8} Match #{match.match_number:2} ({match.round:25}): {team1_name:20} {team1_score}-{team2_score} {team2_name:20}{penalty_str}")

            # Commit after each round to ensure knockout resolutions work
            if match.match_number in [48, 56, 60, 62, 63]:  # End of group stage, R16, QF, SF, 3rd place
                db.commit()

        # Final commit
        db.commit()

        print(f"\n{'='*60}")
        print(f"✅ PREDICTIONS GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"Created:  {predictions_created} new predictions")
        print(f"Updated:  {predictions_updated} existing predictions")
        print(f"Skipped:  {predictions_skipped} unresolved matches")
        print(f"Total:    {predictions_created + predictions_updated} predictions saved")
        print(f"\n✓ All predictions saved for user: {username}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_user_picks.py <username> [--clear]")
        print("\nOptions:")
        print("  username    Username to generate predictions for")
        print("  --clear     Clear existing predictions before generating new ones")
        print("\nExamples:")
        print("  python generate_user_picks.py admin")
        print("  python generate_user_picks.py john --clear")
        sys.exit(1)

    username = sys.argv[1]
    clear_existing = "--clear" in sys.argv

    try:
        generate_user_predictions(username, clear_existing)
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
