"""
Chat and Communication Models Module
====================================
Defines entities for Conversations, Group Memberships, Messages,
Attachments, Reactions, Message Status (Read Receipts), and Notifications.
"""

from datetime import datetime, timezone
from app.extensions import db


class Conversation(db.Model):
    """
    Represents a chat channel: either a 1-to-1 direct message or a multi-user group.
    """

    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), default="direct", nullable=False)  # 'direct' or 'group'
    title = db.Column(db.String(128), nullable=True)  # Name for groups
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(256), default="default_group.svg")
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    creator = db.relationship("User", foreign_keys=[creator_id])
    participants = db.relationship(
        "ConversationParticipant",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    messages = db.relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at.asc()",
    )

    def is_member(self, user_id: int) -> bool:
        """Check if user is a participant of this conversation."""
        return any(p.user_id == user_id for p in self.participants)

    def get_participant_role(self, user_id: int) -> str | None:
        """Retrieve the role of the user within this conversation."""
        for p in self.participants:
            if p.user_id == user_id:
                return p.role
        return None

    def get_other_participant(self, current_user_id: int):
        """For direct 1-to-1 chats, returns the other user."""
        if self.type != "direct":
            return None
        for p in self.participants:
            if p.user_id != current_user_id:
                return p.user
        return None

    def get_display_title(self, current_user_id: int) -> str:
        """Dynamic conversation name resolution based on chat type."""
        if self.type == "group":
            return self.title or "Unnamed Group"
        other_user = self.get_other_participant(current_user_id)
        if other_user:
            return other_user.full_name or other_user.username
        return "Direct Conversation"

    def get_display_avatar(self, current_user_id: int) -> str:
        """Dynamic avatar resolution for conversation list."""
        if self.type == "group":
            return self.icon or "default_group.svg"
        other_user = self.get_other_participant(current_user_id)
        if other_user:
            return other_user.avatar
        return "default_avatar.svg"

    def to_dict(self, current_user_id: int | None = None) -> dict:
        """Serialize conversation details for JSON API and Socket payloads."""
        latest_msg = (
            self.messages[-1].to_dict() if self.messages else None
        )
        return {
            "id": self.id,
            "type": self.type,
            "title": (
                self.get_display_title(current_user_id)
                if current_user_id
                else (self.title or "Conversation")
            ),
            "description": self.description or "",
            "icon": (
                self.get_display_avatar(current_user_id)
                if current_user_id
                else self.icon
            ),
            "creator_id": self.creator_id,
            "participant_count": len(self.participants),
            "participants": [p.to_dict() for p in self.participants],
            "latest_message": latest_msg,
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }

    def __repr__(self) -> str:
        return f"<Conversation {self.id} ({self.type}): {self.title}>"


class ConversationParticipant(db.Model):
    """
    Association entity representing membership of a user within a conversation.
    Supports role-based privileges: 'admin', 'moderator', 'member'.
    """

    __tablename__ = "conversation_participants"
    __table_args__ = (
        db.UniqueConstraint(
            "conversation_id", "user_id", name="uq_conversation_user"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20), default="member", nullable=False)  # 'admin', 'moderator', 'member'
    joined_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_read_message_id = db.Column(db.Integer, default=0)
    is_muted = db.Column(db.Boolean, default=False)

    # Relationships
    conversation = db.relationship(
        "Conversation", back_populates="participants"
    )
    user = db.relationship("User", back_populates="participations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "full_name": self.user.full_name if self.user else None,
            "avatar": self.user.avatar if self.user else "default_avatar.svg",
            "is_online": self.user.is_online if self.user else False,
            "role": self.role,
            "joined_at": (
                self.joined_at.isoformat() if self.joined_at else None
            ),
            "last_read_message_id": self.last_read_message_id,
        }

    def __repr__(self) -> str:
        return f"<Participant User:{self.user_id} in Conv:{self.conversation_id} ({self.role})>"


class Message(db.Model):
    """
    Message entity holding chat communication, Python-based sentiment scores,
    spam tags, categorization, and attachment relationships.
    """

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id"), nullable=False, index=True
    )
    sender_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    parent_id = db.Column(
        db.Integer, db.ForeignKey("messages.id"), nullable=True
    )  # Enables recursive thread replies

    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default="text", nullable=False)  # 'text', 'image', 'file', 'audio', 'system'

    # Academic Python Feature Fields
    category = db.Column(db.String(30), default="general", nullable=False)
    sentiment_score = db.Column(db.Float, default=0.0)
    sentiment_label = db.Column(db.String(20), default="neutral")
    is_spam = db.Column(db.Boolean, default=False)
    spam_score = db.Column(db.Float, default=0.0)

    # State & Timestamps
    is_deleted = db.Column(db.Boolean, default=False)
    is_edited = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    conversation = db.relationship("Conversation", back_populates="messages")
    sender = db.relationship("User", back_populates="messages")
    replies = db.relationship(
        "Message",
        backref=db.backref("parent", remote_side=[id]),
        lazy="selectin",
    )
    attachments = db.relationship(
        "Attachment",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reactions = db.relationship(
        "MessageReaction",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    read_receipts = db.relationship(
        "ReadReceipt",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        """Serialize message record into structured dictionary."""
        reactions_grouped = {}
        for r in self.reactions:
            if r.reaction not in reactions_grouped:
                reactions_grouped[r.reaction] = []
            reactions_grouped[r.reaction].append(
                {"user_id": r.user_id, "username": r.user.username if r.user else "Unknown"}
            )

        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "sender_name": (
                self.sender.full_name or self.sender.username
                if self.sender
                else "System"
            ),
            "sender_username": self.sender.username if self.sender else "system",
            "sender_avatar": (
                self.sender.avatar if self.sender else "default_avatar.svg"
            ),
            "parent_id": self.parent_id,
            "parent_snippet": (
                self.parent.content[:40] + "..."
                if self.parent and not self.parent.is_deleted
                else None
            ),
            "content": "[Message deleted]" if self.is_deleted else self.content,
            "message_type": self.message_type,
            "category": self.category,
            "sentiment_score": round(self.sentiment_score, 2),
            "sentiment_label": self.sentiment_label,
            "is_spam": self.is_spam,
            "is_deleted": self.is_deleted,
            "is_edited": self.is_edited,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "formatted_time": (
                self.created_at.strftime("%I:%M %p") if self.created_at else ""
            ),
            "formatted_date": (
                self.created_at.strftime("%b %d, %Y") if self.created_at else ""
            ),
            "attachments": [att.to_dict() for att in self.attachments],
            "reactions": reactions_grouped,
            "read_count": len(self.read_receipts),
        }

    def __repr__(self) -> str:
        return f"<Message {self.id} in Conv:{self.conversation_id} by User:{self.sender_id}>"


class Attachment(db.Model):
    """Stores uploaded file attachments associated with messages."""

    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(
        db.Integer, db.ForeignKey("messages.id"), nullable=False
    )
    filename = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # 'image', 'document', 'audio'
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    file_url = db.Column(db.String(512), nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    message = db.relationship("Message", back_populates="attachments")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "file_url": self.file_url,
        }

    def __repr__(self) -> str:
        return f"<Attachment {self.id}: {self.original_filename} ({self.file_type})>"


class MessageReaction(db.Model):
    """Emoji reaction attached by a user to a specific message."""

    __tablename__ = "message_reactions"
    __table_args__ = (
        db.UniqueConstraint(
            "message_id", "user_id", "reaction", name="uq_msg_user_reaction"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(
        db.Integer, db.ForeignKey("messages.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reaction = db.Column(db.String(20), nullable=False)  # Emoji symbol
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    message = db.relationship("Message", back_populates="reactions")
    user = db.relationship("User", back_populates="reactions")

    def __repr__(self) -> str:
        return f"<Reaction {self.reaction} on Msg:{self.message_id} by User:{self.user_id}>"


class ReadReceipt(db.Model):
    """
    MessageStatus / ReadReceipt entity tracking delivery and read status.
    """

    __tablename__ = "message_status"
    __table_args__ = (
        db.UniqueConstraint(
            "message_id", "user_id", name="uq_msg_user_status"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(
        db.Integer, db.ForeignKey("messages.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    delivered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    message = db.relationship("Message", back_populates="read_receipts")
    user = db.relationship("User")

    def __repr__(self) -> str:
        return f"<MessageStatus Msg:{self.message_id} User:{self.user_id}>"


# Semantic alias
MessageStatus = ReadReceipt


class Notification(db.Model):
    """
    User notification entity for real-time alerts, invites, and mentions.
    """

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    actor_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )
    type = db.Column(db.String(32), nullable=False)  # 'mention', 'direct_message', 'invite'
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    link_url = db.Column(db.String(256), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor = db.relationship("User", foreign_keys=[actor_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "link_url": self.link_url,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Notification {self.id} for User:{self.user_id} ({self.type})>"
