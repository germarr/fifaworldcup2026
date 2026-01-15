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
    bracket["round_of_16"] = build_round_of_16(db, user_id, bracket)
    bracket["quarter_finals"] = build_quarter_finals(db, user_id, bracket)
    bracket["semi_finals"] = build_semi_finals(db, user_id, bracket)
    bracket["third_place_match"] = build_third_place_match(db, user_id, bracket)
    bracket["final"] = build_final(db, user_id, bracket)

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
        ("3-1", "3-5"), ("3-2", "3-6"), ("3-3", "3-7"), ("3-4", "3-8"),
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
        # Third place slot format: "3-1", "3-2", etc.
        if "-" in slot:
            try:
                idx = int(slot.split("-")[1]) - 1
                return thirds[idx] if idx < len(thirds) else None
            except (IndexError, ValueError):
                return None
        return None

    return None


def build_round_of_16(
    db: Session,
    user_id: int,
    bracket: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build Round of 16 matchups from R32 winners."""
    r16_matches = []
    r32_winners = []
    
    for r32_match in bracket["round_of_32"]:
        if r32_match["prediction"] and r32_match["prediction"]["predicted_winner_team_id"]:
            winner_id = r32_match["prediction"]["predicted_winner_team_id"]
            winner_team = r32_match["home_team"] if r32_match["home_team"]["team_id"] == winner_id else r32_match["away_team"]
            r32_winners.append(winner_team)
    
    match_number = 85
    for i in range(0, len(r32_winners), 2):
        home_team = r32_winners[i] if i < len(r32_winners) else None
        away_team = r32_winners[i + 1] if i + 1 < len(r32_winners) else None
        
        match_obj = db.exec(select(Match).where(Match.match_number == match_number)).first()
        match_id = match_obj.id if match_obj else None
        
        prediction = None
        if match_id:
            pred = db.exec(select(Prediction).where(Prediction.user_id == user_id, Prediction.match_id == match_id)).first()
            if pred:
                prediction = {"id": pred.id, "predicted_outcome": pred.predicted_outcome, "predicted_winner_team_id": pred.predicted_winner_team_id, "predicted_home_score": pred.predicted_home_score, "predicted_away_score": pred.predicted_away_score}
        
        r16_matches.append({"match_id": match_id, "match_number": match_number, "home_team": home_team, "away_team": away_team, "prediction": prediction, "locked": False})
        match_number += 1
    
    return r16_matches


def build_quarter_finals(
    db: Session,
    user_id: int,
    bracket: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build Quarter Finals from R16 winners."""
    qf_matches = []
    r16_winners = []
    
    for r16_match in bracket["round_of_16"]:
        if r16_match["prediction"] and r16_match["prediction"]["predicted_winner_team_id"]:
            winner_id = r16_match["prediction"]["predicted_winner_team_id"]
            if r16_match["home_team"] and r16_match["home_team"]["team_id"] == winner_id:
                winner_team = r16_match["home_team"]
            elif r16_match["away_team"] and r16_match["away_team"]["team_id"] == winner_id:
                winner_team = r16_match["away_team"]
            else:
                continue
            r16_winners.append(winner_team)
    
    match_number = 89
    for i in range(0, len(r16_winners), 2):
        home_team = r16_winners[i] if i < len(r16_winners) else None
        away_team = r16_winners[i + 1] if i + 1 < len(r16_winners) else None
        
        match_obj = db.exec(select(Match).where(Match.match_number == match_number)).first()
        match_id = match_obj.id if match_obj else None
        
        prediction = None
        if match_id:
            pred = db.exec(select(Prediction).where(Prediction.user_id == user_id, Prediction.match_id == match_id)).first()
            if pred:
                prediction = {"id": pred.id, "predicted_outcome": pred.predicted_outcome, "predicted_winner_team_id": pred.predicted_winner_team_id, "predicted_home_score": pred.predicted_home_score, "predicted_away_score": pred.predicted_away_score}
        
        qf_matches.append({"match_id": match_id, "match_number": match_number, "home_team": home_team, "away_team": away_team, "prediction": prediction, "locked": False})
        match_number += 1
    
    return qf_matches


def build_semi_finals(
    db: Session,
    user_id: int,
    bracket: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build Semi Finals from QF winners."""
    sf_matches = []
    qf_winners = []
    
    for qf_match in bracket["quarter_finals"]:
        if qf_match["prediction"] and qf_match["prediction"]["predicted_winner_team_id"]:
            winner_id = qf_match["prediction"]["predicted_winner_team_id"]
            if qf_match["home_team"] and qf_match["home_team"]["team_id"] == winner_id:
                winner_team = qf_match["home_team"]
            elif qf_match["away_team"] and qf_match["away_team"]["team_id"] == winner_id:
                winner_team = qf_match["away_team"]
            else:
                continue
            qf_winners.append(winner_team)
    
    match_number = 93
    for i in range(0, len(qf_winners), 2):
        home_team = qf_winners[i] if i < len(qf_winners) else None
        away_team = qf_winners[i + 1] if i + 1 < len(qf_winners) else None
        
        match_obj = db.exec(select(Match).where(Match.match_number == match_number)).first()
        match_id = match_obj.id if match_obj else None
        
        prediction = None
        if match_id:
            pred = db.exec(select(Prediction).where(Prediction.user_id == user_id, Prediction.match_id == match_id)).first()
            if pred:
                prediction = {"id": pred.id, "predicted_outcome": pred.predicted_outcome, "predicted_winner_team_id": pred.predicted_winner_team_id, "predicted_home_score": pred.predicted_home_score, "predicted_away_score": pred.predicted_away_score}
        
        sf_matches.append({"match_id": match_id, "match_number": match_number, "home_team": home_team, "away_team": away_team, "prediction": prediction, "locked": False})
        match_number += 1
    
    return sf_matches


def build_third_place_match(
    db: Session,
    user_id: int,
    bracket: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Build Third Place match from SF losers."""
    sf_matches = bracket.get("semi_finals", [])
    if len(sf_matches) < 2:
        return None
    
    sf_losers = []
    for sf_match in sf_matches:
        if sf_match["prediction"] and sf_match["prediction"]["predicted_winner_team_id"]:
            winner_id = sf_match["prediction"]["predicted_winner_team_id"]
            if sf_match["home_team"] and sf_match["home_team"]["team_id"] != winner_id:
                sf_losers.append(sf_match["home_team"])
            elif sf_match["away_team"] and sf_match["away_team"]["team_id"] != winner_id:
                sf_losers.append(sf_match["away_team"])
    
    if len(sf_losers) < 2:
        return None
    
    match_obj = db.exec(select(Match).where(Match.match_number == 95)).first()
    match_id = match_obj.id if match_obj else None
    
    prediction = None
    if match_id:
        pred = db.exec(select(Prediction).where(Prediction.user_id == user_id, Prediction.match_id == match_id)).first()
        if pred:
            prediction = {"id": pred.id, "predicted_outcome": pred.predicted_outcome, "predicted_winner_team_id": pred.predicted_winner_team_id, "predicted_home_score": pred.predicted_home_score, "predicted_away_score": pred.predicted_away_score}
    
    return {"match_id": match_id, "match_number": 95, "home_team": sf_losers[0], "away_team": sf_losers[1], "prediction": prediction, "locked": False}


def build_final(
    db: Session,
    user_id: int,
    bracket: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Build Final from SF winners."""
    sf_matches = bracket.get("semi_finals", [])
    if len(sf_matches) < 2:
        return None
    
    sf_winners = []
    for sf_match in sf_matches:
        if sf_match["prediction"] and sf_match["prediction"]["predicted_winner_team_id"]:
            winner_id = sf_match["prediction"]["predicted_winner_team_id"]
            if sf_match["home_team"] and sf_match["home_team"]["team_id"] == winner_id:
                sf_winners.append(sf_match["home_team"])
            elif sf_match["away_team"] and sf_match["away_team"]["team_id"] == winner_id:
                sf_winners.append(sf_match["away_team"])
    
    if len(sf_winners) < 2:
        return None
    
    match_obj = db.exec(select(Match).where(Match.match_number == 96)).first()
    match_id = match_obj.id if match_obj else None
    
    prediction = None
    if match_id:
        pred = db.exec(select(Prediction).where(Prediction.user_id == user_id, Prediction.match_id == match_id)).first()
        if pred:
            prediction = {"id": pred.id, "predicted_outcome": pred.predicted_outcome, "predicted_winner_team_id": pred.predicted_winner_team_id, "predicted_home_score": pred.predicted_home_score, "predicted_away_score": pred.predicted_away_score}
    
    return {"match_id": match_id, "match_number": 96, "home_team": sf_winners[0], "away_team": sf_winners[1], "prediction": prediction, "locked": False}
