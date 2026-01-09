from sqlmodel import SQLModel, create_engine
from app.models import *

engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(engine)
print("Success")
