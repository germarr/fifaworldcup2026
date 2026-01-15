from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR, STATIC_DIR
from app.database import create_db_and_tables
from app.routers import auth, pages, predictions, leaderboard, teams, admin, bracket


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables
    create_db_and_tables()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="FIFA World Cup 2026 Bracket Game",
    description="Predict match outcomes and compete with friends!",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Set up templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include routers
app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(predictions.router)
app.include_router(leaderboard.router)
app.include_router(teams.router)
app.include_router(admin.router)
app.include_router(bracket.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
