"""
Migration script to make user_id nullable in quick_games table
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('worldcup.db')
    cursor = conn.cursor()

    print("Starting migration...")

    # Check current data
    cursor.execute("SELECT COUNT(*) FROM quick_games")
    count = cursor.fetchone()[0]
    print(f"Found {count} existing quick games")

    # Create new table with user_id as nullable
    cursor.execute("""
        CREATE TABLE quick_games_new (
            id INTEGER NOT NULL PRIMARY KEY,
            user_id INTEGER,
            game_code VARCHAR(20) NOT NULL,
            is_completed BOOLEAN NOT NULL,
            champion_team_id INTEGER,
            created_at DATETIME NOT NULL,
            completed_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id),
            FOREIGN KEY(champion_team_id) REFERENCES teams (id),
            UNIQUE (game_code)
        )
    """)
    print("Created new table with nullable user_id")

    # Copy data from old table to new table
    cursor.execute("""
        INSERT INTO quick_games_new
        SELECT * FROM quick_games
    """)
    print("Copied data to new table")

    # Drop old table
    cursor.execute("DROP TABLE quick_games")
    print("Dropped old table")

    # Rename new table
    cursor.execute("ALTER TABLE quick_games_new RENAME TO quick_games")
    print("Renamed new table")

    # Recreate indexes
    cursor.execute("CREATE INDEX ix_quick_games_user_id ON quick_games (user_id)")
    cursor.execute("CREATE INDEX ix_quick_games_game_code ON quick_games (game_code)")
    print("Recreated indexes")

    # Also need to handle quick_game_matches table foreign key
    # Check if it exists and has data
    cursor.execute("SELECT COUNT(*) FROM quick_game_matches")
    matches_count = cursor.fetchone()[0]
    print(f"Found {matches_count} quick game matches")

    if matches_count > 0:
        # Recreate quick_game_matches with proper foreign key
        cursor.execute("""
            CREATE TABLE quick_game_matches_new (
                id INTEGER NOT NULL PRIMARY KEY,
                quick_game_id INTEGER NOT NULL,
                match_id INTEGER NOT NULL,
                result VARCHAR(10) NOT NULL,
                advancing_team_id INTEGER,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(quick_game_id) REFERENCES quick_games (id),
                FOREIGN KEY(match_id) REFERENCES matches (id),
                FOREIGN KEY(advancing_team_id) REFERENCES teams (id)
            )
        """)

        cursor.execute("""
            INSERT INTO quick_game_matches_new
            SELECT * FROM quick_game_matches
        """)

        cursor.execute("DROP TABLE quick_game_matches")
        cursor.execute("ALTER TABLE quick_game_matches_new RENAME TO quick_game_matches")

        # Recreate indexes
        cursor.execute("CREATE INDEX ix_quick_game_matches_quick_game_id ON quick_game_matches (quick_game_id)")
        print("Recreated quick_game_matches table")

    conn.commit()
    conn.close()

    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
