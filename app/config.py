"""
ConnectX Configuration Module
=============================
Defines configuration environments for development, testing, and production.
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration class with default settings."""

    # Security
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "connectx-super-secret-key-2026"
    )

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER, "avatars")
    ATTACHMENT_FOLDER = os.path.join(UPLOAD_FOLDER, "attachments")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "txt", "docx", "doc", "zip", "csv"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg"}
    ALLOWED_EXTENSIONS = (
        ALLOWED_IMAGE_EXTENSIONS
        | ALLOWED_DOCUMENT_EXTENSIONS
        | ALLOWED_AUDIO_EXTENSIONS
    )

    # SocketIO
    SOCKETIO_ASYNC_MODE = os.environ.get("SOCKETIO_ASYNC_MODE", "threading")
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"

    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Application details
    APP_NAME = "ConnectX"
    COURSE_CODE = ""
    SUBJECT = ""
    ACADEMIC_YEAR = "2025-2026"


class DevelopmentConfig(Config):
    """Configuration used during active local development."""

    DEBUG = True
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'connectx.db'}")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url


class TestingConfig(Config):
    """Configuration used for automated Pytest test suites."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost.localdomain"


class ProductionConfig(Config):
    """Configuration used for deployed production environment."""

    DEBUG = False
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'connectx_prod.db'}")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

