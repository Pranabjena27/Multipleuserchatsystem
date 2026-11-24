"""
User and Settings Model Module
==============================
Implements user account management, password hashing, authentication mixins,
profile attributes, and personalized user settings.
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """
    User entity representing a registered participant in ConnectX.
    Demonstrates OOP concepts: Encapsulation, Methods, and Inheritance from UserMixin.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False, default="")
    bio = db.Column(db.Text, default="Hey there! I am using ConnectX.")
    avatar = db.Column(db.String(256), default="default_avatar.svg")
    status_message = db.Column(db.String(128), default="Available")
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    role = db.Column(db.String(20), default="user", nullable=False)  # 'admin', 'moderator', 'user'
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    settings = db.relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    participations = db.relationship(
        "ConversationParticipant",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    messages = db.relationship(
        "Message",
        back_populates="sender",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    reactions = db.relationship(
        "MessageReaction",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    notifications = db.relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def set_password(self, password: str) -> None:
        """Hash and set user password securely using Werkzeug (PBKDF2-HMAC-SHA256)."""
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify given plain-text password against stored password hash."""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """Encapsulated check to determine if the user holds admin rights."""
        return self.role == "admin"

    @property
    def is_moderator(self) -> bool:
        """Encapsulated check to determine if the user holds moderator or admin rights."""
        return self.role in ("admin", "moderator")

    @property
    def is_active(self) -> bool:
        """Flask-Login required property: banned accounts cannot log in."""
        return not self.is_banned

    def update_presence(self, is_online: bool) -> None:
        """Update user presence status and timestamp."""
        self.is_online = is_online
        self.last_seen = datetime.now(timezone.utc)
        db.session.commit()

    def get_or_create_settings(self):
        """Retrieve existing or initialize default user settings."""
        if not self.settings:
            settings = UserSettings(user_id=self.id)
            db.session.add(settings)
            db.session.commit()
            return settings
        return self.settings

    def to_dict(self, include_email: bool = False) -> dict:
        """Serialize user entity to a Python dictionary."""
        data = {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name or self.username,
            "bio": self.bio,
            "avatar": self.avatar,
            "status_message": self.status_message,
            "is_online": self.is_online,
            "last_seen": (
                self.last_seen.isoformat() if self.last_seen else None
            ),
            "role": self.role,
            "is_banned": self.is_banned,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
        if include_email:
            data["email"] = self.email
        return data

    def __repr__(self) -> str:
        return f"<User {self.id}: {self.username} ({self.role})>"


class UserSettings(db.Model):
    """
    Stores user-specific UI preferences, theme choices, and privacy controls.
    """

    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    theme = db.Column(db.String(16), default="light", nullable=False)  # 'light' or 'dark'
    sound_enabled = db.Column(db.Boolean, default=True, nullable=False)
    desktop_notifications = db.Column(db.Boolean, default=True, nullable=False)
    enter_is_send = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    user = db.relationship("User", back_populates="settings")

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "sound_enabled": self.sound_enabled,
            "desktop_notifications": self.desktop_notifications,
            "enter_is_send": self.enter_is_send,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<UserSettings User:{self.user_id} Theme:{self.theme}>"
