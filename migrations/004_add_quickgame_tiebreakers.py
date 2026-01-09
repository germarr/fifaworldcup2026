#!/usr/bin/env python3
"""
Migration: Add quick game group tie-breakers
-------------------------------------------
- Adds quick_game_group_tiebreakers table

Usage: Run from project root directory
    python migrations/004_add_quickgame_tiebreakers.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, text
from app.database import engine


def run_migration():
    print("\n" + "=" * 60)
    print("ADD QUICK GAME GROUP TIE-BREAKERS")
    print("=" * 60)

    create_sql = """
    CREATE TABLE IF NOT EXISTS quick_game_group_tiebreakers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quick_game_id INTEGER NOT NULL,
        group_letter VARCHAR(1) NOT NULL,
        first_team_id INTEGER,
        second_team_id INTEGER,
        created_at DATETIME NOT NULL,
        FOREIGN KEY (quick_game_id) REFERENCES quick_games(id),
        FOREIGN KEY (first_team_id) REFERENCES teams(id),
        FOREIGN KEY (second_team_id) REFERENCES teams(id)
    )
    """

    with Session(engine) as db:
        db.exec(text(create_sql))
        db.exec(text("CREATE INDEX IF NOT EXISTS ix_qg_tiebreakers_game_group ON quick_game_group_tiebreakers (quick_game_id, group_letter)"))
        db.commit()

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
