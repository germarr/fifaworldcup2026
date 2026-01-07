import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select
from app.models import User, Session as SessionModel

# Session expiry duration (7 days)
SESSION_EXPIRY_DAYS = 7


def hash_password(password: str) -> str:
    """Hash a password using bcrypt. Truncates to 72 bytes for bcrypt compatibility."""
    # Bcrypt has a 72-byte limit on the password bytes
    # Encode to bytes and truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    # Hash the password
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    # Return as string for database storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)


def create_session(db: Session, user_id: int) -> SessionModel:
    """Create a new session for a user."""
    session_token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRY_DAYS)

    session = SessionModel(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def get_user_by_session_token(db: Session, session_token: str) -> Optional[User]:
    """Get user by session token if session is valid."""
    statement = select(SessionModel).where(SessionModel.session_token == session_token)
    session = db.exec(statement).first()

    if not session:
        return None

    # Check if session has expired
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        return None

    # Get and return the user
    user_statement = select(User).where(User.id == session.user_id)
    user = db.exec(user_statement).first()

    return user


def delete_session(db: Session, session_token: str) -> bool:
    """Delete a session (logout)."""
    statement = select(SessionModel).where(SessionModel.session_token == session_token)
    session = db.exec(statement).first()

    if session:
        db.delete(session)
        db.commit()
        return True

    return False


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    statement = select(User).where(User.username == username)
    user = db.exec(statement).first()

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
