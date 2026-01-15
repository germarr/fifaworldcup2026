#!/usr/bin/env python3
"""
Convert Knockout Matches to Group Stage
---------------------------------------
Converts matches 49-64 from knockout rounds to group stage matches based on CSV.
"""

import csv
import sys
from datetime import datetime
from sqlmodel import Session, select
sys.path.insert(0, '..')
from app.database import engine
from app.models import Match, Team


def convert_knockout_to_group_stage(csv_file='mockups/group_stage_matches.csv', dry_run=False):
    """
    Convert matches 49-64 from knockout to group stage based on CSV.

    Args:
        csv_file: Path to CSV file
        dry_run: If True, show what would be changed without saving
    """
    print(f"\n{'='*60}")
    print(f"🔄 Converting Knockout Matches to Group Stage")
    print(f"{'='*60}")
    print(f"Source: {csv_file}")
    print(f"Mode: {'DRY RUN (no changes will be saved)' if dry_run else 'LIVE (database will be updated)'}")
    print(f"{'='*60}\n")

    with Session(engine) as db:
        matches_updated = 0
        teams_added = 0
        errors = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    match_number = int(row['match_number'])

                    # Only process matches 49-64 (the ones that need conversion)
                    if match_number < 49 or match_number > 64:
                        continue

                    # Get match from database
                    statement = select(Match).where(Match.match_number == match_number)
                    match = db.exec(statement).first()

                    if not match:
                        error_msg = f"Match #{match_number} not found in database"
                        errors.append(error_msg)
                        print(f"❌ {error_msg}")
                        continue

                    print(f"\n🔄 Processing Match #{match_number}: {match.round} → {row['round']}")

                    # Process team1
                    team1_code = row['team1_code'].strip()
                    team1_name = row['team1_name'].strip()
                    team1_id = None
                    team1_placeholder = None

                    if team1_code != 'TBD':
                        # Check by code first
                        team1_stmt = select(Team).where(Team.code == team1_code)
                        team1 = db.exec(team1_stmt).first()

                        # If not found by code, check by name
                        if not team1:
                            team1_stmt = select(Team).where(Team.name == team1_name)
                            team1 = db.exec(team1_stmt).first()

                        if not team1:
                            # Create new team
                            group_letter = row['group'].strip()
                            team1 = Team(
                                name=team1_name,
                                code=team1_code,
                                group=group_letter
                            )
                            if not dry_run:
                                db.add(team1)
                                db.flush()
                                teams_added += 1
                                print(f"  ✅ Created team: {team1_code} - {team1_name} (Group {group_letter})")
                            else:
                                print(f"  🔍 Would create team: {team1_code} - {team1_name} (Group {group_letter})")

                        team1_id = team1.id if team1 and not dry_run else None
                    else:
                        team1_placeholder = team1_name

                    # Process team2
                    team2_code = row['team2_code'].strip()
                    team2_name = row['team2_name'].strip()
                    team2_id = None
                    team2_placeholder = None

                    if team2_code != 'TBD':
                        # Check by code first
                        team2_stmt = select(Team).where(Team.code == team2_code)
                        team2 = db.exec(team2_stmt).first()

                        # If not found by code, check by name
                        if not team2:
                            team2_stmt = select(Team).where(Team.name == team2_name)
                            team2 = db.exec(team2_stmt).first()

                        if not team2:
                            # Create new team
                            group_letter = row['group'].strip()
                            team2 = Team(
                                name=team2_name,
                                code=team2_code,
                                group=group_letter
                            )
                            if not dry_run:
                                db.add(team2)
                                db.flush()
                                teams_added += 1
                                print(f"  ✅ Created team: {team2_code} - {team2_name} (Group {group_letter})")
                            else:
                                print(f"  🔍 Would create team: {team2_code} - {team2_name} (Group {group_letter})")

                        team2_id = team2.id if team2 and not dry_run else None
                    else:
                        team2_placeholder = team2_name

                    # Parse the date
                    date_str = row['date'].strip()
                    match_date = datetime.strptime(date_str, '%m/%d/%Y')

                    # Update the match
                    if not dry_run:
                        match.round = row['round'].strip()
                        match.team1_id = team1_id
                        match.team2_id = team2_id
                        match.team1_placeholder = team1_placeholder
                        match.team2_placeholder = team2_placeholder
                        match.match_date = match_date
                        match.stadium = row.get('stadium', '').strip() or None
                        match.time = row.get('time', '').strip() or None
                        match.datetime_str = row.get('datetime', '').strip() or None
                        match.actual_team1_score = None
                        match.actual_team2_score = None
                        match.is_finished = False
                        db.add(match)
                        print(f"  ✅ Updated: {team1_code} vs {team2_code} - {row['stadium']} - {row['time']}")
                    else:
                        print(f"  🔍 Would update: {team1_code} vs {team2_code} - {row['stadium']} - {row['time']}")

                    matches_updated += 1

            if not dry_run:
                db.commit()
                print(f"\n{'='*60}")
                print(f"💾 Database committed successfully!")
                print(f"{'='*60}")

        except FileNotFoundError:
            print(f"\n❌ Error: CSV file not found: {csv_file}")
            return False
        except Exception as e:
            print(f"\n❌ Error during conversion: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Print summary
        print(f"\n{'='*60}")
        print(f"📈 SUMMARY")
        print(f"{'='*60}")
        print(f"Teams Added:      {teams_added}")
        print(f"Matches Updated:  {matches_updated}")
        print(f"Errors:           {len(errors)}")

        if errors:
            print(f"\n⚠️  Errors encountered:")
            for error in errors:
                print(f"  - {error}")

        print(f"\n{'✓ Conversion completed successfully!' if len(errors) == 0 else '⚠️  Conversion completed with errors'}")
        print(f"{'='*60}\n")

        return len(errors) == 0


if __name__ == "__main__":
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("\n🔍 DRY RUN MODE: No changes will be saved to database\n")

    try:
        success = convert_knockout_to_group_stage(dry_run=dry_run)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
