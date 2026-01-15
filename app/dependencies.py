from datetime import datetime
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from sqlmodel import Session, select

from .database import get_session
from .models.user import User
from .models.session import Session as UserSession
from .config import SESSION_COOKIE_NAME


async def get_current_user(
    request: Request,
    db: Session = Depends(get_session)
) -> Optional[User]:
    """Get the current logged-in user from session cookie."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None

    # Find valid session
    statement = select(UserSession).where(
        UserSession.session_token == session_token,
        UserSession.expires_at > datetime.utcnow()
    )
    user_session = db.exec(statement).first()

    if not user_session:
        return None

    # Get user
    statement = select(User).where(User.id == user_session.user_id)
    user = db.exec(statement).first()

    return user


async def require_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require a logged-in user, redirect to login if not authenticated."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(require_user)
) -> User:
    """Require an admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
