"""
Dynamic tournament configuration utilities.
Automatically adapts to the number of groups and teams in the database/CSV.
"""

from typing import List, Tuple
from sqlmodel import Session, select
from app.models import Team, Match


def get_all_groups(db: Session) -> List[str]:
    """
    Get all unique group letters from the database, sorted.

    Returns:
        List of group letters (e.g., ['A', 'B', 'C', ...])
    """
    groups = db.exec(select(Team.group).distinct().order_by(Team.group)).all()
    return [g for g in groups if g]


def get_group_count(db: Session) -> int:
    """Get the total number of groups in the tournament."""
    return len(get_all_groups(db))


def get_qualifying_teams_count(db: Session) -> int:
    """
    Calculate how many teams qualify for knockout stage.
    Assumes top 2 teams from each group qualify.
    """
    group_count = get_group_count(db)
    if group_count == 12:
        return 32
    return group_count * 2


def generate_knockout_bracket_structure(num_qualifying_teams: int) -> List[Tuple[str, str, int, str]]:
    """
    Generate knockout bracket structure based on number of qualifying teams.

    Args:
        num_qualifying_teams: Total teams entering knockout stage (e.g., 16, 24, 32, 48)

    Returns:
        List of rounds with their structure:
        [(round_name, num_matches, starting_match_number, description), ...]

    Examples:
        16 teams -> Round of 16 (8), Quarters (4), Semis (2), Third Place (1), Final (1)
        32 teams -> Round of 32 (16), Round of 16 (8), Quarters (4), Semis (2), Third Place (1), Final (1)

    Match numbering for 12 groups (32 teams in knockout):
        73-88: Round of 32 (16 matches)
        89-96: Round of 16 (8 matches)
        97-100: Quarter Finals (4 matches)
        101-102: Semi Finals (2 matches)
        103: Third Place (1 match)
        104: Final (1 match)
    """
    rounds = []
    current_teams = num_qualifying_teams
    match_num = 73  # Assuming 72 group stage matches

    # Handle each power of 2 from current_teams down to 4
    while current_teams >= 4:
        num_matches = current_teams // 2

        if current_teams == 32:
            round_name = "Round of 32"
        elif current_teams == 16:
            round_name = "Round of 16"
        elif current_teams == 8:
            round_name = "Quarter Finals"
        elif current_teams == 4:
            round_name = "Semi Finals"
        else:
            # For non-standard sizes (e.g., 64, 128)
            round_name = f"Round of {current_teams}"

        rounds.append((round_name, num_matches, match_num, f"{num_matches} matches"))
        match_num += num_matches
        current_teams //= 2

    # Third place and Final
    rounds.append(("Third Place", 1, match_num, "Losers of semis"))
    match_num += 1
    rounds.append(("Final", 1, match_num, "Winners of semis"))

    return rounds


def get_knockout_placeholders(num_groups: int) -> List[Tuple[str, str]]:
    """
    Generate appropriate knockout match placeholders based on number of groups.

    Args:
        num_groups: Number of groups in tournament

    Returns:
        List of (team1_placeholder, team2_placeholder) for first knockout round
    """
    group_letters = [chr(65 + i) for i in range(num_groups)]  # A, B, C, ...

    # Calculate qualifying teams (12 groups = 32 teams including third-place)
    if num_groups == 12:
        qualifying_teams = 32  # Top 2 from each group + 8 best third-place
    else:
        qualifying_teams = num_groups * 2  # Top 2 from each group

    if qualifying_teams == 16:
        # Standard 16-team bracket (8 groups)
        return [
            ("1A", "2B"),
            ("1C", "2D"),
            ("1E", "2F"),
            ("1G", "2H"),
            ("1B", "2A"),
            ("1D", "2C"),
            ("1F", "2E"),
            ("1H", "2G"),
        ]
    elif qualifying_teams == 24:
        # 24 teams (12 groups) - need to get to 16
        # Give byes to top 8 group winners (1A-1H)
        # Other 16 teams (1I-1L and all 2nd place) play 8 matches
        return [
            ("1I", "2L"),
            ("1J", "2K"),
            ("1K", "2J"),
            ("1L", "2I"),
            ("2A", "2H"),
            ("2B", "2G"),
            ("2C", "2F"),
            ("2D", "2E"),
        ]
    elif qualifying_teams == 32:
        if num_groups == 12:
            # 48-team format: top 2 per group + best 8 third-place teams.
            # Placeholders like 3ABCDF indicate a third-place team from those groups.
            return [
                ("2A", "2B"),
                ("1C", "2F"),
                ("1E", "3ABCDF"),
                ("1F", "2C"),
                ("2E", "2I"),
                ("1I", "3CDFGH"),
                ("1A", "3CEFHI"),
                ("1L", "3EHIJK"),
                ("1G", "3AEHIJ"),
                ("1D", "3BEFIJ"),
                ("1H", "2J"),
                ("2K", "2L"),
                ("1B", "3EFGIJ"),
                ("2D", "2G"),
                ("1J", "2H"),
                ("1K", "3DEIJL"),
            ]
        # 32 teams (16 groups) - standard Round of 32
        placeholders = []
        for i in range(0, num_groups, 2):
            g1 = group_letters[i]
            g2 = group_letters[i + 1]
            placeholders.append((f"1{g1}", f"2{g2}"))
            placeholders.append((f"1{g2}", f"2{g1}"))
        return placeholders
    else:
        # Generic approach for any number
        # Pair group winners with runners-up from different groups
        placeholders = []
        half = num_groups // 2

        for i in range(half):
            g1 = group_letters[i]
            g2 = group_letters[num_groups - 1 - i]
            placeholders.append((f"1{g1}", f"2{g2}"))
            placeholders.append((f"1{g2}", f"2{g1}"))

        # Handle odd number of groups if needed
        if num_groups % 2 == 1:
            mid = group_letters[half]
            placeholders.append((f"1{mid}", f"2{group_letters[0]}"))

        return placeholders


def get_tournament_info(db: Session) -> dict:
    """
    Get comprehensive tournament information.

    Returns:
        Dictionary with tournament configuration
    """
    groups = get_all_groups(db)
    num_groups = len(groups)
    qualifying_teams = get_qualifying_teams_count(db)

    return {
        'groups': groups,
        'num_groups': num_groups,
        'teams_per_tournament': num_groups * 4,  # Assuming ~4 teams per group average
        'qualifying_teams': qualifying_teams,
        'knockout_structure': generate_knockout_bracket_structure(qualifying_teams),
    }
