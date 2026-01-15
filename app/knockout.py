"""
Knockout team resolution based on group standings and match predictions.
"""

from typing import Dict, Optional, List, Tuple
from sqlmodel import Session, select
from app.models import Match, Prediction, Team
from app.standings import calculate_group_standings, TeamStanding


def resolve_knockout_teams(user_id: int, db: Session) -> Dict[str, Optional[Team]]:
    """
    Resolve team placeholders for knockout matches.

    Args:
        user_id: User ID to resolve teams for
        db: Database session

    Returns:
        Dictionary mapping placeholder codes to Team objects
        Example: {'1A': Team(Brazil), '2B': Team(Senegal), 'W49': Team(Netherlands), '3A': Team(Poland)}
    """
    resolution: Dict[str, Optional[Team]] = {}

    # Calculate standings once and reuse
    standings = calculate_group_standings(user_id, db)

    # 1. Resolve group winners and runners-up
    for group, group_standings in standings.items():
        winner = group_standings[0].team if len(group_standings) > 0 else None
        runner_up = group_standings[1].team if len(group_standings) > 1 else None

        resolution[f"1{group}"] = winner
        resolution[f"2{group}"] = runner_up
        
        # Also map 3rd place for each group specifically (e.g., "3A")
        # This is useful if a placeholder explicitly asks for "3A"
        third = group_standings[2].team if len(group_standings) > 2 else None
        resolution[f"3{group}"] = third

    # 2. Resolve 3rd place allocation (Constraint Satisfaction)
    # Get all 3rd place teams
    third_place_candidates = []
    for group, group_standings in standings.items():
        if len(group_standings) > 2:
            third_place_candidates.append({
                "team": group_standings[2].team,
                "group": group,
                "standing": group_standings[2]
            })

    # Rank them: Points DESC, GD DESC, GF DESC
    # (Fair play and lots not supported in predictions, fallback to name/stable sort)
    ranked_thirds = sorted(
        third_place_candidates,
        key=lambda x: (
            x["standing"].points,
            x["standing"].goal_difference,
            x["standing"].goals_for,
            x["team"].name
        ),
        reverse=True
    )

    # Take top 8
    qualified_thirds = ranked_thirds[:8]

    # Get all knockout matches to find multi-group placeholders
    knockout_matches_statement = select(Match).where(
        ~Match.round.like("Group Stage%")
    ).order_by(Match.match_number)
    
    knockout_matches = db.exec(knockout_matches_statement).all()
    
    # Identify placeholders like "3ABCDF"
    multi_group_placeholders = []
    for match in knockout_matches:
        for ph in [match.team1_placeholder, match.team2_placeholder]:
            if ph and ph.startswith("3") and len(ph) > 2:
                # e.g., "3ABCDF" -> allowed groups {A, B, C, D, F}
                allowed_groups = set(ph[1:])
                multi_group_placeholders.append((ph, allowed_groups))
    
    # Solve assignment
    if multi_group_placeholders and qualified_thirds:
        assignment = _solve_third_place_assignment(multi_group_placeholders, qualified_thirds)
        for ph, team_data in assignment.items():
            resolution[ph] = team_data["team"]


    # 3. Resolve match winners (for quarters, semis, etc.)
    # Get user predictions for knockout matches
    knockout_match_ids = [m.id for m in knockout_matches]
    predictions_statement = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.match_id.in_(knockout_match_ids)
    )
    predictions = db.exec(predictions_statement).all()

    predictions_map = {p.match_id: p for p in predictions}

    # Get all teams once to avoid repeated queries
    teams_statement = select(Team)
    teams_map = {t.id: t for t in db.exec(teams_statement).all()}

    # Resolve match winners and losers based on predictions AND actual results
    for match in knockout_matches:
        prediction = predictions_map.get(match.id)
        
        # First, resolve the teams in this match
        team1, team2 = resolve_match_teams_with_cache(match, resolution, teams_map)

        # Determine winner and loser
        winner_team = None
        loser_team = None

        # A. Check ACTUAL result first (Visual consistency with finished matches)
        match_finished = match.is_finished or (
            match.actual_team1_score is not None and match.actual_team2_score is not None
        )
        if match_finished:
            if match.actual_team1_score > match.actual_team2_score:
                winner_team = team1
                loser_team = team2
            elif match.actual_team2_score > match.actual_team1_score:
                winner_team = team2
                loser_team = team1
            elif match.actual_team1_score == match.actual_team2_score and match.penalty_winner_id:
                if team1 and match.penalty_winner_id == team1.id:
                    winner_team = team1
                    loser_team = team2
                elif team2 and match.penalty_winner_id == team2.id:
                    winner_team = team2
                    loser_team = team1
        
        # B. Check PREDICTION (User's Fantasy Path)
        # If match is NOT finished (or we want to show prediction path), use prediction
        # Ideally, we follow prediction path until it diverges from reality?
        # The prompt implies "/bracket" is for predictions.
        # But if a match is finished, the next round should probably use the actual winner?
        # Actually, bracket predictions usually lock. If I predict Brazil to win, but they lose,
        # my next round prediction is invalid (or "failed").
        # However, for the UI "My Bracket", we usually show the user's predicted path.
        
        # Let's keep existing logic: Prediction overrides "Actual" for the purpose of the resolution map
        # unless prediction is missing.
        # WAIT: The previous logic had: "Check ACTUAL result first... Check PREDICTION first".
        # It was overwriting actual with prediction if prediction existed.
        # That is correct for a "Prediction Bracket View".
        
        if prediction:
            # Check explicit winner ID first (handles swapped teams)
            winner_found = False
            if prediction.predicted_winner_id:
                if team1 and prediction.predicted_winner_id == team1.id:
                    winner_team = team1
                    loser_team = team2
                    winner_found = True
                elif team2 and prediction.predicted_winner_id == team2.id:
                    winner_team = team2
                    loser_team = team1
                    winner_found = True
            
            if not winner_found:
                if prediction.predicted_team1_score > prediction.predicted_team2_score:
                    winner_team = team1
                    loser_team = team2
                elif prediction.predicted_team2_score > prediction.predicted_team1_score:
                    winner_team = team2
                    loser_team = team1
                else:
                    # Tie
                    if prediction.penalty_shootout_winner_id:
                        if team1 and prediction.penalty_shootout_winner_id == team1.id:
                            winner_team = team1
                            loser_team = team2
                        elif team2 and prediction.penalty_shootout_winner_id == team2.id:
                            winner_team = team2
                            loser_team = team1
                        else:
                            penalty_winner = teams_map.get(prediction.penalty_shootout_winner_id)
                            if penalty_winner:
                                winner_team = penalty_winner
                                loser_team = team2 if winner_team == team1 else team1
                            else:
                                winner_team = team1
                                loser_team = team2

                    if not winner_team:
                        winner_team = team1
                        loser_team = team2

        resolution[f"W{match.match_number}"] = winner_team
        resolution[f"L{match.match_number}"] = loser_team

    return resolution


def _solve_third_place_assignment(
    placeholders: List[Tuple[str, set]],
    qualified_teams: List[Dict]
) -> Dict[str, Dict]:
    """
    Solve constraint satisfaction for assigning 3rd place teams to placeholders.
    Reused from quickgame logic.
    """
    # Sort placeholders by constraint tightness (fewest options first)
    def count_available(placeholder_allowed_groups):
        return sum(1 for team in qualified_teams if team["group"] in placeholder_allowed_groups)

    placeholders_sorted = sorted(placeholders, key=lambda p: count_available(p[1]))

    def backtrack(index: int, assignment: Dict[str, Dict], used_ids: set) -> Optional[Dict]:
        if index == len(placeholders_sorted):
            return assignment

        placeholder, allowed_groups = placeholders_sorted[index]

        for team_item in qualified_teams:
            if team_item["team"].id in used_ids:
                continue
            if team_item["group"] not in allowed_groups:
                continue

            assignment[placeholder] = team_item
            used_ids.add(team_item["team"].id)

            result = backtrack(index + 1, assignment, used_ids)
            if result is not None:
                return result

            del assignment[placeholder]
            used_ids.remove(team_item["team"].id)

        return None

    result = backtrack(0, {}, set())
    return result if result is not None else {}


def resolve_match_teams_with_cache(match: Match, resolution: Dict[str, Optional[Team]], teams_map: Dict[int, Team]) -> tuple[Optional[Team], Optional[Team]]:
    """
    Resolve the actual teams for a match using cached data.
    """
    # If match has direct team IDs (group stage), use those
    if match.team1_id and match.team2_id and not match.team1_placeholder and not match.team2_placeholder:
        team1 = teams_map.get(match.team1_id)
        team2 = teams_map.get(match.team2_id)
        return team1, team2

    team1 = None
    team2 = None

    if match.team1_placeholder:
        team1 = resolution.get(match.team1_placeholder)
    elif match.team1_id:
        team1 = teams_map.get(match.team1_id)

    if match.team2_placeholder:
        team2 = resolution.get(match.team2_placeholder)
    elif match.team2_id:
        team2 = teams_map.get(match.team2_id)

    return team1, team2


def resolve_match_teams(match: Match, user_id: int, db: Session) -> tuple[Optional[Team], Optional[Team]]:
    """
    Public wrapper to resolve a single match (less efficient than batch).
    """
    if match.team1_id and match.team2_id and not match.team1_placeholder and not match.team2_placeholder:
        teams_statement = select(Team).where(Team.id.in_([match.team1_id, match.team2_id]))
        teams = {t.id: t for t in db.exec(teams_statement).all()}
        return teams.get(match.team1_id), teams.get(match.team2_id)

    resolution = resolve_knockout_teams(user_id, db)

    team1 = resolution.get(match.team1_placeholder) if match.team1_placeholder else None
    team2 = resolution.get(match.team2_placeholder) if match.team2_placeholder else None

    # Fallbacks
    if not team1 and match.team1_id:
        team1 = db.get(Team, match.team1_id)
    if not team2 and match.team2_id:
        team2 = db.get(Team, match.team2_id)

    return team1, team2