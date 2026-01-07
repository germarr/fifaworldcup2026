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
                if ph.startswith('W'):
                    # Winner
                    if prev_match.actual_team1_score > prev_match.actual_team2_score:
                        match.team1_id = prev_match.team1_id
                    else:
                        match.team1_id = prev_match.team2_id
                else:
                    # Loser (Third Place)
                    if prev_match.actual_team1_score > prev_match.actual_team2_score:
                        match.team1_id = prev_match.team2_id
                    else:
                        match.team1_id = prev_match.team1_id
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
                if ph.startswith('W'):
                    if prev_match.actual_team1_score > prev_match.actual_team2_score:
                        match.team2_id = prev_match.team1_id
                    else:
                        match.team2_id = prev_match.team2_id
                else:
                    if prev_match.actual_team1_score > prev_match.actual_team2_score:
                        match.team2_id = prev_match.team2_id
                    else:
                        match.team2_id = prev_match.team1_id
                changed = True
                
    return changed

def simulate_full_tournament():
    with Session(engine) as session:
        print("--- RESETTING TOURNAMENT ---")
        # Reset all matches
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
                    # 2. Simulate Result (Knockout cannot be a draw)
                    score1 = 0
                    score2 = 0
                    while score1 == score2:
                        score1 = random.randint(0, 3)
                        score2 = random.randint(0, 3)
                    
                    m.actual_team1_score = score1
                    m.actual_team2_score = score2
                    m.is_finished = True
                    session.add(m)
                    
                    t1 = session.get(Team, m.team1_id).name
                    t2 = session.get(Team, m.team2_id).name
                    print(f"Match {m.match_number}: {t1} {score1} - {score2} {t2}")
                
            session.commit() # Commit after each round so next round can see winners

        # Update user scores based on full tournament results
        update_user_scores(session)

if __name__ == "__main__":
    simulate_full_tournament()
