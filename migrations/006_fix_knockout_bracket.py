#!/usr/bin/env python3
"""
Migration 006: Fix Knockout Bracket Structure
----------------------------------------------
Fixes the knockout bracket to have correct match numbers:
- Round of 32: Matches 73-88 (16 matches)
- Round of 16: Matches 89-96 (8 matches)
- Quarter Finals: Matches 97-100 (4 matches)
- Semi Finals: Matches 101-102 (2 matches)
- Third Place: Match 103 (1 match)
- Final: Match 104 (1 match)

This is the correct structure for 12 groups with 32 qualifying teams
(top 2 from each group + best 8 third-place teams).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import engine
from app.models import Match
from app.tournament_config import (
    get_all_groups,
    generate_knockout_bracket_structure,
    get_knockout_placeholders
)


def migrate_knockout_bracket(dry_run: bool = False):
    """Fix the knockout bracket structure."""
    print("="*60)
    print("MIGRATION 006: Fix Knockout Bracket Structure")
    print("="*60)
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLYING CHANGES'}")
    print("="*60)

    with Session(engine) as session:
        # Get current groups
        groups = get_all_groups(session)
        num_groups = len(groups)

        print(f"\nDetected {num_groups} groups")

        if num_groups != 12:
            print(f"⚠️  This migration is designed for 12 groups (found {num_groups})")
            print("Exiting without changes.")
            return

        # Expected: 32 qualifying teams (24 from top 2 + 8 best third-place)
        qualifying_teams = 32

        print(f"Qualifying teams: {qualifying_teams}")
        print("\nTarget structure:")
        print("  73-88:  Round of 32 (16 matches)")
        print("  89-96:  Round of 16 (8 matches)")
        print("  97-100: Quarter Finals (4 matches)")
        print("  101-102: Semi Finals (2 matches)")
        print("  103: Third Place (1 match)")
        print("  104: Final (1 match)")

        # Get current knockout matches
        knockout_matches = session.exec(
            select(Match).where(~Match.round.like('Group Stage%')).order_by(Match.match_number)
        ).all()

        print(f"\n➖ Deleting {len(knockout_matches)} existing knockout matches...")

        if not dry_run:
            for match in knockout_matches:
                session.delete(match)
            session.commit()

        # Generate new knockout structure
        knockout_structure = generate_knockout_bracket_structure(qualifying_teams)

        print("\n✅ Generating new knockout bracket:")
        for round_name, num_matches, start_match, desc in knockout_structure:
            print(f"  {round_name}: {num_matches} matches (starting at #{start_match})")

        # Get the last group stage match date
        last_group_match = session.exec(
            select(Match).where(Match.round.like('Group Stage%')).order_by(Match.match_date.desc())
        ).first()
        base_knockout_date = last_group_match.match_date if last_group_match else datetime(2026, 6, 29)

        match_number = 73
        total_matches_created = 0

        # First round: Round of 32 with group placeholders (including third-place)
        first_round_name = knockout_structure[0][0]
        first_round_matches = knockout_structure[0][1]
        placeholders = get_knockout_placeholders(num_groups)

        print(f"\n{first_round_name}:")
        for i, (team1_ph, team2_ph) in enumerate(placeholders[:first_round_matches]):
            print(f"  Match {match_number}: {team1_ph} vs {team2_ph}")
            if not dry_run:
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
            match_number += 1
            total_matches_created += 1

        # Subsequent rounds use winner placeholders
        days_offset = 2
        for round_idx in range(1, len(knockout_structure)):
            round_name, num_matches, _, _ = knockout_structure[round_idx]
            days_offset += 3

            print(f"\n{round_name}:")

            if round_name == "Third Place":
                # Third place uses loser placeholders from semis
                prev_round_start = match_number - 2
                print(f"  Match {match_number}: L{prev_round_start - 1} vs L{prev_round_start}")
                if not dry_run:
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
                match_number += 1
                total_matches_created += 1

            elif round_name == "Final":
                # Final uses winner placeholders from semis
                prev_round_start = match_number - 3
                print(f"  Match {match_number}: W{prev_round_start - 1} vs W{prev_round_start}")
                if not dry_run:
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
                match_number += 1
                total_matches_created += 1

            else:
                # Regular knockout rounds (Round of 16, Quarters, Semis)
                prev_round_matches = knockout_structure[round_idx - 1][1]
                prev_round_start = match_number - prev_round_matches

                for i in range(num_matches):
                    w1 = prev_round_start + (i * 2)
                    w2 = prev_round_start + (i * 2) + 1
                    print(f"  Match {match_number}: W{w1} vs W{w2}")
                    if not dry_run:
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
                    match_number += 1
                    total_matches_created += 1

        if not dry_run:
            session.commit()
            print(f"\n✅ Successfully created {total_matches_created} knockout matches")
        else:
            print(f"\n🔍 Would create {total_matches_created} knockout matches")

        # Verify
        if not dry_run:
            print("\nVerifying structure...")
            knockout_matches = session.exec(
                select(Match).where(~Match.round.like('Group Stage%')).order_by(Match.match_number)
            ).all()

            rounds_count = {}
            for match in knockout_matches:
                rounds_count[match.round] = rounds_count.get(match.round, 0) + 1

            print("\nFinal structure:")
            for round_name, count in rounds_count.items():
                print(f"  {round_name}: {count} matches")

        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be applied\n")

    migrate_knockout_bracket(dry_run=dry_run)
