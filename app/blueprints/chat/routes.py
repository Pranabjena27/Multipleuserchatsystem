"""
Chat Interface Blueprint Routes
===============================
Renders the primary real-time multi-user chat views and handles direct channel routing.
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.chat import Conversation, ConversationParticipant
from app.models.audit import SystemAnnouncement

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/")
@login_required
def index():
    """Main dashboard rendering the ConnectX 3-pane real-time chat workstation."""
    # Active system announcements
    announcements = (
        SystemAnnouncement.query.filter_by(is_active=True)
        .order_by(SystemAnnouncement.created_at.desc())
        .limit(3)
        .all()
    )

    # User's joined conversations
    participations = (
        ConversationParticipant.query.filter_by(user_id=current_user.id)
        .join(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    conversations = [p.conversation for p in participations]

    return render_template(
        "chat/index.html",
        conversations=conversations,
        announcements=announcements,
        user=current_user,
    )


@chat_bp.route("/c/<int:conversation_id>")
@login_required
def open_conversation(conversation_id: int):
    """Direct route linking into a specific conversation room."""
    conv = Conversation.query.get_or_404(conversation_id)
    if not conv.is_member(current_user.id) and not current_user.is_admin:
        return redirect(url_for("chat.index"))

    announcements = (
        SystemAnnouncement.query.filter_by(is_active=True)
        .order_by(SystemAnnouncement.created_at.desc())
        .limit(3)
        .all()
    )

    participations = (
        ConversationParticipant.query.filter_by(user_id=current_user.id)
        .join(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    conversations = [p.conversation for p in participations]

    return render_template(
        "chat/index.html",
        conversations=conversations,
        active_conversation_id=conversation_id,
        announcements=announcements,
        user=current_user,
    )

