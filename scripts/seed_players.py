"""Seed test players with random predictions."""
import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.user import User
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.fifa_team import FifaTeam
from app.services.auth import hash_password

# Test user names
TEST_USERS = [
    {"display_name": "Soccer Fan 1", "email": "fan1@test.com"},
    {"display_name": "Football Guru", "email": "guru@test.com"},
    {"display_name": "World Cup Expert", "email": "expert@test.com"},
    {"display_name": "Bracket Master", "email": "master@test.com"},
    {"display_name": "Prediction Pro", "email": "pro@test.com"},
    {"display_name": "Game Analyst", "email": "analyst@test.com"},
    {"display_name": "Sports Buff", "email": "buff@test.com"},
    {"display_name": "Match Watcher", "email": "watcher@test.com"},
    {"display_name": "Goal Seeker", "email": "seeker@test.com"},
    {"display_name": "Cup Dreamer", "email": "dreamer@test.com"},
]


def generate_random_prediction(match: Match) -> dict:
    """Generate a random prediction for a match."""
    outcomes = ["home_win", "away_win", "draw"]
    outcome = random.choice(outcomes)

    # Generate scores based on outcome
    if outcome == "home_win":
        home_score = random.randint(1, 4)
        away_score = random.randint(0, home_score - 1)
    elif outcome == "away_win":
        away_score = random.randint(1, 4)
        home_score = random.randint(0, away_score - 1)
    else:
        score = random.randint(0, 3)
        home_score = away_score = score

    return {
        "predicted_outcome": outcome,
        "predicted_home_score": home_score,
        "predicted_away_score": away_score,
        "predicted_winner_team_id": match.home_team_id if outcome == "home_win" else (match.away_team_id if outcome == "away_win" else None)
    }


def seed_players(num_users: int = 10):
    create_db_and_tables()

    with Session(engine) as session:
        # Get all group stage matches
        matches = session.exec(
            select(Match).where(Match.round == "group_stage")
        ).all()

        if not matches:
            print("Please seed matches first!")
            return

        # Get all teams for random assignment
        teams = session.exec(select(FifaTeam)).all()
        if not teams:
            print("Warning: No teams found, users will not have a favorite team.")

        users_created = 0
        predictions_created = 0

        for i, user_data in enumerate(TEST_USERS[:num_users]):
            # Check if user exists
            existing = session.exec(
                select(User).where(User.email == user_data["email"])
            ).first()

            if existing:
                print(f"User {user_data['email']} already exists, skipping...")
                continue

            # Create user
            user = User(
                email=user_data["email"],
                password_hash=hash_password("password123"),
                display_name=user_data["display_name"],
                cookie_consent=True,
                favorite_team_id=random.choice(teams).id if teams else None
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            users_created += 1

            # Create predictions for all group stage matches
            # Each user predicts a random subset (70-100% of matches)
            num_predictions = random.randint(int(len(matches) * 0.7), len(matches))
            selected_matches = random.sample(matches, num_predictions)

            for match in selected_matches:
                pred_data = generate_random_prediction(match)
                prediction = Prediction(
                    user_id=user.id,
                    match_id=match.id,
                    **pred_data
                )
                session.add(prediction)
                predictions_created += 1

            session.commit()
            print(f"Created user {user.display_name} with {len(selected_matches)} predictions")

        print(f"\nSeeded {users_created} users with {predictions_created} total predictions.")


def seed_admin():
    """Create the admin user."""
    create_db_and_tables()

    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.email == "admin@worldcup.com")
        ).first()

        if existing:
            print("Admin user already exists.")
            return

        admin = User(
            email="admin@worldcup.com",
            password_hash=hash_password("password"),
            display_name="Admin",
            is_admin=True,
            cookie_consent=True
        )
        session.add(admin)
        session.commit()
        print("Admin user created: admin@worldcup.com / password")


if __name__ == "__main__":
    seed_admin()

    if "--users" in sys.argv:
        try:
            idx = sys.argv.index("--users")
            num = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            num = 10
        seed_players(num)
    else:
        seed_players()
