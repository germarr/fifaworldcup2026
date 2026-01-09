# Migrations

This folder contains database migration scripts that manage schema changes and data transformations.

## Files

- **001_settings_redesign.py** - Settings schema redesign migration. Updates database structure for improved settings management.

- **002_add_penalty_scores.py** - Adds penalty score tracking to the database schema.

- **003_fix_users_schema.py** - Fixes and corrects the users table schema.

- **004_add_quickgame_tiebreakers.py** - Adds tiebreaker logic and fields to the quick_games table.

- **migrate_quickgames.py** - Migration script to make user_id nullable in the quick_games table, allowing anonymous quick game submissions.

## Usage

Migrations are typically applied in order by the migration system. To run a specific migration:

```bash
python migrations/migrate_quickgames.py
```

Each migration script connects to the SQLite database and performs necessary schema and data transformations.
