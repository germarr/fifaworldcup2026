"""Seed stadiums for World Cup 2026."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session
from app.database import engine, create_db_and_tables
from app.models.stadium import Stadium

# World Cup 2026 venues (USA, Mexico, Canada)
STADIUMS = [
    # USA
    {"name": "MetLife Stadium", "city": "East Rutherford, NJ", "country": "USA"},
    {"name": "AT&T Stadium", "city": "Arlington, TX", "country": "USA"},
    {"name": "SoFi Stadium", "city": "Inglewood, CA", "country": "USA"},
    {"name": "Hard Rock Stadium", "city": "Miami Gardens, FL", "country": "USA"},
    {"name": "Mercedes-Benz Stadium", "city": "Atlanta, GA", "country": "USA"},
    {"name": "Levi's Stadium", "city": "Santa Clara, CA", "country": "USA"},
    {"name": "NRG Stadium", "city": "Houston, TX", "country": "USA"},
    {"name": "Lincoln Financial Field", "city": "Philadelphia, PA", "country": "USA"},
    {"name": "Gillette Stadium", "city": "Foxborough, MA", "country": "USA"},
    {"name": "Arrowhead Stadium", "city": "Kansas City, MO", "country": "USA"},
    {"name": "Lumen Field", "city": "Seattle, WA", "country": "USA"},

    # Mexico
    {"name": "Estadio Azteca", "city": "Mexico City", "country": "Mexico"},
    {"name": "Estadio Akron", "city": "Guadalajara", "country": "Mexico"},
    {"name": "Estadio BBVA", "city": "Monterrey", "country": "Mexico"},

    # Canada
    {"name": "BMO Field", "city": "Toronto", "country": "Canada"},
    {"name": "BC Place", "city": "Vancouver", "country": "Canada"},
]


def seed_stadiums():
    create_db_and_tables()

    with Session(engine) as session:
        existing = session.query(Stadium).first()
        if existing:
            print("Stadiums already seeded. Use --force to re-seed.")
            return

        for stadium_data in STADIUMS:
            stadium = Stadium(**stadium_data)
            session.add(stadium)

        session.commit()
        print(f"Seeded {len(STADIUMS)} stadiums.")


if __name__ == "__main__":
    if "--force" in sys.argv:
        with Session(engine) as session:
            session.query(Stadium).delete()
            session.commit()
    seed_stadiums()
