"""
Audit and Moderation Models Module
==================================
Tracks administrative audits, user moderation reports, and global announcements.
"""

from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    """
    Tracks significant system operations for administrative oversight and security auditing.
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False)  # 'USER_REGISTER', 'USER_BAN', 'GROUP_CREATE', etc.
    target_type = db.Column(db.String(32), nullable=True)  # 'user', 'message', 'group'
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    user = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "System",
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": (
                self.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.created_at
                else None
            ),
        }

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by User:{self.user_id}>"


class ModerationReport(db.Model):
    """
    User-submitted reports flagging offensive or abusive messages.
    """

    __tablename__ = "moderation_reports"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    message_id = db.Column(
        db.Integer, db.ForeignKey("messages.id"), nullable=False
    )
    reason = db.Column(db.String(128), nullable=False)  # 'spam', 'harassment', 'inappropriate', 'other'
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending")  # 'pending', 'resolved', 'dismissed'
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    reporter = db.relationship("User", foreign_keys=[reporter_id])
    message = db.relationship("Message", foreign_keys=[message_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reporter_username": (
                self.reporter.username if self.reporter else "Unknown"
            ),
            "message_id": self.message_id,
            "message_content": (
                self.message.content if self.message else "[Deleted]"
            ),
            "message_sender": (
                self.message.sender.username
                if self.message and self.message.sender
                else "System"
            ),
            "reason": self.reason,
            "details": self.details,
            "status": self.status,
            "created_at": (
                self.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.created_at
                else None
            ),
        }

    def __repr__(self) -> str:
        return f"<ModerationReport {self.id} for Msg:{self.message_id} ({self.status})>"


class SystemAnnouncement(db.Model):
    """
    Global broadcast announcement published by administrators.
    """

    __tablename__ = "system_announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default="info")  # 'info', 'warning', 'critical'
    is_active = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    creator = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_by": self.creator.username if self.creator else "Admin",
            "created_at": (
                self.created_at.strftime("%Y-%m-%d %H:%M")
                if self.created_at
                else None
            ),
        }

    def __repr__(self) -> str:
        return f"<SystemAnnouncement {self.id}: {self.title}>"

