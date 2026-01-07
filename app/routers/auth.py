from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.models import User, Team
from app.database import get_session
import re
from app.auth import hash_password, authenticate_user, create_session, delete_session
from app.dependencies import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Home page - shows login/register or redirects to bracket if logged in."""
    if current_user:
        return RedirectResponse(url="/bracket", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def get_register(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Registration page."""
    if current_user:
        return RedirectResponse(url="/bracket", status_code=status.HTTP_303_SEE_OTHER)

    # Fetch all teams for favorite team dropdown
    all_teams = db.exec(select(Team).order_by(Team.name)).all()

    return templates.TemplateResponse("register.html", {
        "request": request,
        "all_teams": all_teams
    })


@router.post("/register")
async def post_register(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),  # NEW: Required email field
    favorite_team_id: int = Form(None),  # NEW: FK to Team table (optional)
    db: Session = Depends(get_session)
):
    """Handle user registration."""
    # Check if username already exists
    statement = select(User).where(User.username == username)
    existing_user = db.exec(statement).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists
    email_statement = select(User).where(User.email == email)
    existing_email = db.exec(email_statement).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Validate password length
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    if len(password) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be 72 characters or less"
        )

    # Create new user
    hashed_password = hash_password(password)
    new_user = User(
        username=username,
        password_hash=hashed_password,
        email=email,  # NEW
        favorite_team_id=favorite_team_id if favorite_team_id else None,  # NEW
        cookie_consent=True  # Set to true since they registered
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create session
    session = create_session(db, new_user.id)

    # Set session cookie
    response = RedirectResponse(url="/bracket", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="session_token",
        value=session.session_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days
        samesite="lax"
    )

    return response


@router.get("/login", response_class=HTMLResponse)
async def get_login(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Login page."""
    if current_user:
        return RedirectResponse(url="/bracket", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def post_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session)
):
    """Handle user login."""
    user = authenticate_user(db, username, password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Create session
    session = create_session(db, user.id)

    # Set session cookie
    response = RedirectResponse(url="/bracket", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="session_token",
        value=session.session_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days
        samesite="lax"
    )

    return response


@router.post("/logout")
async def logout(
    response: Response,
    session_token: str = None,
    db: Session = Depends(get_session)
):
    """Handle user logout."""
    if session_token:
        delete_session(db, session_token)

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="session_token")

    return response


@router.post("/cookie-consent")
async def cookie_consent(
    response: Response,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """Handle cookie consent."""
    if current_user:
        current_user.cookie_consent = True
        db.add(current_user)
        db.commit()

    return {"status": "success"}
