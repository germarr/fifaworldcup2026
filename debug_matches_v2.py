from sqlmodel import Session, select, create_engine
from app.models import Match, Team

# Create database engine
engine = create_engine("sqlite:///worldcup.db")

def debug_matches():
    with Session(engine) as session:
        # Get all finished knockout matches
        statement = select(Match).where(
            Match.is_finished == True, 
            ~Match.round.like("Group Stage%")
        ).order_by(Match.match_number)
        matches = session.exec(statement).all()
        
        print(f"Found {len(matches)} finished knockout matches:")
        match_map = {m.id: m for m in matches}
        
        for match in matches:
            team1 = session.get(Team, match.team1_id) if match.team1_id else None
            team2 = session.get(Team, match.team2_id) if match.team2_id else None
            t1_name = team1.name if team1 else "TBD"
            t2_name = team2.name if team2 else "TBD"
            
            winner = "Unknown"
            if match.actual_team1_score > match.actual_team2_score:
                winner = t1_name
            elif match.actual_team2_score > match.actual_team1_score:
                winner = t2_name
            elif match.penalty_winner_id:
                w_team = session.get(Team, match.penalty_winner_id)
                winner = f"{w_team.name} (Pens)"
            
            print(f"Match {match.match_number} ({match.round}): {t1_name} {match.actual_team1_score}-{match.actual_team2_score} {t2_name}")
            if match.actual_team1_penalty_score is not None:
                 print(f"  Penalties: {match.actual_team1_penalty_score}-{match.actual_team2_penalty_score}")
            print(f"  Winner: {winner}")
            print("-" * 20)

if __name__ == "__main__":
    debug_matches()
