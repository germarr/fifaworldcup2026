from typing import Optional
from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import Session
from app.database import get_session
from app.auth import get_user_by_session_token
from app.models import User


def get_current_user(
    session_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_session)
) -> User:
    """
    Dependency to get the current authenticated user from session cookie.
    Raises 401 if user is not authenticated.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user = get_user_by_session_token(db, session_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    return user


def get_current_user_optional(
    session_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_session)
) -> Optional[User]:
    """
    Dependency to get the current user if authenticated, None otherwise.
    Does not raise an exception if user is not authenticated.
    """
    if not session_token:
        return None

    return get_user_by_session_token(db, session_token)


def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to ensure the current user is the admin."""
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user
