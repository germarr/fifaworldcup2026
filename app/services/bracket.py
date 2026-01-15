from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from ..models.match import Match
from ..models.prediction import Prediction
from ..models.fifa_team import FifaTeam
from ..models.third_place_ranking import UserThirdPlaceRanking
from .standings import calculate_group_standings, get_third_place_teams


def get_user_bracket(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Build the complete bracket for a user based on their predictions.
    Returns group winners, runners-up, qualified third-place teams,
    and knockout round matchups.
    """
    bracket = {
        "groups": {},
        "third_place": [],
        "round_of_32": [],
        "round_of_16": [],
        "quarter_finals": [],
        "semi_finals": [],
        "third_place_match": None,
        "final": None
    }

    # Get group standings
    for group in "ABCDEFGHIJKL":
        standings = calculate_group_standings(db, user_id, group)
        bracket["groups"][group] = standings

    # Get third-place rankings (user's manual ordering if available)
    user_rankings = db.exec(
        select(UserThirdPlaceRanking)
        .where(UserThirdPlaceRanking.user_id == user_id)
        .order_by(UserThirdPlaceRanking.rank_position)
    ).all()

    if user_rankings:
        # Use user's manual ranking
        third_place = []
        for ranking in user_rankings:
            team = db.get(FifaTeam, ranking.team_id)
            if team:
                # Find the team's stats from their group
                group_standings = bracket["groups"].get(team.group_letter, [])
                team_stats = next((t for t in group_standings if t["team_id"] == team.id), None)
                if team_stats:
                    team_stats = team_stats.copy()
                    team_stats["rank"] = ranking.rank_position
                    team_stats["qualifies"] = ranking.rank_position <= 8
                    third_place.append(team_stats)
        bracket["third_place"] = third_place
    else:
        # Calculate automatically
        bracket["third_place"] = get_third_place_teams(db, user_id)

    # Build knockout bracket
    bracket["round_of_32"] = build_round_of_32(db, user_id, bracket)

    return bracket


def build_round_of_32(
    db: Session,
    user_id: int,
    bracket: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Build Round of 32 matchups based on FIFA 2026 bracket structure.
    With 48 teams: 24 group qualifiers + 8 best third-place teams = 32 teams
    """
    # FIFA 2026 Round of 32 structure (example - actual bracket TBD)
    # This is a simplified structure - actual FIFA bracket will be different
    r32_matches = []

    # Get qualified teams
    group_winners = {}
    group_runners_up = {}
    qualified_thirds = []

    for group, standings in bracket["groups"].items():
        if len(standings) >= 2:
            group_winners[group] = standings[0]
            group_runners_up[group] = standings[1]

    for third in bracket["third_place"][:8]:
        qualified_thirds.append(third)

    # Example R32 structure (simplified)
    # Match 1: 1A vs 3C/D/E/F
    # Match 2: 1B vs 3A/D/E/F
    # etc.

    # For now, create placeholder structure
    # In real implementation, follow FIFA's official bracket

    matchups = [
        ("1A", "2B"), ("1C", "2D"), ("1E", "2F"), ("1G", "2H"),
        ("1I", "2J"), ("1K", "2L"), ("1B", "2A"), ("1D", "2C"),
        ("1F", "2E"), ("1H", "2G"), ("1J", "2I"), ("1L", "2K"),
        # Third place matchups would go here
    ]

    for i, (home_slot, away_slot) in enumerate(matchups):
        home_team = resolve_slot(home_slot, group_winners, group_runners_up, qualified_thirds)
        away_team = resolve_slot(away_slot, group_winners, group_runners_up, qualified_thirds)
        
        # Find the actual match ID from database
        match_number = 73 + i
        match_obj = db.exec(
            select(Match).where(Match.match_number == match_number)
        ).first()
        
        match_id = match_obj.id if match_obj else None
        
        # Get prediction if it exists
        prediction = None
        if match_id:
            pred = db.exec(
                select(Prediction).where(
                    Prediction.user_id == user_id,
                    Prediction.match_id == match_id
                )
            ).first()
            if pred:
                prediction = {
                    "id": pred.id,
                    "predicted_outcome": pred.predicted_outcome,
                    "predicted_winner_team_id": pred.predicted_winner_team_id,
                    "predicted_home_score": pred.predicted_home_score,
                    "predicted_away_score": pred.predicted_away_score
                }

        r32_matches.append({
            "match_id": match_id,
            "match_number": match_number,
            "home_slot": home_slot,
            "away_slot": away_slot,
            "home_team": home_team,
            "away_team": away_team,
            "prediction": prediction,
            "locked": False  # Would check match.scheduled_datetime
        })

    return r32_matches


def resolve_slot(
    slot: str,
    winners: Dict[str, Dict],
    runners_up: Dict[str, Dict],
    thirds: List[Dict]
) -> Optional[Dict]:
    """
    Resolve a bracket slot to a team.
    Slot format: "1A" = winner of group A, "2A" = runner-up of group A
    """
    if not slot:
        return None

    if slot.startswith("1"):
        group = slot[1]
        return winners.get(group)
    elif slot.startswith("2"):
        group = slot[1]
        return runners_up.get(group)
    elif slot.startswith("3"):
        # Third place - would need more complex logic
        idx = int(slot[3:]) - 1 if len(slot) > 3 else 0
        return thirds[idx] if idx < len(thirds) else None

    return None
