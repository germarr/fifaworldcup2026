from sqlmodel import SQLModel, create_engine
from app.models import User, Match, Prediction, Team, PlayerTeam, GroupStanding

engine = create_engine("sqlite:///:memory:")

try:
    SQLModel.metadata.create_all(engine)
    print("Models created successfully.")
except Exception as e:
    print(f"Error: {e}")
