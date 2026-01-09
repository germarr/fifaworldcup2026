#!/usr/bin/env python3
"""
Export Group Stage Matches to CSV
----------------------------------
Creates a CSV file with all group stage matches for easy manual updating of actual results.
"""

import csv
from sqlmodel import Session, select
from app.database import engine
from app.models import Match


def export_group_matches_to_csv(output_file='mockups/group_stage_matches.csv'):
    """
    Export all group stage matches to CSV.

    Args:
        output_file: Path to output CSV file
    """
    with Session(engine) as db:
        # Get all group stage matches
        statement = select(Match).where(
            Match.round.like("Group Stage%")
        ).order_by(Match.match_number)

        matches = db.exec(statement).all()

        # Define CSV columns
        fieldnames = [
            'match_number',
            'round',
            'group',
            'match_date',
            'team1_code',
            'team1_name',
            'team2_code',
            'team2_name',
            'actual_team1_score',
            'actual_team2_score',
            'is_finished'
        ]

        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for match in matches:
                # Extract group letter from round (e.g., "Group Stage - Group A" -> "A")
                group_letter = match.round.split("Group ")[-1] if "Group" in match.round else ""

                row = {
                    'match_number': match.match_number,
                    'round': match.round,
                    'group': group_letter,
                    'match_date': match.match_date.strftime('%Y-%m-%d'),
                    'team1_code': match.team1.code if match.team1 else '',
                    'team1_name': match.team1.name if match.team1 else '',
                    'team2_code': match.team2.code if match.team2 else '',
                    'team2_name': match.team2.name if match.team2 else '',
                    'actual_team1_score': match.actual_team1_score if match.actual_team1_score is not None else '',
                    'actual_team2_score': match.actual_team2_score if match.actual_team2_score is not None else '',
                    'is_finished': 'TRUE' if match.is_finished else 'FALSE'
                }

                writer.writerow(row)

        print(f"✓ Exported {len(matches)} group stage matches to: {output_file}")
        print(f"\nInstructions:")
        print(f"1. Open {output_file} in a spreadsheet editor")
        print(f"2. Fill in actual_team1_score and actual_team2_score columns")
        print(f"3. Set is_finished to TRUE for completed matches")
        print(f"4. Save the CSV")
        print(f"5. Run: python import_group_results_csv.py")


if __name__ == "__main__":
    export_group_matches_to_csv()
