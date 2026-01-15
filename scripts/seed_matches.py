"""Seed matches for World Cup 2026."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.match import Match
from app.models.fifa_team import FifaTeam
from app.models.stadium import Stadium


def seed_matches():
    create_db_and_tables()

    with Session(engine) as session:
        existing = session.query(Match).first()
        if existing:
            print("Matches already seeded. Use --force to re-seed.")
            return

        # Get teams by group
        teams = session.exec(select(FifaTeam)).all()
        teams_by_group = {}
        for team in teams:
            if team.group_letter:
                if team.group_letter not in teams_by_group:
                    teams_by_group[team.group_letter] = []
                teams_by_group[team.group_letter].append(team)

        # Get stadiums
        stadiums = session.exec(select(Stadium)).all()
        if not stadiums:
            print("Please seed stadiums first!")
            return

        match_number = 1
        base_date = datetime(2026, 6, 11, 18, 0)  # Tournament starts June 11, 2026

        # Group stage matches (72 matches)
        # Each group has 6 matches (round-robin: 4 teams = 6 matches)
        for group_letter in sorted(teams_by_group.keys()):
            group_teams = teams_by_group[group_letter]
            if len(group_teams) < 4:
                continue

            # Generate round-robin matchups
            matchups = [
                (0, 1), (2, 3),  # Matchday 1
                (0, 2), (1, 3),  # Matchday 2
                (0, 3), (1, 2),  # Matchday 3
            ]

            for i, (home_idx, away_idx) in enumerate(matchups):
                match = Match(
                    match_number=match_number,
                    round="group_stage",
                    group_letter=group_letter,
                    home_team_id=group_teams[home_idx].id,
                    away_team_id=group_teams[away_idx].id,
                    stadium_id=random.choice(stadiums).id,
                    scheduled_datetime=base_date + timedelta(days=match_number // 8, hours=(match_number % 8) * 3)
                )
                session.add(match)
                match_number += 1

        # Round of 32 (16 matches)
        r32_slots = [
            ("1A", "2B"), ("1C", "2D"), ("1E", "2F"), ("1G", "2H"),
            ("1I", "2J"), ("1K", "2L"), ("1B", "2A"), ("1D", "2C"),
            ("1F", "2E"), ("1H", "2G"), ("1J", "2I"), ("1L", "2K"),
            ("1A", "3rd_1"), ("1B", "3rd_2"), ("1C", "3rd_3"), ("1D", "3rd_4"),
        ]
        r32_date = base_date + timedelta(days=15)

        for i, (home_slot, away_slot) in enumerate(r32_slots):
            match = Match(
                match_number=match_number,
                round="round_of_32",
                home_slot=home_slot,
                away_slot=away_slot,
                stadium_id=random.choice(stadiums).id,
                scheduled_datetime=r32_date + timedelta(days=i // 4, hours=(i % 4) * 3)
            )
            session.add(match)
            match_number += 1

        # Round of 16 (8 matches)
        r16_date = r32_date + timedelta(days=4)
        for i in range(8):
            match = Match(
                match_number=match_number,
                round="round_of_16",
                home_slot=f"W{73 + i*2}",  # Winner of R32 match
                away_slot=f"W{74 + i*2}",
                stadium_id=random.choice(stadiums).id,
                scheduled_datetime=r16_date + timedelta(days=i // 4, hours=(i % 4) * 3)
            )
            session.add(match)
            match_number += 1

        # Quarter Finals (4 matches)
        qf_date = r16_date + timedelta(days=4)
        for i in range(4):
            match = Match(
                match_number=match_number,
                round="quarter_final",
                home_slot=f"W{89 + i*2}",
                away_slot=f"W{90 + i*2}",
                stadium_id=random.choice(stadiums).id,
                scheduled_datetime=qf_date + timedelta(days=i // 2, hours=(i % 2) * 4)
            )
            session.add(match)
            match_number += 1

        # Semi Finals (2 matches)
        sf_date = qf_date + timedelta(days=4)
        for i in range(2):
            match = Match(
                match_number=match_number,
                round="semi_final",
                home_slot=f"W{97 + i*2}",
                away_slot=f"W{98 + i*2}",
                stadium_id=random.choice(stadiums).id,
                scheduled_datetime=sf_date + timedelta(days=i, hours=20)
            )
            session.add(match)
            match_number += 1

        # Third Place Match
        third_date = sf_date + timedelta(days=3)
        match = Match(
            match_number=match_number,
            round="third_place",
            home_slot="L101",  # Loser of SF 1
            away_slot="L102",  # Loser of SF 2
            stadium_id=random.choice(stadiums).id,
            scheduled_datetime=third_date
        )
        session.add(match)
        match_number += 1

        # Final
        final_date = third_date + timedelta(days=1)
        match = Match(
            match_number=match_number,
            round="final",
            home_slot="W101",  # Winner of SF 1
            away_slot="W102",  # Winner of SF 2
            stadium_id=stadiums[0].id,  # MetLife Stadium for final
            scheduled_datetime=final_date
        )
        session.add(match)

        session.commit()
        print(f"Seeded {match_number} matches.")


if __name__ == "__main__":
    if "--force" in sys.argv:
        with Session(engine) as session:
            session.query(Match).delete()
            session.commit()
    seed_matches()
