#!/usr/bin/env python3
"""
Generate dummy results for FIFA World Cup 2026 matches.

This script simulates tournament results for testing purposes.
It generates random scores, calculates standings, resolves knockout brackets,
and triggers scoring for all user predictions.

Usage:
    python -m app.scripts.generate_dummy_results --all
    python -m app.scripts.generate_dummy_results --round group_stage
    python -m app.scripts.generate_dummy_results --reset
    python -m app.scripts.generate_dummy_results --all --seed 42
"""

import argparse
import random
import sys
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple, Any

from sqlmodel import Session, select

# Add parent to path for imports
sys.path.insert(0, str(__file__).rsplit("/app/", 1)[0])

from app.database import engine
from app.models.match import Match
from app.models.fifa_team import FifaTeam

# Scoring is disabled for dummy results - the SQLAlchemy model relationships
# require all related models to be imported which adds unnecessary complexity.
# Scoring can be triggered separately via the admin interface if needed.
SCORING_ENABLED = False

if SCORING_ENABLED:
    from app.models.prediction import Prediction
    from app.services.scoring import calculate_match_points
else:
    Prediction = None
    calculate_match_points = None

def is_scoring_available(db) -> bool:
    """Check if scoring should be performed."""
    return SCORING_ENABLED and calculate_match_points is not None


# Match number ranges for each round
ROUND_RANGES = {
    "group_stage": (1, 72),
    "round_of_32": (73, 88),
    "round_of_16": (89, 96),
    "quarter_final": (97, 100),
    "semi_final": (101, 102),
    "third_place": (103, 103),
    "final": (104, 104),
}

# Round of 32 bracket structure (home_slot vs away_slot)
R32_MATCHUPS = [
    ("1A", "2B"), ("1C", "2D"), ("1E", "2F"), ("1G", "2H"),
    ("1I", "2J"), ("1K", "2L"), ("1B", "2A"), ("1D", "2C"),
    ("1F", "2E"), ("1H", "2G"), ("1J", "2I"), ("1L", "2K"),
    ("3-1", "3-5"), ("3-2", "3-6"), ("3-3", "3-7"), ("3-4", "3-8"),
]


def generate_score(max_goals: int = 4) -> Tuple[int, int]:
    """Generate a random match score."""
    home = random.randint(0, max_goals)
    away = random.randint(0, max_goals)
    return home, away


def generate_knockout_score(max_goals: int = 3, draw_probability: float = 0.2) -> Tuple[int, int, bool]:
    """
    Generate a random knockout match score.
    Returns (home_score, away_score, went_to_penalties).
    """
    home, away = generate_score(max_goals)

    # Simulate penalty shootout if draw
    went_to_penalties = (home == away)

    return home, away, went_to_penalties


def calculate_actual_group_standings(
    db: Session,
    group_letter: str
) -> List[Dict[str, Any]]:
    """
    Calculate group standings based on ACTUAL match results.
    Returns teams sorted by: Points > Goal Diff > Goals Scored
    """
    # Get all group stage matches for this group
    matches = db.exec(
        select(Match).where(
            Match.round == "group_stage",
            Match.group_letter == group_letter,
            Match.status == "completed"
        )
    ).all()

    # Get teams in this group
    teams = db.exec(
        select(FifaTeam).where(FifaTeam.group_letter == group_letter)
    ).all()

    # Initialize team stats
    teams_stats: Dict[int, Dict[str, Any]] = {}
    for team in teams:
        teams_stats[team.id] = {
            "team_id": team.id,
            "team_name": team.name,
            "country_code": team.country_code,
            "flag_emoji": team.flag_emoji,
            "group": group_letter,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_diff": 0,
            "points": 0
        }

    # Process each completed match
    for match in matches:
        if match.home_team_id not in teams_stats or match.away_team_id not in teams_stats:
            continue

        if match.actual_home_score is None or match.actual_away_score is None:
            continue

        home_score = match.actual_home_score
        away_score = match.actual_away_score

        home_stats = teams_stats[match.home_team_id]
        away_stats = teams_stats[match.away_team_id]

        # Update played
        home_stats["played"] += 1
        away_stats["played"] += 1

        # Update goals
        home_stats["goals_for"] += home_score
        home_stats["goals_against"] += away_score
        away_stats["goals_for"] += away_score
        away_stats["goals_against"] += home_score

        # Determine winner and update points
        if home_score > away_score:
            home_stats["won"] += 1
            home_stats["points"] += 3
            away_stats["lost"] += 1
        elif away_score > home_score:
            away_stats["won"] += 1
            away_stats["points"] += 3
            home_stats["lost"] += 1
        else:  # draw
            home_stats["drawn"] += 1
            away_stats["drawn"] += 1
            home_stats["points"] += 1
            away_stats["points"] += 1

    # Calculate goal difference
    for stats in teams_stats.values():
        stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]

    # Sort by points, then goal diff, then goals scored
    sorted_standings = sorted(
        teams_stats.values(),
        key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]),
        reverse=True
    )

    # Add position
    for i, standing in enumerate(sorted_standings):
        standing["position"] = i + 1

    return sorted_standings


def get_actual_third_place_teams(db: Session) -> List[Dict[str, Any]]:
    """
    Get all third-place teams from all groups based on ACTUAL results.
    Sorted by: Points > Goal Diff > Goals Scored
    """
    third_place_teams = []

    for group in "ABCDEFGHIJKL":
        standings = calculate_actual_group_standings(db, group)
        if len(standings) >= 3:
            third_place = standings[2].copy()
            third_place["group"] = group
            third_place_teams.append(third_place)

    # Sort third-place teams
    sorted_thirds = sorted(
        third_place_teams,
        key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]),
        reverse=True
    )

    # Add rank
    for i, team in enumerate(sorted_thirds):
        team["rank"] = i + 1
        team["qualifies"] = i < 8  # Top 8 third-place teams qualify

    return sorted_thirds


def resolve_actual_knockout_teams(db: Session) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Resolve which teams qualify for knockout rounds based on actual results.
    Returns a dict mapping bracket slots to team info.
    """
    slot_to_team: Dict[str, Optional[Dict[str, Any]]] = {}

    # Get group winners and runners-up
    for group in "ABCDEFGHIJKL":
        standings = calculate_actual_group_standings(db, group)
        if len(standings) >= 2:
            slot_to_team[f"1{group}"] = standings[0]  # Winner
            slot_to_team[f"2{group}"] = standings[1]  # Runner-up

    # Get qualified third-place teams
    thirds = get_actual_third_place_teams(db)
    for i, team in enumerate(thirds[:8]):
        slot_to_team[f"3-{i + 1}"] = team

    return slot_to_team


def generate_group_stage_results(db: Session, verbose: bool = True) -> int:
    """Generate results for all group stage matches."""
    start, end = ROUND_RANGES["group_stage"]
    matches = db.exec(
        select(Match).where(
            Match.match_number >= start,
            Match.match_number <= end
        ).order_by(Match.match_number)
    ).all()

    count = 0
    for match in matches:
        if match.home_team_id is None or match.away_team_id is None:
            if verbose:
                print(f"  Skipping match {match.match_number}: teams not assigned")
            continue

        home_score, away_score = generate_score()

        match.actual_home_score = home_score
        match.actual_away_score = away_score
        match.status = "completed"
        match.updated_at = datetime.now(UTC)

        db.add(match)
        count += 1

        if verbose:
            home_team = db.get(FifaTeam, match.home_team_id)
            away_team = db.get(FifaTeam, match.away_team_id)
            home_name = home_team.name if home_team else "TBD"
            away_name = away_team.name if away_team else "TBD"
            print(f"  Match {match.match_number}: {home_name} {home_score} - {away_score} {away_name}")

    db.commit()

    # Calculate points for all predictions (if scoring tables exist)
    if is_scoring_available(db):
        for match in matches:
            if match.status == "completed":
                try:
                    calculate_match_points(db, match)
                except Exception as e:
                    if verbose:
                        print(f"  Warning: Could not calculate points for match {match.match_number}: {e}")

    return count


def assign_knockout_teams(db: Session, verbose: bool = True) -> None:
    """Assign actual teams to knockout matches based on group stage results."""
    slot_to_team = resolve_actual_knockout_teams(db)

    if verbose:
        print("\n  Resolved knockout qualifiers:")
        for slot, team in slot_to_team.items():
            if team:
                print(f"    {slot}: {team['team_name']}")

    # Update Round of 32 matches
    for i, (home_slot, away_slot) in enumerate(R32_MATCHUPS):
        match_number = 73 + i
        match = db.exec(
            select(Match).where(Match.match_number == match_number)
        ).first()

        if match:
            home_team = slot_to_team.get(home_slot)
            away_team = slot_to_team.get(away_slot)

            match.home_team_id = home_team["team_id"] if home_team else None
            match.away_team_id = away_team["team_id"] if away_team else None
            match.updated_at = datetime.now(UTC)
            db.add(match)

    db.commit()


def generate_knockout_round_results(
    db: Session,
    round_name: str,
    verbose: bool = True
) -> int:
    """Generate results for a specific knockout round."""
    if round_name not in ROUND_RANGES:
        print(f"Unknown round: {round_name}")
        return 0

    start, end = ROUND_RANGES[round_name]
    matches = db.exec(
        select(Match).where(
            Match.match_number >= start,
            Match.match_number <= end
        ).order_by(Match.match_number)
    ).all()

    count = 0
    winners: List[Tuple[int, int]] = []  # (match_number, winner_team_id)
    losers: List[Tuple[int, int]] = []   # For semi-finals tracking

    for match in matches:
        if match.home_team_id is None or match.away_team_id is None:
            if verbose:
                print(f"  Skipping match {match.match_number}: teams not assigned")
            continue

        home_score, away_score, went_to_penalties = generate_knockout_score()

        match.actual_home_score = home_score
        match.actual_away_score = away_score
        match.status = "completed"
        match.updated_at = datetime.now(UTC)

        # Determine winner
        if home_score > away_score:
            match.actual_winner_team_id = match.home_team_id
            loser_id = match.away_team_id
        elif away_score > home_score:
            match.actual_winner_team_id = match.away_team_id
            loser_id = match.home_team_id
        else:
            # Penalty shootout - random winner
            if random.random() < 0.5:
                match.actual_winner_team_id = match.home_team_id
                loser_id = match.away_team_id
            else:
                match.actual_winner_team_id = match.away_team_id
                loser_id = match.home_team_id

        winners.append((match.match_number, match.actual_winner_team_id))
        losers.append((match.match_number, loser_id))

        db.add(match)
        count += 1

        if verbose:
            home_team = db.get(FifaTeam, match.home_team_id)
            away_team = db.get(FifaTeam, match.away_team_id)
            winner_team = db.get(FifaTeam, match.actual_winner_team_id)
            home_name = home_team.name if home_team else "TBD"
            away_name = away_team.name if away_team else "TBD"
            winner_name = winner_team.name if winner_team else "TBD"
            penalty_str = " (penalties)" if went_to_penalties else ""
            print(f"  Match {match.match_number}: {home_name} {home_score} - {away_score} {away_name} | Winner: {winner_name}{penalty_str}")

    db.commit()

    # Calculate points for all predictions (if scoring tables exist)
    if is_scoring_available(db):
        for match in matches:
            if match.status == "completed":
                try:
                    calculate_match_points(db, match)
                except Exception as e:
                    if verbose:
                        print(f"  Warning: Could not calculate points for match {match.match_number}: {e}")

    # Assign winners to next round
    assign_next_round_teams(db, round_name, winners, losers, verbose)

    return count


def assign_next_round_teams(
    db: Session,
    current_round: str,
    winners: List[Tuple[int, int]],
    losers: List[Tuple[int, int]],
    verbose: bool = True
) -> None:
    """Assign winners to the next knockout round matches."""
    next_round_map = {
        "round_of_32": ("round_of_16", 89),
        "round_of_16": ("quarter_final", 97),
        "quarter_final": ("semi_final", 101),
        "semi_final": ("final", 104),
    }

    if current_round not in next_round_map:
        return

    next_round, start_match = next_round_map[current_round]

    # Sort winners by match number
    winners.sort(key=lambda x: x[0])

    # Special handling for semi-finals -> final and third place
    if current_round == "semi_final":
        losers.sort(key=lambda x: x[0])

        # Third place match (match 103)
        third_place_match = db.exec(
            select(Match).where(Match.match_number == 103)
        ).first()
        if third_place_match and len(losers) >= 2:
            third_place_match.home_team_id = losers[0][1]
            third_place_match.away_team_id = losers[1][1]
            third_place_match.updated_at = datetime.now(UTC)
            db.add(third_place_match)
            if verbose:
                home = db.get(FifaTeam, losers[0][1])
                away = db.get(FifaTeam, losers[1][1])
                print(f"  Third place: {home.name if home else 'TBD'} vs {away.name if away else 'TBD'}")

        # Final (match 104)
        final_match = db.exec(
            select(Match).where(Match.match_number == 104)
        ).first()
        if final_match and len(winners) >= 2:
            final_match.home_team_id = winners[0][1]
            final_match.away_team_id = winners[1][1]
            final_match.updated_at = datetime.now(UTC)
            db.add(final_match)
            if verbose:
                home = db.get(FifaTeam, winners[0][1])
                away = db.get(FifaTeam, winners[1][1])
                print(f"  Final: {home.name if home else 'TBD'} vs {away.name if away else 'TBD'}")
    else:
        # Pair up winners for next round
        for i in range(0, len(winners), 2):
            if i + 1 >= len(winners):
                break

            match_number = start_match + (i // 2)
            next_match = db.exec(
                select(Match).where(Match.match_number == match_number)
            ).first()

            if next_match:
                next_match.home_team_id = winners[i][1]
                next_match.away_team_id = winners[i + 1][1]
                next_match.updated_at = datetime.now(UTC)
                db.add(next_match)

                if verbose:
                    home = db.get(FifaTeam, winners[i][1])
                    away = db.get(FifaTeam, winners[i + 1][1])
                    print(f"  Next match {match_number}: {home.name if home else 'TBD'} vs {away.name if away else 'TBD'}")

    db.commit()


def generate_all_results(db: Session, verbose: bool = True) -> Dict[str, int]:
    """Generate results for all matches in the tournament."""
    results = {}

    print("\n[GROUP STAGE]")
    results["group_stage"] = generate_group_stage_results(db, verbose)

    print("\n[ASSIGNING KNOCKOUT TEAMS]")
    assign_knockout_teams(db, verbose)

    knockout_rounds = [
        "round_of_32",
        "round_of_16",
        "quarter_final",
        "semi_final",
        "third_place",
        "final"
    ]

    for round_name in knockout_rounds:
        print(f"\n[{round_name.upper().replace('_', ' ')}]")
        results[round_name] = generate_knockout_round_results(db, round_name, verbose)

    return results


def reset_all_results(db: Session, verbose: bool = True) -> int:
    """Reset all actual results to None and status to scheduled."""
    matches = db.exec(select(Match)).all()

    count = 0
    for match in matches:
        if match.actual_home_score is not None or match.actual_away_score is not None:
            match.actual_home_score = None
            match.actual_away_score = None
            match.actual_winner_team_id = None
            match.status = "scheduled"
            match.updated_at = datetime.now(UTC)
            db.add(match)
            count += 1

    # Also reset points earned on predictions (if tables exist)
    if is_scoring_available(db) and Prediction is not None:
        try:
            predictions = db.exec(select(Prediction)).all()
            for pred in predictions:
                if pred.points_earned != 0:
                    pred.points_earned = 0
                    db.add(pred)
        except Exception:
            pass  # Prediction table may not exist

    # Reset knockout match team assignments (keep group stage teams)
    knockout_start = ROUND_RANGES["round_of_32"][0]
    knockout_matches = db.exec(
        select(Match).where(Match.match_number >= knockout_start)
    ).all()

    for match in knockout_matches:
        # Only clear if this was dynamically assigned (not preset)
        # For simplicity, clear all knockout team assignments
        match.home_team_id = None
        match.away_team_id = None
        db.add(match)

    db.commit()

    if verbose:
        print(f"Reset {count} matches and cleared prediction points")

    return count


def show_standings(db: Session) -> None:
    """Display current group standings based on actual results."""
    print("\n=== GROUP STANDINGS ===\n")

    for group in "ABCDEFGHIJKL":
        standings = calculate_actual_group_standings(db, group)
        if not standings:
            continue

        print(f"Group {group}:")
        print(f"  {'Pos':<4} {'Team':<20} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<5} {'Pts':<4}")
        print(f"  {'-'*60}")

        for team in standings:
            print(f"  {team['position']:<4} {team['team_name']:<20} {team['played']:<3} {team['won']:<3} {team['drawn']:<3} {team['lost']:<3} {team['goals_for']:<4} {team['goals_against']:<4} {team['goal_diff']:<5} {team['points']:<4}")
        print()


def show_third_place(db: Session) -> None:
    """Display third-place team rankings."""
    print("\n=== THIRD-PLACE TEAMS ===\n")

    thirds = get_actual_third_place_teams(db)

    print(f"  {'Rank':<5} {'Team':<20} {'Group':<6} {'Pts':<4} {'GD':<5} {'GF':<4} {'Status':<10}")
    print(f"  {'-'*60}")

    for team in thirds:
        status = "Qualifies" if team["qualifies"] else "Eliminated"
        print(f"  {team['rank']:<5} {team['team_name']:<20} {team['group']:<6} {team['points']:<4} {team['goal_diff']:<5} {team['goals_for']:<4} {status:<10}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate dummy results for FIFA World Cup 2026 matches"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate results for all matches"
    )

    parser.add_argument(
        "--round",
        type=str,
        choices=list(ROUND_RANGES.keys()),
        help="Generate results for a specific round"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all actual results to None"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible results"
    )

    parser.add_argument(
        "--standings",
        action="store_true",
        help="Show current group standings"
    )

    parser.add_argument(
        "--thirds",
        action="store_true",
        help="Show third-place team rankings"
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress detailed output"
    )

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    verbose = not args.quiet

    with Session(engine) as db:
        if args.reset:
            print("Resetting all results...")
            reset_all_results(db, verbose)
            print("Done!")

        elif args.all:
            print("Generating results for all matches...")
            results = generate_all_results(db, verbose)
            print("\n=== SUMMARY ===")
            total = sum(results.values())
            for round_name, count in results.items():
                print(f"  {round_name}: {count} matches")
            print(f"  Total: {total} matches")

        elif args.round:
            print(f"Generating results for {args.round}...")

            if args.round == "group_stage":
                count = generate_group_stage_results(db, verbose)
            else:
                # For knockout rounds, need to ensure teams are assigned
                if args.round == "round_of_32":
                    assign_knockout_teams(db, verbose)
                count = generate_knockout_round_results(db, args.round, verbose)

            print(f"\nGenerated {count} match results")

        elif args.standings:
            show_standings(db)

        elif args.thirds:
            show_third_place(db)

        else:
            parser.print_help()


if __name__ == "__main__":
    main()
