#!/usr/bin/env python3
"""
Migration: Settings Redesign
-----------------------------
- Adds email, first_name, last_name, favorite_team_id to User
- Creates UserTeamMembership junction table
- Migrates data from old structure to new

Usage: Run from project root directory
    python migrations/001_settings_redesign.py
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, select, SQLModel, text
from sqlalchemy import func
from app.database import engine
from app.models import User, Team, PlayerTeam, UserTeamMembership


def run_migration():
    """Execute migration steps."""

    print("\n" + "="*60)
    print("SETTINGS REDESIGN MIGRATION")
    print("="*60)

    print("\nStep 1: Creating new tables and columns...")

    with Session(engine) as db:
        # First, create the UserTeamMembership table if it doesn't exist
        SQLModel.metadata.create_all(engine)

        # Add new columns to users table using raw SQL
        # SQLite doesn't support multiple ALTER TABLE in one statement
        try:
            db.exec(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
            print("  ✓ Added 'email' column to users table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'email' already exists")
            else:
                raise

        try:
            db.exec(text("ALTER TABLE users ADD COLUMN first_name VARCHAR(100)"))
            print("  ✓ Added 'first_name' column to users table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'first_name' already exists")
            else:
                raise

        try:
            db.exec(text("ALTER TABLE users ADD COLUMN last_name VARCHAR(100)"))
            print("  ✓ Added 'last_name' column to users table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'last_name' already exists")
            else:
                raise

        try:
            db.exec(text("ALTER TABLE users ADD COLUMN favorite_team_id INTEGER REFERENCES teams(id)"))
            print("  ✓ Added 'favorite_team_id' column to users table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'favorite_team_id' already exists")
            else:
                raise

        db.commit()

    print("✓ Tables created/updated")

    with Session(engine) as db:
        print("\nStep 2: Migrating user data...")
        users = db.exec(select(User)).all()

        migrated_count = 0
        for user in users:
            needs_update = False

            # Migrate email (generate temp if missing)
            if not user.email:
                # Generate email from username, remove spaces, lowercase
                clean_username = user.username.lower().replace(' ', '').replace('.', '')
                user.email = f"{clean_username}@temp.example.com"
                print(f"  ✓ Generated temp email for '{user.username}': {user.email}")
                needs_update = True

            # Migrate favorite_team text to Team FK
            if user.favorite_team and not user.favorite_team_id:
                # Try to find matching team (case-insensitive partial match)
                team = db.exec(select(Team).where(
                    func.lower(Team.name).like(f"%{user.favorite_team.lower()}%")
                )).first()

                if team:
                    user.favorite_team_id = team.id
                    print(f"  ✓ Matched '{user.favorite_team}' → {team.name} for '{user.username}'")
                    needs_update = True
                else:
                    print(f"  ⚠ Could not match '{user.favorite_team}' to Team table for '{user.username}'")

            # Migrate single team (player_team_id) to many-to-many
            if user.player_team_id:
                # Check if membership already exists
                existing = db.exec(select(UserTeamMembership).where(
                    UserTeamMembership.user_id == user.id,
                    UserTeamMembership.player_team_id == user.player_team_id
                )).first()

                if not existing:
                    membership = UserTeamMembership(
                        user_id=user.id,
                        player_team_id=user.player_team_id
                    )
                    db.add(membership)
                    print(f"  ✓ Created team membership for '{user.username}'")
                    needs_update = True

            if needs_update:
                db.add(user)
                migrated_count += 1

        db.commit()
        print(f"\n✓ Migrated {migrated_count} users")

        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        print("\nWhat was done:")
        print("  ✓ Created UserTeamMembership table")
        print("  ✓ Added email, first_name, last_name, favorite_team_id to User table")
        print("  ✓ Generated temporary emails for existing users")
        print("  ✓ Migrated favorite_team text to FK references")
        print("  ✓ Migrated single team memberships to junction table")
        print("\nNext steps:")
        print("  1. Users with @temp.example.com emails should update their email in settings")
        print("  2. Deploy updated code (routes, templates, CSS)")
        print("  3. Test registration and settings pages")
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
