"""Fix group sizes by merging extra teams into the target teams defined in CSV."""
import sys
import csv
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.fifa_team import FifaTeam
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.third_place_ranking import UserThirdPlaceRanking

CORE_FILES_DIR = Path(__file__).parent.parent / "app" / "core_files"
TEAMS_CSV = CORE_FILES_DIR / "teams.csv"

def fix_groups():
    if not TEAMS_CSV.exists():
        print("teams.csv not found")
        return

    # 1. Load desired state from CSV
    desired_teams_by_group = defaultdict(set)
    with open(TEAMS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['group_letter']:
                desired_teams_by_group[row['group_letter']].add(row['name'])

    with Session(engine) as session:
        # 2. Iterate through groups
        for group_letter, desired_names in desired_teams_by_group.items():
            # Get current DB teams for this group
            db_teams = session.exec(
                select(FifaTeam).where(FifaTeam.group_letter == group_letter)
            ).all()
            
            db_team_names = {t.name for t in db_teams}
            
            # Identify sets
            # Intersection: Teams that are correct and exist
            # Extra: Teams in DB but not in CSV (To be deleted/merged)
            # Missing: Teams in CSV but not in DB (Should have been created by update_data.py)
            
            extra_teams = [t for t in db_teams if t.name not in desired_names]
            valid_teams = [t for t in db_teams if t.name in desired_names]
            
            # We specifically look for the case where we have valid teams that were "just added" 
            # and extra teams that are "placeholders" to be removed.
            
            # Simple heuristic:
            # If we have Extra teams, we need to move their matches to the Valid teams that "replaced" them.
            # Which Valid team? The one that isn't taking matches from another existing team.
            # But practically, "TBD A4" matches should go to "Panama".
            # "Panama" is in `valid_teams`. "TBD A4" is in `extra_teams`.
            
            if not extra_teams:
                print(f"Group {group_letter} is clean ({len(db_teams)} teams).")
                continue

            print(f"Group {group_letter} has {len(extra_teams)} extra teams: {[t.name for t in extra_teams]}")
            
            # Find the "New" valid teams (those that might need matches)
            # A "New" valid team is one that likely doesn't have matches yet? 
            # Or we can just map 1-to-1 if counts match.
            
            # In Group A: Extra=[TBD A4], Valid=[USA, MEX, CAN, PAN]
            # Likely TBD A4 matches -> PAN.
            # How to confirm? USA, MEX, CAN likely already have their matches correct (linked to them).
            # PAN likely has 0 matches (except those from matches.csv).
            # TBD A4 has matches.
            
            # Let's find valid teams with 0 matches (or few) and Extra teams with matches.
            
            for extra in extra_teams:
                # Count matches for extra team
                extra_matches_count = session.query(Match).filter(
                    (Match.home_team_id == extra.id) | (Match.away_team_id == extra.id)
                ).count()
                
                if extra_matches_count == 0:
                    print(f"  Deleting unused extra team: {extra.name}")
                    session.delete(extra)
                    continue
                
                # It has matches. We need to move them to a valid team.
                # Find a valid team that needs matches?
                # Or just find the valid team that is NOT in the original seed list?
                # Hard to know original seed list here.
                
                # Heuristic: Find a valid team in this group that has FEWEST matches.
                # (Ideally 0, or just the ones from matches.csv).
                candidate = None
                min_matches = 9999
                
                for valid in valid_teams:
                    # Skip if this valid team name looks like a TBD (unlikely to be the replacement target for another TBD, unless we renamed)
                    # Actually, if we replaced TBD A4 with Panama, Panama is the target.
                    
                    count = session.query(Match).filter(
                        (Match.home_team_id == valid.id) | (Match.away_team_id == valid.id)
                    ).count()
                    
                    if count < min_matches:
                        min_matches = count
                        candidate = valid
                
                if candidate:
                    print(f"  Merging {extra.name} ({extra_matches_count} matches) -> {candidate.name} ({min_matches} matches)")
                    
                    # Move Home Matches
                    session.exec(select(Match).where(Match.home_team_id == extra.id)).all()
                    # SQLModel update not straightforward with exec, iterating
                    matches_home = session.exec(select(Match).where(Match.home_team_id == extra.id)).all()
                    for m in matches_home:
                        m.home_team_id = candidate.id
                        session.add(m)
                        
                    # Move Away Matches
                    matches_away = session.exec(select(Match).where(Match.away_team_id == extra.id)).all()
                    for m in matches_away:
                        m.away_team_id = candidate.id
                        session.add(m)
                        
                    # Predictions?
                    # If users predicted TBD A4, move to Panama.
                    # Warning: If user also predicted Panama (unlikely if they couldn't see it), might duplicate.
                    # Assuming unique match_id per user... wait, prediction is linked to match_id.
                    # We updated the MATCH. So the prediction is now linked to a match that has Panama.
                    # BUT, Prediction table has `predicted_winner_team_id`. We need to update that too!
                    
                    preds = session.exec(select(Prediction).where(Prediction.predicted_winner_team_id == extra.id)).all()
                    for p in preds:
                        p.predicted_winner_team_id = candidate.id
                        session.add(p)
                        
                    # Third Place Rankings?
                    rankings = session.exec(select(UserThirdPlaceRanking).where(UserThirdPlaceRanking.team_id == extra.id)).all()
                    for r in rankings:
                        r.team_id = candidate.id
                        session.add(r)
                        
                    # Now delete extra
                    session.delete(extra)
                else:
                    print(f"  Could not find candidate for {extra.name}")

        session.commit()
        print("Groups fixed.")

if __name__ == "__main__":
    fix_groups()
