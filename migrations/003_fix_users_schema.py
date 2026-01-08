#!/usr/bin/env python3
"""
Migration: Fix Users Schema
---------------------------
- Makes favorite_team nullable to fix IntegrityError
- Recreates table to apply schema change (SQLite limitation)
- Ensures indices exist

Usage: Run from project root directory
    python migrations/003_fix_users_schema.py
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, text
from app.database import engine

def run_migration():
    print("\n" + "="*60)
    print("FIX USERS SCHEMA MIGRATION")
    print("="*60)

    with Session(engine) as db:
        # Check if users_old already exists (failed previous run?)
        try:
            db.exec(text("SELECT 1 FROM users_old LIMIT 1"))
            print("⚠ 'users_old' table exists. Previous migration might have failed.")
            print("  Restoring from users_old before proceeding...")
            db.exec(text("DROP TABLE IF EXISTS users"))
            db.exec(text("ALTER TABLE users_old RENAME TO users"))
            print("  Restored 'users' table.")
        except Exception:
            # Table doesn't exist, which is good
            pass

        print("Step 1: Renaming old table...")
        db.exec(text("ALTER TABLE users RENAME TO users_old"))
        
        print("Step 2: Creating new table...")
        create_sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            favorite_team VARCHAR(100),
            cookie_consent BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            avatar_seed VARCHAR(50) DEFAULT 'adventurer',
            total_points INTEGER DEFAULT 0,
            player_team_id INTEGER,
            email VARCHAR(255),
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            favorite_team_id INTEGER,
            FOREIGN KEY (player_team_id) REFERENCES player_teams(id),
            FOREIGN KEY (favorite_team_id) REFERENCES teams(id)
        )
        """
        db.exec(text(create_sql))
        
        print("Step 3: Copying data...")
        cols = "id, username, password_hash, favorite_team, cookie_consent, created_at, avatar_seed, total_points, player_team_id, email, first_name, last_name, favorite_team_id"
        db.exec(text(f"INSERT INTO users ({cols}) SELECT {cols} FROM users_old"))
        
        print("Step 4: Dropping old table...")
        db.exec(text("DROP TABLE users_old"))
        
        print("Step 5: Recreating indices...")
        db.exec(text("CREATE UNIQUE INDEX ix_users_username ON users (username)"))
        db.exec(text("CREATE UNIQUE INDEX ix_users_email ON users (email)"))
        
        db.commit()

    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
