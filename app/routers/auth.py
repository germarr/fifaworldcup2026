from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from ..config import TEMPLATES_DIR, SESSION_COOKIE_NAME, SESSION_EXPIRE_DAYS
from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..services.auth import (
    get_user_by_email,
    create_user,
    verify_password,
    create_session,
    delete_session
)

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "current_user": None
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session)
):
    user = get_user_by_email(db, email)

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "current_user": None,
            "error": "Invalid email or password"
        }, status_code=400)

    # Create session
    session_token = create_session(db, user.id)

    # Redirect to home with session cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax"
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "current_user": None
    })


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_session)
):
    # Check if user exists
    if get_user_by_email(db, email):
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "current_user": None,
            "error": "Email already registered"
        }, status_code=400)

    # Create user
    user = create_user(db, email, password, display_name)

    # Create session
    session_token = create_session(db, user.id)

    # Redirect to home with session cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax"
    )
    return response


@router.get("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_session)
):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        delete_session(db, session_token)

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.post("/cookie-consent")
async def cookie_consent(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    if current_user:
        current_user.cookie_consent = True
        db.add(current_user)
        db.commit()
    return {"status": "ok"}
