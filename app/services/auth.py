import secrets
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from sqlmodel import Session, select

from ..models.user import User
from ..models.session import Session as UserSession
from ..config import SESSION_EXPIRE_DAYS


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_session(db: Session, user_id: int) -> str:
    """Create a new session for a user and return the session token."""
    # Generate secure token
    session_token = secrets.token_urlsafe(32)

    # Calculate expiry
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRE_DAYS)

    # Create session
    user_session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    db.add(user_session)
    db.commit()

    return session_token


def delete_session(db: Session, session_token: str) -> None:
    """Delete a session (logout)."""
    statement = select(UserSession).where(UserSession.session_token == session_token)
    user_session = db.exec(statement).first()
    if user_session:
        db.delete(user_session)
        db.commit()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email."""
    statement = select(User).where(User.email == email)
    return db.exec(statement).first()


def create_user(
    db: Session,
    email: str,
    password: str,
    display_name: str,
    is_admin: bool = False
) -> User:
    """Create a new user."""
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
