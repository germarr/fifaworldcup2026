#!/usr/bin/env python3
"""
Import Group Stage Results from CSV
------------------------------------
Reads the CSV file with actual match results and updates the database.
Also updates official group standings after importing.
"""

import csv
import sys
from sqlmodel import Session, select
from app.database import engine
from app.models import Match
from simulations.simulate_full_tournament import update_official_standings


def import_group_results_from_csv(csv_file='mockups/group_stage_matches.csv', dry_run=False):
    """
    Import actual match results from CSV file.

    Args:
        csv_file: Path to CSV file
        dry_run: If True, show changes without saving to database
    """
    print(f"\n{'='*60}")
    print(f"📥 Importing Group Stage Results from CSV")
    print(f"{'='*60}")
    print(f"Source: {csv_file}")
    print(f"Mode: {'DRY RUN (no changes will be saved)' if dry_run else 'LIVE (database will be updated)'}")
    print(f"{'='*60}\n")

    with Session(engine) as db:
        matches_updated = 0
        matches_skipped = 0
        errors = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    match_number = int(row['match_number'])

                    # Get match from database
                    statement = select(Match).where(Match.match_number == match_number)
                    match = db.exec(statement).first()

                    if not match:
                        error_msg = f"Match #{match_number} not found in database"
                        errors.append(error_msg)
                        print(f"❌ {error_msg}")
                        continue

                    # Verify it's a group stage match
                    if not match.round.startswith("Group Stage"):
                        error_msg = f"Match #{match_number} is not a group stage match (round: {match.round})"
                        errors.append(error_msg)
                        print(f"⚠️  {error_msg}")
                        matches_skipped += 1
                        continue

                    # Parse scores (handle empty values)
                    actual_team1_score = row['actual_team1_score'].strip()
                    actual_team2_score = row['actual_team2_score'].strip()

                    if actual_team1_score == '' or actual_team2_score == '':
                        print(f"⏭️  Match #{match_number:2} ({row['team1_code']:3} vs {row['team2_code']:3}): No scores provided, skipping")
                        matches_skipped += 1
                        continue

                    try:
                        team1_score = int(actual_team1_score)
                        team2_score = int(actual_team2_score)
                    except ValueError:
                        error_msg = f"Match #{match_number}: Invalid score values ('{actual_team1_score}' - '{actual_team2_score}')"
                        errors.append(error_msg)
                        print(f"❌ {error_msg}")
                        continue

                    # Parse is_finished
                    is_finished = row['is_finished'].strip().upper() == 'TRUE'

                    # Parse new metadata fields
                    stadium = row.get('stadium', '').strip() or None
                    time = row.get('time', '').strip() or None
                    datetime_str = row.get('datetime', '').strip() or None

                    # Check if scores or metadata have changed
                    score_changed = (
                        match.actual_team1_score != team1_score or
                        match.actual_team2_score != team2_score or
                        match.is_finished != is_finished
                    )

                    metadata_changed = (
                        match.stadium != stadium or
                        match.time != time or
                        match.datetime_str != datetime_str
                    )

                    if score_changed or metadata_changed:
                        old_score = f"{match.actual_team1_score if match.actual_team1_score is not None else '-'}-{match.actual_team2_score if match.actual_team2_score is not None else '-'}"
                        new_score = f"{team1_score}-{team2_score}"

                        status = "✅ UPDATE" if not dry_run else "🔍 WOULD UPDATE"
                        changes = []
                        if score_changed:
                            changes.append(f"{old_score} → {new_score}")
                        if metadata_changed:
                            if match.stadium != stadium:
                                changes.append(f"stadium: {match.stadium or 'None'} → {stadium or 'None'}")
                            if match.time != time:
                                changes.append(f"time: {match.time or 'None'} → {time or 'None'}")

                        print(f"{status} Match #{match_number:2} ({row['team1_code']:3} vs {row['team2_code']:3}): {' | '.join(changes)} | Finished: {is_finished}")

                        if not dry_run:
                            match.actual_team1_score = team1_score
                            match.actual_team2_score = team2_score
                            match.is_finished = is_finished
                            match.stadium = stadium
                            match.time = time
                            match.datetime_str = datetime_str
                            db.add(match)

                        matches_updated += 1
                    else:
                        print(f"⏭️  Match #{match_number:2} ({row['team1_code']:3} vs {row['team2_code']:3}): {team1_score}-{team2_score} (no changes)")
                        matches_skipped += 1

            if not dry_run:
                db.commit()
                print(f"\n{'='*60}")
                print(f"💾 Database committed successfully!")
                print(f"{'='*60}")

                # Update official standings
                print(f"\n{'='*60}")
                print(f"📊 Updating Official Group Standings...")
                print(f"{'='*60}\n")
                update_official_standings(db)
                print(f"\n✅ Official standings updated!")

        except FileNotFoundError:
            print(f"\n❌ Error: CSV file not found: {csv_file}")
            print(f"\nPlease run: python export_group_matches_csv.py")
            return False
        except Exception as e:
            print(f"\n❌ Error during import: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Print summary
        print(f"\n{'='*60}")
        print(f"📈 IMPORT SUMMARY")
        print(f"{'='*60}")
        print(f"Matches Updated:  {matches_updated}")
        print(f"Matches Skipped:  {matches_skipped}")
        print(f"Errors:           {len(errors)}")

        if errors:
            print(f"\n⚠️  Errors encountered:")
            for error in errors:
                print(f"  - {error}")

        print(f"\n{'✓ Import completed successfully!' if len(errors) == 0 else '⚠️  Import completed with errors'}")
        print(f"{'='*60}\n")

        return len(errors) == 0


if __name__ == "__main__":
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("\n🔍 DRY RUN MODE: No changes will be saved to database\n")

    try:
        success = import_group_results_from_csv(dry_run=dry_run)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Import cancelled by user")
        sys.exit(1)
