"""
Database seeder for FIFA World Cup teams and matches.
Run this script to populate the database with sample data.
"""

import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models import Team, Match, GroupStanding

GROUP_MATCHES = [
    # Group A
    ("QAT", "ECU", "A"),
    ("SEN", "NED", "A"),
    ("QAT", "SEN", "A"),
    ("NED", "ECU", "A"),
    ("NED", "QAT", "A"),
    ("ECU", "SEN", "A"),

    # Group B
    ("ENG", "IRN", "B"),
    ("USA", "WAL", "B"),
    ("WAL", "IRN", "B"),
    ("ENG", "USA", "B"),
    ("WAL", "ENG", "B"),
    ("IRN", "USA", "B"),

    # Group C
    ("ARG", "KSA", "C"),
    ("MEX", "POL", "C"),
    ("POL", "KSA", "C"),
    ("ARG", "MEX", "C"),
    ("POL", "ARG", "C"),
    ("KSA", "MEX", "C"),

    # Group D
    ("FRA", "AUS", "D"),
    ("DEN", "TUN", "D"),
    ("TUN", "AUS", "D"),
    ("FRA", "DEN", "D"),
    ("TUN", "FRA", "D"),
    ("AUS", "DEN", "D"),

    # Group E
    ("ESP", "CRC", "E"),
    ("GER", "JPN", "E"),
    ("JPN", "CRC", "E"),
    ("ESP", "GER", "E"),
    ("JPN", "ESP", "E"),
    ("CRC", "GER", "E"),

    # Group F
    ("BEL", "CAN", "F"),
    ("MAR", "CRO", "F"),
    ("CRO", "CAN", "F"),
    ("BEL", "MAR", "F"),
    ("CRO", "BEL", "F"),
    ("CAN", "MAR", "F"),

    # Group G
    ("BRA", "SRB", "G"),
    ("SUI", "CMR", "G"),
    ("CMR", "SRB", "G"),
    ("BRA", "SUI", "G"),
    ("CMR", "BRA", "G"),
    ("SRB", "SUI", "G"),

    # Group H
    ("POR", "GHA", "H"),
    ("URU", "KOR", "H"),
    ("KOR", "GHA", "H"),
    ("POR", "URU", "H"),
    ("KOR", "POR", "H"),
    ("GHA", "URU", "H"),
]


def seed_teams():
    """Seed teams for the World Cup."""
    teams_data = [
        # Group A
        {"name": "Qatar", "code": "QAT", "group": "A"},
        {"name": "Ecuador", "code": "ECU", "group": "A"},
        {"name": "Senegal", "code": "SEN", "group": "A"},
        {"name": "Netherlands", "code": "NED", "group": "A"},

        # Group B
        {"name": "England", "code": "ENG", "group": "B"},
        {"name": "Iran", "code": "IRN", "group": "B"},
        {"name": "USA", "code": "USA", "group": "B"},
        {"name": "Wales", "code": "WAL", "group": "B"},

        # Group C
        {"name": "Argentina", "code": "ARG", "group": "C"},
        {"name": "Saudi Arabia", "code": "KSA", "group": "C"},
        {"name": "Mexico", "code": "MEX", "group": "C"},
        {"name": "Poland", "code": "POL", "group": "C"},

        # Group D
        {"name": "France", "code": "FRA", "group": "D"},
        {"name": "Australia", "code": "AUS", "group": "D"},
        {"name": "Denmark", "code": "DEN", "group": "D"},
        {"name": "Tunisia", "code": "TUN", "group": "D"},

        # Group E
        {"name": "Spain", "code": "ESP", "group": "E"},
        {"name": "Costa Rica", "code": "CRC", "group": "E"},
        {"name": "Germany", "code": "GER", "group": "E"},
        {"name": "Japan", "code": "JPN", "group": "E"},

        # Group F
        {"name": "Belgium", "code": "BEL", "group": "F"},
        {"name": "Canada", "code": "CAN", "group": "F"},
        {"name": "Morocco", "code": "MAR", "group": "F"},
        {"name": "Croatia", "code": "CRO", "group": "F"},

        # Group G
        {"name": "Brazil", "code": "BRA", "group": "G"},
        {"name": "Serbia", "code": "SRB", "group": "G"},
        {"name": "Switzerland", "code": "SUI", "group": "G"},
        {"name": "Cameroon", "code": "CMR", "group": "G"},

        # Group H
        {"name": "Portugal", "code": "POR", "group": "H"},
        {"name": "Ghana", "code": "GHA", "group": "H"},
        {"name": "Uruguay", "code": "URU", "group": "H"},
        {"name": "South Korea", "code": "KOR", "group": "H"},
    ]

    with Session(engine) as session:
        # Check if teams already exist
        existing_teams = session.exec(select(Team)).first()
        if existing_teams:
            print("Teams already seeded. Skipping...")
            return

        for team_data in teams_data:
            team = Team(**team_data)
            session.add(team)

        session.commit()
        print(f"Successfully seeded {len(teams_data)} teams!")


def seed_matches():
    """Seed matches for the World Cup."""
    with Session(engine) as session:
        # Check if matches already exist
        existing_matches = session.exec(select(Match)).first()
        if existing_matches:
            print("Matches already seeded. Skipping...")
            return

        # Get all teams
        teams = {team.code: team for team in session.exec(select(Team)).all()}

        if not teams:
            print("Error: No teams found. Please seed teams first.")
            return

        # Base date for matches (starting from today)
        base_date = datetime.now()
        match_number = 1

        # Group Stage Matches
        for team1_code, team2_code, group in GROUP_MATCHES:
            match = Match(
                round=f"Group Stage - Group {group}",
                match_number=match_number,
                team1_id=teams[team1_code].id,
                team2_id=teams[team2_code].id,
                match_date=base_date + timedelta(days=(match_number - 1) // 4),
                is_finished=False
            )
            session.add(match)
            match_number += 1

        # Round of 16 - FIFA World Cup bracket structure
        # Match numbers 49-56 (Round of 16)
        # Format: (team1_placeholder, team2_placeholder, match_date_offset)
        round_of_16_matches = [
            ("1A", "2B", 15),  # Match 49
            ("1C", "2D", 15),  # Match 50
            ("1E", "2F", 16),  # Match 51
            ("1G", "2H", 16),  # Match 52
            ("1B", "2A", 17),  # Match 53
            ("1D", "2C", 17),  # Match 54
            ("1F", "2E", 18),  # Match 55
            ("1H", "2G", 18),  # Match 56
        ]

        for team1_ph, team2_ph, day_offset in round_of_16_matches:
            match = Match(
                round="Round of 16",
                match_number=match_number,
                team1_id=None,
                team2_id=None,
                team1_placeholder=team1_ph,
                team2_placeholder=team2_ph,
                match_date=base_date + timedelta(days=day_offset),
                is_finished=False
            )
            session.add(match)
            match_number += 1

        # Quarter Finals - Winners of Round of 16 (Match 57-60)
        quarter_finals_matches = [
            ("W49", "W50", 20),  # Match 57: Winner of 49 vs Winner of 50
            ("W51", "W52", 20),  # Match 58: Winner of 51 vs Winner of 52
            ("W53", "W54", 21),  # Match 59: Winner of 53 vs Winner of 54
            ("W55", "W56", 21),  # Match 60: Winner of 55 vs Winner of 56
        ]

        for team1_ph, team2_ph, day_offset in quarter_finals_matches:
            match = Match(
                round="Quarter Finals",
                match_number=match_number,
                team1_id=None,
                team2_id=None,
                team1_placeholder=team1_ph,
                team2_placeholder=team2_ph,
                match_date=base_date + timedelta(days=day_offset),
                is_finished=False
            )
            session.add(match)
            match_number += 1

        # Semi Finals - Winners of Quarter Finals (Match 61-62)
        semi_finals_matches = [
            ("W57", "W58", 24),  # Match 61: Winner of 57 vs Winner of 58
            ("W59", "W60", 24),  # Match 62: Winner of 59 vs Winner of 60
        ]

        for team1_ph, team2_ph, day_offset in semi_finals_matches:
            match = Match(
                round="Semi Finals",
                match_number=match_number,
                team1_id=None,
                team2_id=None,
                team1_placeholder=team1_ph,
                team2_placeholder=team2_ph,
                match_date=base_date + timedelta(days=day_offset),
                is_finished=False
            )
            session.add(match)
            match_number += 1

        # Third Place Match (Match 63)
        match = Match(
            round="Third Place",
            match_number=match_number,
            team1_id=None,
            team2_id=None,
            team1_placeholder="L61",  # Loser of semi 1
            team2_placeholder="L62",  # Loser of semi 2
            match_date=base_date + timedelta(days=27),
            is_finished=False
        )
        session.add(match)
        match_number += 1

        # Final (Match 64)
        match = Match(
            round="Final",
            match_number=match_number,
            team1_id=None,
            team2_id=None,
            team1_placeholder="W61",  # Winner of semi 1
            team2_placeholder="W62",  # Winner of semi 2
            match_date=base_date + timedelta(days=28),
            is_finished=False
        )
        session.add(match)
        match_number += 1

        session.commit()
        print(f"Successfully seeded {match_number - 1} matches!")


def seed_group_standings():
    """Seed random group standings (max 4 goals per team per match)."""
    with Session(engine) as session:
        existing_standings = session.exec(select(GroupStanding)).first()
        if existing_standings:
            print("Group standings already seeded. Skipping...")
            return

        teams = {team.code: team for team in session.exec(select(Team)).all()}

        if not teams:
            print("Error: No teams found. Please seed teams first.")
            return

        standings = {}
        for team in teams.values():
            if team.group:
                standings[team.code] = {
                    "team": team,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0,
                }

        for team1_code, team2_code, _group in GROUP_MATCHES:
            team1_score = random.randint(0, 4)
            team2_score = random.randint(0, 4)

            team1 = standings[team1_code]
            team2 = standings[team2_code]

            team1["played"] += 1
            team2["played"] += 1

            team1["goals_for"] += team1_score
            team1["goals_against"] += team2_score
            team2["goals_for"] += team2_score
            team2["goals_against"] += team1_score

            if team1_score > team2_score:
                team1["won"] += 1
                team1["points"] += 3
                team2["lost"] += 1
            elif team2_score > team1_score:
                team2["won"] += 1
                team2["points"] += 3
                team1["lost"] += 1
            else:
                team1["drawn"] += 1
                team2["drawn"] += 1
                team1["points"] += 1
                team2["points"] += 1

        for stats in standings.values():
            team = stats["team"]
            session.add(GroupStanding(
                group_letter=team.group,
                team_id=team.id,
                played=stats["played"],
                won=stats["won"],
                drawn=stats["drawn"],
                lost=stats["lost"],
                goals_for=stats["goals_for"],
                goals_against=stats["goals_against"],
                goal_difference=stats["goals_for"] - stats["goals_against"],
                points=stats["points"],
            ))

        session.commit()
        print("Successfully seeded group standings!")


def main():
    """Main function to seed the database."""
    print("Creating database tables...")
    create_db_and_tables()

    print("\nSeeding teams...")
    seed_teams()

    print("\nSeeding matches...")
    seed_matches()

    print("\nSeeding group standings...")
    seed_group_standings()

    print("\nDatabase seeding complete!")


if __name__ == "__main__":
    main()
