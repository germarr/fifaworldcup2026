
from sqlmodel import Session, select, create_engine
from app.models import Match, Team, Prediction
from app.knockout import resolve_match_teams

engine = create_engine("sqlite:///worldcup.db")

def debug():
    with Session(engine) as session:
        user_id = 1 # Assuming user 1
        
        # Get Match 64
        match = session.exec(select(Match).where(Match.match_number == 64)).first()
        print(f"Match 64: {match.match_number} {match.round}")
        print(f"Actual IDs: {match.team1_id} vs {match.team2_id}")
        print(f"Scores: {match.actual_team1_score}-{match.actual_team2_score}")
        print(f"Finished: {match.is_finished}")
        
        # Calculate Actual Winner ID
        actual_winner_id = None
        if match.is_finished:
            if match.actual_team1_score > match.actual_team2_score:
                actual_winner_id = match.team1_id
            elif match.actual_team2_score > match.actual_team1_score:
                actual_winner_id = match.team2_id
            elif match.penalty_winner_id:
                actual_winner_id = match.penalty_winner_id
        
        print(f"Calculated Actual Winner ID: {actual_winner_id}")
        
        # Resolve Teams for User
        team1, team2 = resolve_match_teams(match, user_id, session)
        
        t1_name = team1.name if team1 else "None"
        t1_id = team1.id if team1 else "None"
        t2_name = team2.name if team2 else "None"
        t2_id = team2.id if team2 else "None"
        
        print(f"Resolved User Team 1: {t1_name} (ID: {t1_id})")
        print(f"Resolved User Team 2: {t2_name} (ID: {t2_id})")
        
        # Calculate Flags
        is_t1 = (team1 and actual_winner_id and team1.id == actual_winner_id)
        is_t2 = (team2 and actual_winner_id and team2.id == actual_winner_id)
        
        print(f"team1_is_actual_winner: {is_t1}")
        print(f"team2_is_actual_winner: {is_t2}")

if __name__ == "__main__":
    debug()
