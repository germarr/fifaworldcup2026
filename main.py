from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlmodel import Session, select
from app.database import create_db_and_tables, engine
from app.auth import hash_password
from app.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create database tables
    create_db_and_tables()
    with Session(engine) as db:
        admin_statement = select(User).where(User.username == "admin")
        admin_user = db.exec(admin_statement).first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=hash_password("password")
            )
            db.add(admin_user)
            db.commit()
    yield
    # Shutdown: cleanup if needed


# Initialize FastAPI app
app = FastAPI(
    title="FIFA World Cup Bracket Predictor",
    description="Predict World Cup match outcomes and compete with friends",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Include routers
from app.routers import auth, brackets, api, social, crm

app.include_router(auth.router, tags=["auth"])
app.include_router(brackets.router, tags=["brackets"])
app.include_router(api.router, tags=["api"])
app.include_router(social.router, tags=["social"])
app.include_router(crm.router, tags=["crm"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
