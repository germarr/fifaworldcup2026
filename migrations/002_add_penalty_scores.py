#!/usr/bin/env python3
"""
Migration: Add Penalty Scores
-----------------------------
- Adds actual_team1_penalty_score, actual_team2_penalty_score, penalty_winner_id to Match

Usage: Run from project root directory
    python migrations/002_add_penalty_scores.py
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, text
from app.database import engine

def run_migration():
    """Execute migration steps."""

    print("\n" + "="*60)
    print("ADD PENALTY SCORES MIGRATION")
    print("="*60)

    print("\nStep 1: Adding new columns to matches table...")

    with Session(engine) as db:
        try:
            db.exec(text("ALTER TABLE matches ADD COLUMN actual_team1_penalty_score INTEGER"))
            print("  ✓ Added 'actual_team1_penalty_score' column to matches table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'actual_team1_penalty_score' already exists")
            else:
                raise

        try:
            db.exec(text("ALTER TABLE matches ADD COLUMN actual_team2_penalty_score INTEGER"))
            print("  ✓ Added 'actual_team2_penalty_score' column to matches table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'actual_team2_penalty_score' already exists")
            else:
                raise

        try:
            db.exec(text("ALTER TABLE matches ADD COLUMN penalty_winner_id INTEGER REFERENCES teams(id)"))
            print("  ✓ Added 'penalty_winner_id' column to matches table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'penalty_winner_id' already exists")
            else:
                raise

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
