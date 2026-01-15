import os
import secrets
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_URL = f"sqlite:///{BASE_DIR}/worldcup.db"

# Security
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
SESSION_COOKIE_NAME = "worldcup_session"
SESSION_EXPIRE_DAYS = 30

# Admin credentials (in production, use environment variables)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"

# Templates
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"
