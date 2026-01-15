"""
Database seeder for FIFA World Cup 2026 teams and matches.
FULLY DYNAMIC - adapts to CSV content automatically.
Run this script to populate the database with tournament data.
"""

import sys
import os
import csv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models import Team, Match, GroupStanding
from app.tournament_config import (
    get_all_groups,
    generate_knockout_bracket_structure,
    get_knockout_placeholders
)


def extract_groups_from_csv(csv_file='mockups/group_stage_matches.csv') -> set:
    """Extract unique group letters from CSV file."""
    groups = set()
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            group = row['group'].strip()
            if group:
                groups.add(group)
    return sorted(groups)


def seed_teams_from_csv(csv_file='mockups/group_stage_matches.csv'):
    """Seed teams from the CSV file - completely dynamic."""
    with Session(engine) as session:
        # Check if teams already exist
        existing_teams = session.exec(select(Team)).first()
        if existing_teams:
            print("Teams already seeded. Skipping...")
            return

        teams_map = {}  # Track unique teams by name (to avoid duplicates)

        # Read CSV and extract unique teams
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Process team1
                team1_code = row['team1_code'].strip()
                team1_name = row['team1_name'].strip()
                group = row['group'].strip()

                if team1_code != 'TBD' and team1_name not in teams_map:
                    teams_map[team1_name] = {
                        'name': team1_name,
                        'code': team1_code,
                        'group': group
                    }

                # Process team2
                team2_code = row['team2_code'].strip()
                team2_name = row['team2_name'].strip()

                if team2_code != 'TBD' and team2_name not in teams_map:
                    teams_map[team2_name] = {
                        'name': team2_name,
                        'code': team2_code,
                        'group': group
                    }

        # Sort teams by group and name for consistent ordering
        teams_list = sorted(teams_map.values(), key=lambda x: (x['group'], x['name']))

        # Add teams to database
        for team_data in teams_list:
            team = Team(**team_data)
            session.add(team)

        session.commit()

        # Get group summary
        groups = sorted(set(t['group'] for t in teams_list))
        print(f"Successfully seeded {len(teams_list)} teams across {len(groups)} groups!")
        print(f"Groups: {', '.join(groups)}")


def seed_matches_from_csv(csv_file='mockups/group_stage_matches.csv'):
    """Seed group stage and knockout matches - completely dynamic."""
    with Session(engine) as session:
        # Check if matches already exist
        existing_matches = session.exec(select(Match)).first()
        if existing_matches:
            print("Matches already seeded. Skipping...")
            return

        # Get all teams
        teams_list = session.exec(select(Team)).all()
        teams = {team.code: team for team in teams_list}
        teams_by_name = {team.name: team for team in teams_list}

        if not teams:
            print("Error: No teams found. Please seed teams first.")
            return

        # Read CSV and create group stage matches
        group_matches_added = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_number = int(row['match_number'])
                team1_code = row['team1_code'].strip()
                team2_code = row['team2_code'].strip()
                team1_name = row['team1_name'].strip()
                team2_name = row['team2_name'].strip()

                # Parse date
                date_str = row['date'].strip()
                match_date = datetime.strptime(date_str, '%m/%d/%Y')

                # Get team IDs or placeholders
                # Try to find team by code first, then by name (for code variations)
                if team1_code != 'TBD':
                    team1_id = teams.get(team1_code)
                    if team1_id:
                        team1_id = team1_id.id
                    else:
                        # Try by name
                        team1_obj = teams_by_name.get(team1_name)
                        team1_id = team1_obj.id if team1_obj else None
                    team1_placeholder = None
                else:
                    team1_id = None
                    team1_placeholder = team1_name

                if team2_code != 'TBD':
                    team2_id = teams.get(team2_code)
                    if team2_id:
                        team2_id = team2_id.id
                    else:
                        # Try by name
                        team2_obj = teams_by_name.get(team2_name)
                        team2_id = team2_obj.id if team2_obj else None
                    team2_placeholder = None
                else:
                    team2_id = None
                    team2_placeholder = team2_name

                match = Match(
                    round=row['round'].strip(),
                    match_number=match_number,
                    team1_id=team1_id,
                    team2_id=team2_id,
                    team1_placeholder=team1_placeholder,
                    team2_placeholder=team2_placeholder,
                    match_date=match_date,
                    stadium=row.get('stadium', '').strip() or None,
                    time=row.get('time', '').strip() or None,
                    datetime_str=row.get('datetime', '').strip() or None,
                    is_finished=False
                )
                session.add(match)
                group_matches_added += 1

        # DYNAMIC KNOCKOUT BRACKET GENERATION
        # Get number of groups from database
        groups = get_all_groups(session)
        num_groups = len(groups)
        qualifying_teams = num_groups * 2  # Top 2 from each group

        print(f"\nGenerating knockout bracket for {num_groups} groups ({qualifying_teams} qualifying teams)...")

        # Generate knockout structure
        knockout_structure = generate_knockout_bracket_structure(qualifying_teams)

        match_number = group_matches_added + 1  # Start after group stage
        total_knockout_matches = 0

        # Get the last group stage match date to calculate knockout dates
        last_group_match = session.exec(
            select(Match).where(Match.round.like('Group Stage%')).order_by(Match.match_date.desc())
        ).first()
        base_knockout_date = last_group_match.match_date if last_group_match else datetime(2026, 6, 29)

        # First knockout round uses group placeholders
        first_round_name = knockout_structure[0][0]
        first_round_matches = knockout_structure[0][1]
        placeholders = get_knockout_placeholders(num_groups)

        print(f"\n{first_round_name}:")
        for i, (team1_ph, team2_ph) in enumerate(placeholders[:first_round_matches]):
            match = Match(
                round=first_round_name,
                match_number=match_number,
                team1_id=None,
                team2_id=None,
                team1_placeholder=team1_ph,
                team2_placeholder=team2_ph,
                match_date=base_knockout_date + timedelta(days=2),
                is_finished=False
            )
            session.add(match)
            print(f"  Match {match_number}: {team1_ph} vs {team2_ph}")
            match_number += 1
            total_knockout_matches += 1

        # Subsequent rounds use winner placeholders
        days_offset = 2
        for round_idx in range(1, len(knockout_structure)):
            round_name, num_matches, _, _ = knockout_structure[round_idx]
            days_offset += 3  # 3 days between rounds

            print(f"\n{round_name}:")

            if round_name == "Third Place":
                # Third place uses loser placeholders from semis
                prev_round_start = match_number - 2  # Last 2 matches were semis
                match = Match(
                    round=round_name,
                    match_number=match_number,
                    team1_id=None,
                    team2_id=None,
                    team1_placeholder=f"L{prev_round_start - 1}",
                    team2_placeholder=f"L{prev_round_start}",
                    match_date=base_knockout_date + timedelta(days=days_offset),
                    is_finished=False
                )
                session.add(match)
                print(f"  Match {match_number}: L{prev_round_start - 1} vs L{prev_round_start}")
                match_number += 1
                total_knockout_matches += 1

            elif round_name == "Final":
                # Final uses winner placeholders from semis
                prev_round_start = match_number - 3  # -3 because third place was just added
                match = Match(
                    round=round_name,
                    match_number=match_number,
                    team1_id=None,
                    team2_id=None,
                    team1_placeholder=f"W{prev_round_start - 1}",
                    team2_placeholder=f"W{prev_round_start}",
                    match_date=base_knockout_date + timedelta(days=days_offset + 1),
                    is_finished=False
                )
                session.add(match)
                print(f"  Match {match_number}: W{prev_round_start - 1} vs W{prev_round_start}")
                match_number += 1
                total_knockout_matches += 1

            else:
                # Regular knockout rounds
                prev_round_matches = knockout_structure[round_idx - 1][1]
                prev_round_start = match_number - prev_round_matches

                for i in range(num_matches):
                    w1 = prev_round_start + (i * 2)
                    w2 = prev_round_start + (i * 2) + 1
                    match = Match(
                        round=round_name,
                        match_number=match_number,
                        team1_id=None,
                        team2_id=None,
                        team1_placeholder=f"W{w1}",
                        team2_placeholder=f"W{w2}",
                        match_date=base_knockout_date + timedelta(days=days_offset),
                        is_finished=False
                    )
                    session.add(match)
                    print(f"  Match {match_number}: W{w1} vs W{w2}")
                    match_number += 1
                    total_knockout_matches += 1

        session.commit()
        print(f"\nSuccessfully seeded {group_matches_added} group stage matches!")
        print(f"Successfully seeded {total_knockout_matches} knockout matches!")
        print(f"Total matches: {match_number - 1}")


def seed_group_standings():
    """Initialize empty group standings for all teams."""
    with Session(engine) as session:
        existing_standings = session.exec(select(GroupStanding)).first()
        if existing_standings:
            print("Group standings already seeded. Skipping...")
            return

        teams = session.exec(select(Team)).all()

        if not teams:
            print("Error: No teams found. Please seed teams first.")
            return

        for team in teams:
            if team.group:
                session.add(GroupStanding(
                    group_letter=team.group,
                    team_id=team.id,
                    played=0,
                    won=0,
                    drawn=0,
                    lost=0,
                    goals_for=0,
                    goals_against=0,
                    goal_difference=0,
                    points=0,
                ))

        session.commit()
        print(f"Successfully initialized group standings for {len(teams)} teams!")


def main():
    """Main function to seed the database."""
    print("="*60)
    print("FIFA WORLD CUP 2026 - DYNAMIC DATABASE SEEDER")
    print("="*60)

    # Extract groups from CSV first
    csv_file = 'mockups/group_stage_matches.csv'
    print(f"\nAnalyzing CSV: {csv_file}")
    groups_in_csv = extract_groups_from_csv(csv_file)
    print(f"Detected {len(groups_in_csv)} groups: {', '.join(groups_in_csv)}")

    print("\nCreating database tables...")
    create_db_and_tables()

    print("\nSeeding teams from CSV...")
    seed_teams_from_csv(csv_file)

    print("\nSeeding matches from CSV (with dynamic knockout generation)...")
    seed_matches_from_csv(csv_file)

    print("\nInitializing group standings...")
    seed_group_standings()

    print("\n" + "="*60)
    print("DATABASE SEEDING COMPLETE!")
    print("="*60)
    print("\nFinal Summary:")
    with Session(engine) as session:
        from sqlalchemy import func
        team_count = session.exec(select(func.count(Team.id))).first()
        match_count = session.exec(select(func.count(Match.id))).first()
        groups = get_all_groups(session)
        print(f"  Teams: {team_count}")
        print(f"  Matches: {match_count}")
        print(f"  Groups: {len(groups)} ({', '.join(groups)})")

        # Show knockout structure
        from app.tournament_config import generate_knockout_bracket_structure
        qualifying_teams = len(groups) * 2
        knockout_structure = generate_knockout_bracket_structure(qualifying_teams)
        print(f"\nKnockout Structure:")
        for round_name, num_matches, _, desc in knockout_structure:
            print(f"  {round_name}: {num_matches} match{'es' if num_matches > 1 else ''}")


if __name__ == "__main__":
    main()
