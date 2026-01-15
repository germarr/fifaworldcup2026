from typing import List, Dict, Any
from sqlmodel import Session, select
from ..models.match import Match
from ..models.prediction import Prediction
from ..models.fifa_team import FifaTeam


def calculate_group_standings(
    db: Session,
    user_id: int,
    group_letter: str
) -> List[Dict[str, Any]]:
    """
    Calculate group standings based on user's predictions.
    Returns teams sorted by: Points > Goal Diff > Goals Scored
    """
    # Get all group stage matches for this group
    matches_query = select(Match).where(
        Match.round == "group_stage",
        Match.group_letter == group_letter
    )
    matches = db.exec(matches_query).all()

    if not matches:
        return []

    # Get user's predictions for these matches
    match_ids = [m.id for m in matches]
    predictions_query = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.match_id.in_(match_ids)
    )
    predictions = db.exec(predictions_query).all()

    # Create prediction lookup
    pred_by_match = {p.match_id: p for p in predictions}

    # Initialize team stats
    teams_stats: Dict[int, Dict[str, Any]] = {}

    # Get teams in this group
    teams_query = select(FifaTeam).where(FifaTeam.group_letter == group_letter)
    teams = db.exec(teams_query).all()

    for team in teams:
        teams_stats[team.id] = {
            "team_id": team.id,
            "team_name": team.name,
            "country_code": team.country_code,
            "flag_emoji": team.flag_emoji,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_diff": 0,
            "points": 0
        }

    # Process each match
    for match in matches:
        if match.home_team_id not in teams_stats or match.away_team_id not in teams_stats:
            continue

        prediction = pred_by_match.get(match.id)
        if not prediction:
            continue

        home_score = prediction.predicted_home_score or 0
        away_score = prediction.predicted_away_score or 0

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
        if prediction.predicted_outcome == "home_win":
            home_stats["won"] += 1
            home_stats["points"] += 3
            away_stats["lost"] += 1
        elif prediction.predicted_outcome == "away_win":
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


def get_third_place_teams(
    db: Session,
    user_id: int
) -> List[Dict[str, Any]]:
    """
    Get all third-place teams from all groups based on user's predictions.
    Sorted by: Points > Goal Diff > Goals Scored
    """
    third_place_teams = []

    # Get standings for all 12 groups
    for group in "ABCDEFGHIJKL":
        standings = calculate_group_standings(db, user_id, group)
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
