#!/usr/bin/env python3
"""
Migration: Add Match Metadata Fields
-------------------------------------
- Adds stadium, time, and datetime_str fields to Match table

Usage: Run from project root directory
    python migrations/005_add_match_metadata.py
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
    print("ADD MATCH METADATA MIGRATION")
    print("="*60)

    print("\nStep 1: Adding new columns to matches table...")

    with Session(engine) as db:
        try:
            db.exec(text("ALTER TABLE matches ADD COLUMN stadium VARCHAR(100)"))
            print("  ✓ Added 'stadium' column to matches table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'stadium' already exists")
            else:
                raise

        try:
            db.exec(text("ALTER TABLE matches ADD COLUMN time VARCHAR(10)"))
            print("  ✓ Added 'time' column to matches table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'time' already exists")
            else:
                raise

        try:
            db.exec(text("ALTER TABLE matches ADD COLUMN datetime_str VARCHAR(50)"))
            print("  ✓ Added 'datetime_str' column to matches table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  • Column 'datetime_str' already exists")
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
