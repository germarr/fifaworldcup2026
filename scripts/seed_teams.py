"""Seed FIFA teams for World Cup 2026."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session
from app.database import engine, create_db_and_tables
from app.models.fifa_team import FifaTeam

# 48 teams for World Cup 2026
# Some teams are confirmed, others are placeholders
TEAMS = [
    # Group A
    {"name": "USA", "country_code": "USA", "flag_emoji": "🇺🇸", "group_letter": "A"},
    {"name": "Mexico", "country_code": "MEX", "flag_emoji": "🇲🇽", "group_letter": "A"},
    {"name": "Canada", "country_code": "CAN", "flag_emoji": "🇨🇦", "group_letter": "A"},
    {"name": "TBD A4", "country_code": None, "flag_emoji": None, "group_letter": "A"},

    # Group B
    {"name": "Brazil", "country_code": "BRA", "flag_emoji": "🇧🇷", "group_letter": "B"},
    {"name": "Argentina", "country_code": "ARG", "flag_emoji": "🇦🇷", "group_letter": "B"},
    {"name": "Colombia", "country_code": "COL", "flag_emoji": "🇨🇴", "group_letter": "B"},
    {"name": "TBD B4", "country_code": None, "flag_emoji": None, "group_letter": "B"},

    # Group C
    {"name": "Germany", "country_code": "GER", "flag_emoji": "🇩🇪", "group_letter": "C"},
    {"name": "France", "country_code": "FRA", "flag_emoji": "🇫🇷", "group_letter": "C"},
    {"name": "Spain", "country_code": "ESP", "flag_emoji": "🇪🇸", "group_letter": "C"},
    {"name": "TBD C4", "country_code": None, "flag_emoji": None, "group_letter": "C"},

    # Group D
    {"name": "England", "country_code": "ENG", "flag_emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "group_letter": "D"},
    {"name": "Netherlands", "country_code": "NED", "flag_emoji": "🇳🇱", "group_letter": "D"},
    {"name": "Belgium", "country_code": "BEL", "flag_emoji": "🇧🇪", "group_letter": "D"},
    {"name": "TBD D4", "country_code": None, "flag_emoji": None, "group_letter": "D"},

    # Group E
    {"name": "Portugal", "country_code": "POR", "flag_emoji": "🇵🇹", "group_letter": "E"},
    {"name": "Italy", "country_code": "ITA", "flag_emoji": "🇮🇹", "group_letter": "E"},
    {"name": "Croatia", "country_code": "CRO", "flag_emoji": "🇭🇷", "group_letter": "E"},
    {"name": "TBD E4", "country_code": None, "flag_emoji": None, "group_letter": "E"},

    # Group F
    {"name": "Japan", "country_code": "JPN", "flag_emoji": "🇯🇵", "group_letter": "F"},
    {"name": "South Korea", "country_code": "KOR", "flag_emoji": "🇰🇷", "group_letter": "F"},
    {"name": "Australia", "country_code": "AUS", "flag_emoji": "🇦🇺", "group_letter": "F"},
    {"name": "TBD F4", "country_code": None, "flag_emoji": None, "group_letter": "F"},

    # Group G
    {"name": "Morocco", "country_code": "MAR", "flag_emoji": "🇲🇦", "group_letter": "G"},
    {"name": "Senegal", "country_code": "SEN", "flag_emoji": "🇸🇳", "group_letter": "G"},
    {"name": "Nigeria", "country_code": "NGA", "flag_emoji": "🇳🇬", "group_letter": "G"},
    {"name": "TBD G4", "country_code": None, "flag_emoji": None, "group_letter": "G"},

    # Group H
    {"name": "Uruguay", "country_code": "URU", "flag_emoji": "🇺🇾", "group_letter": "H"},
    {"name": "Ecuador", "country_code": "ECU", "flag_emoji": "🇪🇨", "group_letter": "H"},
    {"name": "Chile", "country_code": "CHI", "flag_emoji": "🇨🇱", "group_letter": "H"},
    {"name": "TBD H4", "country_code": None, "flag_emoji": None, "group_letter": "H"},

    # Group I
    {"name": "Switzerland", "country_code": "SUI", "flag_emoji": "🇨🇭", "group_letter": "I"},
    {"name": "Denmark", "country_code": "DEN", "flag_emoji": "🇩🇰", "group_letter": "I"},
    {"name": "Poland", "country_code": "POL", "flag_emoji": "🇵🇱", "group_letter": "I"},
    {"name": "TBD I4", "country_code": None, "flag_emoji": None, "group_letter": "I"},

    # Group J
    {"name": "Serbia", "country_code": "SRB", "flag_emoji": "🇷🇸", "group_letter": "J"},
    {"name": "Ukraine", "country_code": "UKR", "flag_emoji": "🇺🇦", "group_letter": "J"},
    {"name": "Austria", "country_code": "AUT", "flag_emoji": "🇦🇹", "group_letter": "J"},
    {"name": "TBD J4", "country_code": None, "flag_emoji": None, "group_letter": "J"},

    # Group K
    {"name": "Saudi Arabia", "country_code": "KSA", "flag_emoji": "🇸🇦", "group_letter": "K"},
    {"name": "Iran", "country_code": "IRN", "flag_emoji": "🇮🇷", "group_letter": "K"},
    {"name": "Qatar", "country_code": "QAT", "flag_emoji": "🇶🇦", "group_letter": "K"},
    {"name": "TBD K4", "country_code": None, "flag_emoji": None, "group_letter": "K"},

    # Group L
    {"name": "Costa Rica", "country_code": "CRC", "flag_emoji": "🇨🇷", "group_letter": "L"},
    {"name": "Panama", "country_code": "PAN", "flag_emoji": "🇵🇦", "group_letter": "L"},
    {"name": "Jamaica", "country_code": "JAM", "flag_emoji": "🇯🇲", "group_letter": "L"},
    {"name": "TBD L4", "country_code": None, "flag_emoji": None, "group_letter": "L"},
]


def seed_teams():
    create_db_and_tables()

    with Session(engine) as session:
        # Check if teams already exist
        existing = session.query(FifaTeam).first()
        if existing:
            print("Teams already seeded. Use --force to re-seed.")
            return

        for team_data in TEAMS:
            team = FifaTeam(**team_data)
            session.add(team)

        session.commit()
        print(f"Seeded {len(TEAMS)} FIFA teams.")


if __name__ == "__main__":
    import sys
    if "--force" in sys.argv:
        with Session(engine) as session:
            session.query(FifaTeam).delete()
            session.commit()
    seed_teams()
