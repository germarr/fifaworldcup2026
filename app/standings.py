"""
Group standings calculation based on user predictions.
"""

from typing import Dict, List, Optional
from sqlmodel import Session, select
from app.models import Match, Prediction, Team
from app.flags import flag_url


class TeamStanding:
    """Represents a team's standing in a group."""

    def __init__(self, team: Team):
        self.team = team
        self.played = 0
        self.won = 0
        self.drawn = 0
        self.lost = 0
        self.goals_for = 0
        self.goals_against = 0
        self.points = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "team_id": self.team.id,
            "team_name": self.team.name,
            "team_code": self.team.code,
            "team_flag_url": flag_url(self.team.code, 40),
            "played": self.played,
            "won": self.won,
            "drawn": self.drawn,
            "lost": self.lost,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
        }

    def __repr__(self):
        return f"{self.team.name}: {self.points}pts (GD: {self.goal_difference})"


def calculate_group_standings(user_id: int, db: Session) -> Dict[str, List[TeamStanding]]:
    """
    Calculate group standings based on user's predictions.

    Args:
        user_id: User ID to calculate standings for
        db: Database session

    Returns:
        Dictionary mapping group letter to list of TeamStanding objects (sorted)
    """
    # Get all group stage matches
    group_matches_statement = select(Match).where(Match.round.like("Group Stage%"))
    group_matches = db.exec(group_matches_statement).all()

    # Get all predictions for this user on group stage matches
    match_ids = [m.id for m in group_matches]
    predictions_statement = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.match_id.in_(match_ids)
    )
    predictions = db.exec(predictions_statement).all()

    # Create a mapping of match_id to prediction
    predictions_map = {p.match_id: p for p in predictions}

    # Get all teams
    teams_statement = select(Team)
    teams = db.exec(teams_statement).all()
    teams_map = {t.id: t for t in teams}

    # Initialize standings for each group
    groups: Dict[str, Dict[int, TeamStanding]] = {}
    for group_letter in "ABCDEFGH":
        groups[group_letter] = {}

    # Populate groups with teams
    for team in teams:
        if team.group:
            if team.id not in groups[team.group]:
                groups[team.group][team.id] = TeamStanding(team)

    # Process each group stage match with predictions
    for match in group_matches:
        prediction = predictions_map.get(match.id)

        if not prediction:
            continue  # Skip matches without predictions

        # Get the group from the match round (e.g., "Group Stage - Group A" -> "A")
        group_letter = match.round.split("Group ")[-1] if "Group " in match.round else None

        if not group_letter or group_letter not in groups:
            continue

        team1_id = match.team1_id
        team2_id = match.team2_id

        if team1_id not in groups[group_letter] or team2_id not in groups[group_letter]:
            continue

        team1_standing = groups[group_letter][team1_id]
        team2_standing = groups[group_letter][team2_id]

        # Update match statistics
        team1_standing.played += 1
        team2_standing.played += 1

        team1_standing.goals_for += prediction.predicted_team1_score
        team1_standing.goals_against += prediction.predicted_team2_score

        team2_standing.goals_for += prediction.predicted_team2_score
        team2_standing.goals_against += prediction.predicted_team1_score

        # Determine result and update points
        if prediction.predicted_team1_score > prediction.predicted_team2_score:
            # Team 1 wins
            team1_standing.won += 1
            team1_standing.points += 3
            team2_standing.lost += 1
        elif prediction.predicted_team2_score > prediction.predicted_team1_score:
            # Team 2 wins
            team2_standing.won += 1
            team2_standing.points += 3
            team1_standing.lost += 1
        else:
            # Draw
            team1_standing.drawn += 1
            team1_standing.points += 1
            team2_standing.drawn += 1
            team2_standing.points += 1

    # Sort each group by FIFA rules
    sorted_groups: Dict[str, List[TeamStanding]] = {}

    for group_letter, teams_dict in groups.items():
        standings_list = list(teams_dict.values())

        # Sort by: 1) Points DESC, 2) Goal Diff DESC, 3) Goals For DESC, 4) Team name (for stability)
        standings_list.sort(
            key=lambda x: (x.points, x.goal_difference, x.goals_for, x.team.name),
            reverse=True
        )

        sorted_groups[group_letter] = standings_list

    return sorted_groups


def get_group_qualifiers(user_id: int, db: Session) -> Dict[str, List[Team]]:
    """
    Get the top 2 teams from each group based on user predictions.

    Args:
        user_id: User ID to calculate qualifiers for
        db: Database session

    Returns:
        Dictionary mapping group letter to list of 2 qualified Team objects
    """
    standings = calculate_group_standings(user_id, db)

    qualifiers: Dict[str, List[Team]] = {}

    for group_letter, standings_list in standings.items():
        # Get top 2 teams
        top_2 = standings_list[:2] if len(standings_list) >= 2 else standings_list
        qualifiers[group_letter] = [ts.team for ts in top_2]

    return qualifiers


def get_group_winner(group: str, user_id: int, db: Session) -> Optional[Team]:
    """Get the winner (1st place) of a specific group."""
    standings = calculate_group_standings(user_id, db)

    if group in standings and len(standings[group]) > 0:
        return standings[group][0].team

    return None


def get_group_runner_up(group: str, user_id: int, db: Session) -> Optional[Team]:
    """Get the runner-up (2nd place) of a specific group."""
    standings = calculate_group_standings(user_id, db)

    if group in standings and len(standings[group]) > 1:
        return standings[group][1].team

    return None
