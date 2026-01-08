#!/usr/bin/env python3
"""
Seed a New Player into the Database
------------------------------------
This script creates a new player user with:
- Automatic predictions for all tournament matches
- Assignment to one of 4 predefined player teams
- Random predictions following group stage -> knockout logic

Usage:
    python seed_player.py <username> <password> <favorite_team> [<team_name>]

Arguments:
    username       - Unique username for the player (3+ characters)
    password       - Player's password (6-72 characters)
    favorite_team  - Favorite World Cup team (e.g., "Brazil")
    team_name      - Optional. One of: "Phoenix", "Dragons", "Tigers", "Eagles"
                     If not provided, randomly assigned

Examples:
    python seed_player.py john password123 Brazil
    python seed_player.py alice mypass Dragons
    python seed_player.py bob secret123 Argentina Phoenix
"""

import sys
import os
import random
import secrets
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models import User, Match, Prediction, Team, PlayerTeam


# 4 predefined player teams
PLAYER_TEAMS = [
    {"name": "Phoenix", "description": "Rising from the ashes"},
    {"name": "Dragons", "description": "Fierce and powerful"},
    {"name": "Tigers", "description": "Swift and aggressive"},
    {"name": "Eagles", "description": "High flyers"},
]


def create_default_player_teams(db: Session) -> list[PlayerTeam]:
    """
    Create 4 default player teams if they don't exist.
    
    Args:
        db: Database session
        
    Returns:
        List of PlayerTeam objects
    """
    created_teams = []
    
    for team_data in PLAYER_TEAMS:
        # Check if team already exists
        existing = db.exec(
            select(PlayerTeam).where(PlayerTeam.name == team_data["name"])
        ).first()
        
        if existing:
            created_teams.append(existing)
            print(f"✓ Team '{team_data['name']}' already exists")
        else:
            # Generate unique join code
            join_code = secrets.token_hex(5).upper()
            
            new_team = PlayerTeam(
                name=team_data["name"],
                join_code=join_code
            )
            db.add(new_team)
            created_teams.append(new_team)
            print(f"✓ Created team: {team_data['name']} (Code: {join_code})")
    
    db.commit()
    return created_teams


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    from app.auth import hash_password as auth_hash
    return auth_hash(password)


def validate_inputs(username: str, password: str, favorite_team: str, team_name: str = None) -> tuple[bool, str]:
    """
    Validate user inputs.
    
    Args:
        username: Username to validate
        password: Password to validate
        favorite_team: Favorite team name
        team_name: Optional team to join
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(password) < 6 or len(password) > 72:
        return False, "Password must be 6-72 characters"
    
    if not favorite_team or len(favorite_team.strip()) == 0:
        return False, "Favorite team cannot be empty"
    
    if team_name:
        valid_teams = [t["name"] for t in PLAYER_TEAMS]
        if team_name not in valid_teams:
            return False, f"Team must be one of: {', '.join(valid_teams)}"
    
    return True, ""


def generate_prediction_score(is_group_stage: bool) -> tuple[int, int]:
    """
    Generate random prediction scores.
    
    Args:
        is_group_stage: True for group stage, False for knockout
        
    Returns:
        Tuple of (team1_score, team2_score)
    """
    if is_group_stage:
        return random.randint(0, 4), random.randint(0, 4)
    else:
        return random.randint(0, 3), random.randint(0, 3)


def get_resolved_teams_for_knockout(match: Match, user_id: int, db: Session) -> tuple[int, int]:
    """
    Resolve knockout match teams based on user's predictions.
    
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


def seed_player(username: str, password: str, favorite_team: str, team_name: str = None):
    """
    Create a new player with automatic predictions for all matches.
    
    Args:
        username: Username for the new player
        password: Password for the new player
        favorite_team: Favorite World Cup team
        team_name: Optional player team to join
    """
    from app.database import create_db_and_tables
    create_db_and_tables()

    # Validate inputs
    is_valid, error_msg = validate_inputs(username, password, favorite_team, team_name)
    if not is_valid:
        print(f"❌ Validation Error: {error_msg}")
        return False
    
    print(f"\n{'='*70}")
    print(f"🎮 SEEDING NEW PLAYER")
    print(f"{'='*70}\n")
    
    with Session(engine) as db:
        # Check if username already exists
        existing_user = db.exec(
            select(User).where(User.username == username)
        ).first()
        
        if existing_user:
            print(f"❌ Error: Username '{username}' already exists")
            return False
        
        # Create or get default player teams
        print(f"📋 Setting up player teams...")
        player_teams = create_default_player_teams(db)
        
        # Select team for player
        if team_name:
            selected_team = next((t for t in player_teams if t.name == team_name), None)
        else:
            selected_team = random.choice(player_teams)
        
        # Create the new user
        print(f"\n👤 Creating player account...")
        password_hash = hash_password(password)
        
        new_user = User(
            username=username,
            password_hash=password_hash,
            favorite_team=favorite_team,
            cookie_consent=True,
            avatar_seed=username.lower(),
            player_team_id=selected_team.id,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.flush()  # Get the user ID without committing
        
        print(f"✓ Created user: {username}")
        print(f"✓ Favorite team: {favorite_team}")
        print(f"✓ Joined team: {selected_team.name}")
        
        # Get all matches
        matches = db.exec(select(Match).order_by(Match.match_number)).all()
        
        if not matches:
            print(f"\n❌ Error: No matches found in database. Run seed_data.py first.")
            db.rollback()
            return False
        
        # Generate predictions for all matches
        print(f"\n🎯 Generating predictions for {len(matches)} matches...")
        
        predictions_created = 0
        predictions_skipped = 0
        
        for match in matches:
            is_group_stage = match.round.startswith("Group Stage")
            
            if is_group_stage:
                # Group stage: direct teams
                team1_score, team2_score = generate_prediction_score(True)
                penalty_winner_id = None
                team1_id = match.team1_id
                team2_id = match.team2_id
            else:
                # Knockout stage: resolve teams based on group predictions
                team1_id, team2_id = get_resolved_teams_for_knockout(match, new_user.id, db)
                
                if team1_id is None or team2_id is None:
                    predictions_skipped += 1
                    continue
                
                team1_score, team2_score = generate_prediction_score(False)
                
                # If tied in knockout, randomly select penalty winner
                if team1_score == team2_score:
                    penalty_winner_id = random.choice([team1_id, team2_id])
                else:
                    penalty_winner_id = None
            
            # Determine predicted winner
            if team1_score > team2_score:
                predicted_winner_id = team1_id
            elif team2_score > team1_score:
                predicted_winner_id = team2_id
            else:
                predicted_winner_id = None
            
            # Create prediction
            prediction = Prediction(
                user_id=new_user.id,
                match_id=match.id,
                predicted_team1_score=team1_score,
                predicted_team2_score=team2_score,
                predicted_winner_id=predicted_winner_id,
                penalty_shootout_winner_id=penalty_winner_id if not is_group_stage else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(prediction)
            predictions_created += 1
            
            # Commit after group stage to allow knockout resolutions
            if match.match_number == 48:
                db.commit()
        
        # Final commit
        db.commit()
        
        print(f"\n{'='*70}")
        print(f"✅ PLAYER SEEDING COMPLETE")
        print(f"{'='*70}")
        print(f"Username:      {username}")
        print(f"Favorite Team: {favorite_team}")
        print(f"Player Team:   {selected_team.name}")
        print(f"Predictions:   {predictions_created}/{len(matches)} matches")
        if predictions_skipped > 0:
            print(f"Skipped:       {predictions_skipped} (unresolved knockout matches)")
        print(f"\n✓ Player '{username}' is ready to compete!")
        
        return True


def main():
    """Main entry point."""
    if len(sys.argv) < 4:
        print("Usage: python seed_player.py <username> <password> <favorite_team> [<team_name>]")
        print("\nArguments:")
        print("  username      - Unique username (3+ characters)")
        print("  password      - Player's password (6-72 characters)")
        print("  favorite_team - Favorite World Cup team (e.g., 'Brazil')")
        print("  team_name     - Optional. One of: Phoenix, Dragons, Tigers, Eagles")
        print("\nExamples:")
        print("  python seed_player.py john password123 Brazil")
        print("  python seed_player.py alice mypass Dragons")
        print("  python seed_player.py bob secret123 Argentina Phoenix")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    favorite_team = sys.argv[3]
    team_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    try:
        success = seed_player(username, password, favorite_team, team_name)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
