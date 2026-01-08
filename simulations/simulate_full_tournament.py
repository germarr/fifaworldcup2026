import random
from sqlmodel import Session, select
from app.database import engine
from app.models import Match, Team, GroupStanding, User, Prediction
from app.scoring import calculate_match_points

def update_user_scores(session):
    """Recalculate and update total_points for all users based on current match results."""
    print("Updating user scores...")
    users = session.exec(select(User)).all()
    matches = session.exec(select(Match)).all()
    match_map = {m.id: m for m in matches}
    
    for user in users:
        total_points = 0
        predictions = session.exec(select(Prediction).where(Prediction.user_id == user.id)).all()
        
        for pred in predictions:
            match = match_map.get(pred.match_id)
            if match and match.is_finished:
                # Calculate points for this prediction
                result = calculate_match_points(pred, match)
                total_points += result["points"]
        
        user.total_points = total_points
        session.add(user)
    
    session.commit()
    print(f"Updated scores for {len(users)} users.")

def update_official_standings(session):
    """Calculate and save official standings to the GroupStanding table."""
    # Clear existing standings
    session.exec(select(GroupStanding)).all()
    for s in session.exec(select(GroupStanding)).all():
        session.delete(s)
    session.commit()

    # Calculate fresh stats
    statement = select(Match).where(Match.round.like("Group Stage%"), Match.is_finished == True)
    matches = session.exec(statement).all()
    
    teams = session.exec(select(Team)).all()
    stats = {t.id: {
        'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 
        'gf': 0, 'ga': 0, 'points': 0, 'group': t.group
    } for t in teams if t.group}

    for m in matches:
        t1, t2 = stats[m.team1_id], stats[m.team2_id]
        t1['played'] += 1; t2['played'] += 1
        t1['gf'] += m.actual_team1_score; t1['ga'] += m.actual_team2_score
        t2['gf'] += m.actual_team2_score; t2['ga'] += m.actual_team1_score
        
        if m.actual_team1_score > m.actual_team2_score:
            t1['won'] += 1; t1['points'] += 3; t2['lost'] += 1
        elif m.actual_team2_score > m.actual_team1_score:
            t2['won'] += 1; t2['points'] += 3; t1['lost'] += 1
        else:
            t1['drawn'] += 1; t1['points'] += 1; t2['drawn'] += 1; t2['points'] += 1

    # Save to DB
    for team_id, s in stats.items():
        standing = GroupStanding(
            team_id=team_id,
            group_letter=s['group'],
            played=s['played'],
            won=s['won'],
            drawn=s['drawn'],
            lost=s['lost'],
            goals_for=s['gf'],
            goals_against=s['ga'],
            goal_difference=s['gf'] - s['ga'],
            points=s['points']
        )
        session.add(standing)
    session.commit()

def get_actual_standings(session):
    """Calculate standings based on ACTUAL match results."""
    # Get all finished group matches
    statement = select(Match).where(
        Match.round.like("Group Stage%"),
        Match.is_finished == True
    )
    matches = session.exec(statement).all()
    
    # Init stats
    # Structure: {'A': {team_id: {'points': 0, 'gd': 0, 'gf': 0, 'team': obj}}}
    groups = {k: {} for k in "ABCDEFGH"}
    
    # Load all teams to ensure everyone is present
    teams = session.exec(select(Team)).all()
    for team in teams:
        if team.group:
            groups[team.group][team.id] = {
                'points': 0, 'gd': 0, 'gf': 0, 'team': team, 'played': 0
            }

    for m in matches:
        group = m.round.split()[-1] # "Group A" -> "A"
        if group not in groups: continue
        
        t1 = groups[group][m.team1_id]
        t2 = groups[group][m.team2_id]
        
        t1['played'] += 1
        t2['played'] += 1
        
        # Goals
        t1['gf'] += m.actual_team1_score
        t1['gd'] += (m.actual_team1_score - m.actual_team2_score)
        t2['gf'] += m.actual_team2_score
        t2['gd'] += (m.actual_team2_score - m.actual_team1_score)
        
        # Points
        if m.actual_team1_score > m.actual_team2_score:
            t1['points'] += 3
        elif m.actual_team2_score > m.actual_team1_score:
            t2['points'] += 3
        else:
            t1['points'] += 1
            t2['points'] += 1

    # Sort and create mapping key -> team_id (e.g., '1A': 4, '2A': 8)
    placeholder_map = {}
    
    for group, teams_dict in groups.items():
        # Sort: Points DESC, GD DESC, GF DESC
        sorted_teams = sorted(
            teams_dict.values(),
            key=lambda x: (x['points'], x['gd'], x['gf']),
            reverse=True
        )
        
        if len(sorted_teams) >= 1:
            placeholder_map[f"1{group}"] = sorted_teams[0]['team'].id
        if len(sorted_teams) >= 2:
            placeholder_map[f"2{group}"] = sorted_teams[1]['team'].id
            
    return placeholder_map

def resolve_knockout_match(session, match, placeholder_map):
    """Resolve TBD teams in a knockout match."""
    changed = False
    
    # Resolve Team 1
    if not match.team1_id and match.team1_placeholder:
        ph = match.team1_placeholder
        if ph in placeholder_map:
            match.team1_id = placeholder_map[ph]
            changed = True
        elif ph.startswith('W') or ph.startswith('L'):
            # W49 or L61 -> Look up previous match result
            prev_match_num = int(ph[1:])
            prev_match = session.exec(select(Match).where(Match.match_number == prev_match_num)).first()
            
            if prev_match and prev_match.is_finished:
                # Determine winner of previous match
                winner_id = None
                loser_id = None
                
                if prev_match.actual_team1_score > prev_match.actual_team2_score:
                    winner_id = prev_match.team1_id
                    loser_id = prev_match.team2_id
                elif prev_match.actual_team2_score > prev_match.actual_team1_score:
                    winner_id = prev_match.team2_id
                    loser_id = prev_match.team1_id
                elif prev_match.penalty_winner_id:
                    winner_id = prev_match.penalty_winner_id
                    loser_id = prev_match.team2_id if winner_id == prev_match.team1_id else prev_match.team1_id
                
                if winner_id:
                    if ph.startswith('W'):
                        match.team1_id = winner_id
                    else:
                        match.team1_id = loser_id
                    changed = True

    # Resolve Team 2 (Same logic)
    if not match.team2_id and match.team2_placeholder:
        ph = match.team2_placeholder
        if ph in placeholder_map:
            match.team2_id = placeholder_map[ph]
            changed = True
        elif ph.startswith('W') or ph.startswith('L'):
            prev_match_num = int(ph[1:])
            prev_match = session.exec(select(Match).where(Match.match_number == prev_match_num)).first()
            
            if prev_match and prev_match.is_finished:
                # Determine winner of previous match
                winner_id = None
                loser_id = None
                
                if prev_match.actual_team1_score > prev_match.actual_team2_score:
                    winner_id = prev_match.team1_id
                    loser_id = prev_match.team2_id
                elif prev_match.actual_team2_score > prev_match.actual_team1_score:
                    winner_id = prev_match.team2_id
                    loser_id = prev_match.team1_id
                elif prev_match.penalty_winner_id:
                    winner_id = prev_match.penalty_winner_id
                    loser_id = prev_match.team2_id if winner_id == prev_match.team1_id else prev_match.team1_id
                
                if winner_id:
                    if ph.startswith('W'):
                        match.team2_id = winner_id
                    else:
                        match.team2_id = loser_id
                    changed = True
                
    return changed

def simulate_full_tournament(user_id: int = None, db = None):
    """
    Simulate full tournament and optionally create predictions for a user.
    
    Args:
        user_id: If provided, create predictions for this user with simulated scores
        db: Database session (required if user_id is provided)
    """
    # If no db provided, use default engine with context manager
    if db is None:
        session = Session(engine)
        should_close = True
    else:
        session = db
        should_close = False
    
    try:
        print("--- RESETTING TOURNAMENT ---")
        all_matches = session.exec(select(Match)).all()
        for m in all_matches:
            m.actual_team1_score = None
            m.actual_team2_score = None
            m.is_finished = False
            
            # Reset knockout team resolution (keep placeholders)
            if not m.round.startswith("Group Stage"):
                m.team1_id = None
                m.team2_id = None
        
        session.commit()
        print("All matches reset.")

        print("--- PHASE 1: Group Stage ---")
        # Ensure Group Stage is done (using previously simulated data or filling gaps)
        group_matches = session.exec(select(Match).where(Match.round.like("Group Stage%"))).all()
        for m in group_matches:
            if not m.is_finished:
                m.actual_team1_score = random.randint(0, 3)
                m.actual_team2_score = random.randint(0, 3)
                m.is_finished = True
                session.add(m)
        session.commit()
        print("Group stage matches verified/completed.")

        # Update the GroupStanding table for the UI dashboard
        update_official_standings(session)
        print("Official standings table updated.")

        # Calculate Standings & Map Placeholders
        placeholder_map = get_actual_standings(session)
        print(f"Standings calculated. Mapped {len(placeholder_map)} qualifiers.")

        # Rounds in order
        rounds = ["Round of 16", "Quarter Finals", "Semi Finals", "Third Place", "Final"]
        
        for r in rounds:
            print(f"--- PHASE: {r} ---")
            matches = session.exec(select(Match).where(Match.round == r)).all()
            
            for m in matches:
                # 1. Resolve Participants
                resolve_knockout_match(session, m, placeholder_map)
                
                # Check if we have teams now
                if m.team1_id and m.team2_id and not m.is_finished:
                    # 2. Simulate Result
                    # Allow draws (which lead to penalties)
                    score1 = random.randint(0, 3)
                    score2 = random.randint(0, 3)
                    
                    m.actual_team1_score = score1
                    m.actual_team2_score = score2
                    
                    t1 = session.get(Team, m.team1_id).name
                    t2 = session.get(Team, m.team2_id).name
                    
                    if score1 == score2:
                        # Simulate Penalties
                        pen_score1 = 0
                        pen_score2 = 0
                        while pen_score1 == pen_score2:
                            pen_score1 = random.randint(1, 5)
                            pen_score2 = random.randint(1, 5)
                        
                        m.actual_team1_penalty_score = pen_score1
                        m.actual_team2_penalty_score = pen_score2
                        
                        if pen_score1 > pen_score2:
                            m.penalty_winner_id = m.team1_id
                            winner_name = t1
                        else:
                            m.penalty_winner_id = m.team2_id
                            winner_name = t2
                            
                        print(f"Match {m.match_number}: {t1} {score1} - {score2} {t2} (Penalties: {pen_score1}-{pen_score2}, Winner: {winner_name})")
                    else:
                        print(f"Match {m.match_number}: {t1} {score1} - {score2} {t2}")
                        
                    m.is_finished = True
                    session.add(m)
                
            session.commit() # Commit after each round so next round can see winners

        # Update user scores based on full tournament results
        update_user_scores(session)
    
    finally:
        if should_close:
            session.close()


def create_user_predictions_from_simulation(user_id: int, session: Session):
    """
    Create random predictions for a user to auto-populate their bracket.
    
    This is called when user clicks "Pick the entire Tournament" to instantly
    fill in all match predictions with random values. This allows:
    1. Users to have a complete bracket immediately
    2. Predictions to potentially differ from actual results (for scoring)
    3. Users can still edit predictions manually before committing
    """
    from app.models import Prediction
    
    # Get all matches
    matches = session.exec(select(Match)).all()
    
    # Delete any existing predictions for this user (clean slate)
    existing = session.exec(select(Prediction).where(Prediction.user_id == user_id)).all()
    for pred in existing:
        session.delete(pred)
    session.commit()
    
    # Create new RANDOM predictions for each match
    # These are independent of actual_* scores (which may not exist yet)
    for match in matches:
        # Generate random scores (0-3 for realistic match results)
        score1 = random.randint(0, 3)
        score2 = random.randint(0, 3)
        
        prediction = Prediction(
            user_id=user_id,
            match_id=match.id,
            predicted_team1_score=score1,
            predicted_team2_score=score2,
            # Handle penalty shootout for tied knockout matches
            penalty_shootout_winner_id=None  # User would need to set this manually if tied
        )
        session.add(prediction)
    
    session.commit()
    print(f"Created {len(matches)} random predictions for user {user_id}")
