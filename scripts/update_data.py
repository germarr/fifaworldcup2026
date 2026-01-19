"""Update teams, stadiums, and matches from CSV files."""
import sys
import csv
import os
from pathlib import Path
from datetime import datetime, UTC
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.fifa_team import FifaTeam
from app.models.match import Match
from app.models.stadium import Stadium
import pandas as pd

data_ = pd.read_csv('./app/core_files/matches.csv', index_col=0)
data_['scheduled_datetime'] = pd.to_datetime(data_['scheduled_datetime'], format='mixed')
data_.to_csv("./app/core_files/matches.csv")

CORE_FILES_DIR = Path(__file__).parent.parent / "app" / "core_files"
TEAMS_CSV = CORE_FILES_DIR / "teams.csv"
STADIUMS_CSV = CORE_FILES_DIR / "stadiums.csv"
MATCHES_CSV = CORE_FILES_DIR / "matches.csv"

SCORING_ENABLED = os.getenv("ENABLE_SCORING", "0") == "1"

def get_calculate_match_points():
    if not SCORING_ENABLED:
        return None
    try:
        from app.services.scoring import calculate_match_points
    except Exception as exc:
        print(f"Scoring disabled: {exc}")
        return None
    return calculate_match_points

def parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
             return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            print(f"Warning: Could not parse date '{date_str}'")
            return None

def update_teams(session: Session):
    if not TEAMS_CSV.exists():
        print(f"Error: {TEAMS_CSV} not found.")
        return

    print(f"Updating teams from {TEAMS_CSV}...")
    with open(TEAMS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        csv_names = set()
        for row in reader:
            name = row["name"].strip()
            if not name:
                continue
            csv_names.add(name)
            
            # Find existing team
            team = session.exec(select(FifaTeam).where(FifaTeam.name == name)).first()
            
            if not team:
                team = FifaTeam(name=name)
                print(f"  Creating new team: {name}")
            
            # Update fields
            iso_alpha_2 = row.get("iso_alpha_2", "").strip()
            country_code = row.get("country_code", "").strip()
            team.country_code = iso_alpha_2 or country_code or None
            if row.get("flag_emoji"):
                team.flag_emoji = row["flag_emoji"].strip()
            if row.get("group_letter"):
                team.group_letter = row["group_letter"].strip() or None
            
            team.updated_at = datetime.now(UTC)
            session.add(team)
            count += 1
            
        # Clear group assignments for teams not in the CSV
        if csv_names:
            extra_teams = session.exec(select(FifaTeam).where(FifaTeam.name.not_in(csv_names))).all()
            for team in extra_teams:
                team.group_letter = None
                team.updated_at = datetime.now(UTC)
                session.add(team)

        session.commit()
        print(f"Processed {count} teams.")

def update_matches(session: Session):
    if not MATCHES_CSV.exists():
        print(f"Error: {MATCHES_CSV} not found.")
        return

    print(f"Updating matches from {MATCHES_CSV}...")
    calculate_match_points = get_calculate_match_points()
    with open(MATCHES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            try:
                match_number = int(row["match_number"])
            except ValueError:
                print(f"  Skipping row with invalid match_number: {row}")
                continue

            match = session.exec(select(Match).where(Match.match_number == match_number)).first()
            if not match:
                print(f"  Creating new match #{match_number}")
                match = Match(match_number=match_number, round=row.get("round", "group_stage"))

            # Update basic fields
            if row.get("round"):
                match.round = row["round"].strip()
            if row.get("group_letter"):
                match.group_letter = row["group_letter"].strip() or None
            if row.get("home_slot"):
                match.home_slot = row["home_slot"].strip() or None
            if row.get("away_slot"):
                match.away_slot = row["away_slot"].strip() or None
            
            # Resolve Teams
            home_team_name = row.get("home_team", "").strip()
            if home_team_name:
                home_team = session.exec(select(FifaTeam).where(FifaTeam.name == home_team_name)).first()
                if home_team:
                    match.home_team_id = home_team.id
                else:
                    print(f"  Warning: Home team '{home_team_name}' not found for match #{match_number}")
            
            away_team_name = row.get("away_team", "").strip()
            if away_team_name:
                away_team = session.exec(select(FifaTeam).where(FifaTeam.name == away_team_name)).first()
                if away_team:
                    match.away_team_id = away_team.id
                else:
                    print(f"  Warning: Away team '{away_team_name}' not found for match #{match_number}")

            # Resolve Stadium (matches.csv uses "stadium" as the stadium_id value)
            stadium_key = row.get("stadium_id", "").strip() or row.get("stadium", "").strip()
            if stadium_key:
                stadium = session.exec(select(Stadium).where(Stadium.stadium_id == stadium_key)).first()
                if not stadium:
                    print(f"  Warning: Stadium ID '{stadium_key}' not found for match #{match_number}")
                else:
                    match.stadium_id = stadium.id

            # Date
            scheduled_at = parse_date(row.get("scheduled_datetime"))
            if scheduled_at:
                match.scheduled_datetime = scheduled_at

            # Scores and Status
            home_score_str = row.get("home_score", "").strip()
            away_score_str = row.get("away_score", "").strip()
            
            if home_score_str and away_score_str:
                try:
                    match.actual_home_score = int(home_score_str)
                    match.actual_away_score = int(away_score_str)
                    
                    # If status not explicitly set, assume completed if scores present
                    if not row.get("status") or row.get("status") == "scheduled":
                         match.status = "completed"
                    else:
                         match.status = row["status"].strip()

                    # Determine winner for knockout if completed
                    if match.round != "group_stage" and match.status == "completed":
                        if match.actual_home_score > match.actual_away_score:
                            match.actual_winner_team_id = match.home_team_id
                        elif match.actual_away_score > match.actual_home_score:
                            match.actual_winner_team_id = match.away_team_id
                        # Draw handling in knockout usually requires penalties (not in basic CSV)
                except ValueError:
                    print(f"  Warning: Invalid scores for match #{match_number}")
            else:
                if row.get("status"):
                    match.status = row["status"].strip()

            match.updated_at = datetime.now(UTC)
            session.add(match)
            
            # If match is completed, recalculate points
            if match.status == "completed":
                 # We need to commit first to ensure match is updated in DB before calculation if needed, 
                 # but calculate_match_points uses the object passed or DB?
                 # Looking at logic, it queries predictions.
                 # Let's add to session, commit at end of loop? 
                 # Better to commit per match if we want to run calculation immediately?
                 # No, better to batch commit then run calculations?
                 # The `calculate_match_points` function likely takes the DB session and the match object.
                 pass

            count += 1
        
        session.commit()
        
        if calculate_match_points is not None:
            # Recalculate points for completed matches in this CSV.
            f.seek(0)
            reader = csv.DictReader(f)
            for row in reader:
                 try:
                    m_num = int(row["match_number"])
                    m = session.exec(select(Match).where(Match.match_number == m_num)).first()
                    if m and m.status == "completed":
                        calculate_match_points(session, m)
                 except ValueError:
                     pass
        
        print(f"Processed {count} matches.")


def update_stadiums(session: Session):
    if not STADIUMS_CSV.exists():
        print(f"Error: {STADIUMS_CSV} not found.")
        return

    print(f"Updating stadiums from {STADIUMS_CSV}...")
    with open(STADIUMS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            try:
                stadium_pk = int(row["id"])
            except (ValueError, TypeError):
                print(f"  Skipping row with invalid id: {row}")
                continue

            stadium = session.get(Stadium, stadium_pk)
            if not stadium:
                stadium = Stadium(id=stadium_pk)
                print(f"  Creating new stadium: {row.get('name', '').strip() or stadium_pk}")

            stadium_id = row.get("stadium_id", "").strip()
            if stadium_id:
                stadium.stadium_id = stadium_id

            name = row.get("name", "").strip()
            city = row.get("city", "").strip()
            country = row.get("country", "").strip()

            if name:
                stadium.name = name
            if city:
                stadium.city = city
            if country:
                stadium.country = country

            session.add(stadium)
            count += 1

        session.commit()
        print(f"Processed {count} stadiums.")


def main():
    create_db_and_tables()
    with Session(engine) as session:
        update_teams(session)
        update_stadiums(session)
        update_matches(session)

if __name__ == "__main__":
    main()
