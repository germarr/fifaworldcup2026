"""
Update Round of 32 match placeholders to match specific 12-group allocation logic.
Includes 3rd place placeholders (e.g., 3ABCDF).
"""

import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models import Match

def update_round_of_32():
    with Session(engine) as session:
        print("Updating Round of 32 placeholders...")
        
        # Mapping of Match Number -> (Team1 Placeholder, Team2 Placeholder)
        # Matches 73-88
        updates = {
            73: ("2A", "2B"),       # Inferred missing match
            74: ("1C", "2F"),
            75: ("1E", "3ABCDF"),
            76: ("1F", "2C"),
            77: ("2E", "2I"),
            78: ("1I", "3CDFGH"),
            79: ("1A", "3CEFHI"),
            80: ("1L", "3EHIJK"),
            81: ("1G", "3AEHIJ"),
            82: ("1D", "3BEFIJ"),
            83: ("1H", "2J"),
            84: ("2K", "2L"),
            85: ("1B", "3EFGIJ"),
            86: ("2D", "2G"),
            87: ("1J", "2H"),
            88: ("1K", "3DEIJL"),
        }
        
        for match_num, (t1, t2) in updates.items():
            statement = select(Match).where(Match.match_number == match_num)
            match = session.exec(statement).first()
            
            if match:
                print(f"Match {match_num}: Updating {match.team1_placeholder}-{match.team2_placeholder} -> {t1}-{t2}")
                match.team1_placeholder = t1
                match.team2_placeholder = t2
                session.add(match)
            else:
                print(f"Warning: Match {match_num} not found!")

        session.commit()
        print("Update complete!")

if __name__ == "__main__":
    update_round_of_32()
