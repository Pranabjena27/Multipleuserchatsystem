"""
SocketIO Event Handlers Module
==============================
Handles bidirectional WebSocket events: connections, presence broadcast,
message dispatch, typing indicators, read receipts, reactions, message editing, and deletion.
"""

from datetime import datetime, timezone
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app.extensions import db, socketio
from app.models.user import User
from app.models.chat import (
    Conversation,
    ConversationParticipant,
    Message,
    Attachment,
    MessageReaction,
    ReadReceipt,
    Notification,
)
from app.models.audit import ModerationReport
from app.sockets.state import socket_state
from app.python_features.processor import MessageProcessor
from app.python_features.spam_detector import SpamDetector
from app.python_features.sentiment import SentimentAnalyzer
from app.python_features.categorizer import MessageCategorizer
from app.python_features.moderation import ContentModerator

# Initialize pure Python feature engines
processor = MessageProcessor()
spam_detector = SpamDetector()
sentiment_analyzer = SentimentAnalyzer()
categorizer = MessageCategorizer()
moderator = ContentModerator()


@socketio.on("connect")
def handle_connect():
    """Client connected to WebSocket server."""
    if not current_user.is_authenticated:
        return False  # Reject unauthenticated socket connections

    user_id = current_user.id
    first_connection = socket_state.register_socket(user_id, request.sid)

    # Join user's personal notification room
    join_room(f"user_{user_id}")

    # Auto-join all authorized conversation rooms for real-time delivery
    participations = ConversationParticipant.query.filter_by(user_id=user_id).all()
    for p in participations:
        join_room(f"conv_{p.conversation_id}")
        socket_state.user_joined_room(user_id, p.conversation_id)

    if first_connection:
        current_user.is_online = True
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        emit(
            "user_status_changed",
            {"user_id": user_id, "is_online": True, "username": current_user.username},
            broadcast=True,
        )

    emit("connection_acknowledged", {"user_id": user_id, "status": "connected"})


@socketio.on("disconnect")
def handle_disconnect():
    """Client disconnected from WebSocket server."""
    user_id, has_gone_offline = socket_state.unregister_socket(request.sid)
    if user_id and has_gone_offline:
        user = User.query.get(user_id)
        if user:
            user.is_online = False
            user.last_seen = datetime.now(timezone.utc)
            db.session.commit()
            emit(
                "user_status_changed",
                {
                    "user_id": user_id,
                    "is_online": False,
                    "last_seen": user.last_seen.isoformat(),
                    "username": user.username,
                },
                broadcast=True,
            )


@socketio.on("join_conversation")
def handle_join_conversation(data):
    """Client joins a specific conversation room."""
    if not current_user.is_authenticated:
        return

    conv_id = data.get("conversation_id")
    if not conv_id:
        return

    conv = Conversation.query.get(conv_id)
    if not conv or (not conv.is_member(current_user.id) and not current_user.is_admin):
        emit("error_alert", {"message": "Access denied to conversation"})
        return

    room_name = f"conv_{conv_id}"
    join_room(room_name)
    socket_state.user_joined_room(current_user.id, conv_id)
    emit("room_joined", {"conversation_id": conv_id})


@socketio.on("leave_conversation")
def handle_leave_conversation(data):
    """Client leaves a specific conversation room."""
    if not current_user.is_authenticated:
        return

    conv_id = data.get("conversation_id")
    if not conv_id:
        return

    room_name = f"conv_{conv_id}"
    leave_room(room_name)
    socket_state.user_left_room(current_user.id, conv_id)


@socketio.on("send_message")
def handle_send_message(data):
    """
    Process incoming message through Python NLP pipeline, save to database,
    and broadcast in real-time to all conversation participants.
    """
    if not current_user.is_authenticated:
        emit("error_alert", {"message": "Authentication required"})
        return

    if current_user.is_banned:
        emit("error_alert", {"message": "Your account has been suspended"})
        return

    conv_id = data.get("conversation_id")
    raw_content = data.get("content", "").strip()
    parent_id = data.get("parent_id")
    temp_id = data.get("temp_id")
    attachment_ids = data.get("attachment_ids", [])

    if not conv_id or (not raw_content and not attachment_ids):
        emit("error_alert", {"message": "Cannot send an empty message"})
        return

    conv = Conversation.query.get(conv_id)
    if not conv or not conv.is_member(current_user.id):
        emit("error_alert", {"message": "You are not a member of this chat"})
        return

    # 1. Spam evaluation
    spam_result = spam_detector.evaluate(raw_content, user_id=current_user.id)
    if spam_result.is_spam:
        emit(
            "error_alert",
            {
                "message": f"Message blocked by spam filter: {', '.join(spam_result.reasons)}",
                "temp_id": temp_id,
            },
        )
        return

    # 2. Automated content moderation & policy compliance
    mod_verdict = moderator.evaluate(raw_content, user_id=current_user.id)
    if mod_verdict.severity == "critical":
        emit(
            "error_alert",
            {
                "message": f"Message blocked by moderation policy: {'; '.join(mod_verdict.reasons)}",
                "temp_id": temp_id,
            },
        )
        return

    filtered_content = mod_verdict.cleaned_content or raw_content

    # 3. Sentiment analysis
    sentiment = sentiment_analyzer.analyze(filtered_content)

    # 4. Message categorization
    category, _ = categorizer.classify(filtered_content)

    # 5. Persist message record
    msg = Message(
        conversation_id=conv_id,
        sender_id=current_user.id,
        parent_id=parent_id if parent_id else None,
        content=filtered_content,
        message_type="text" if not attachment_ids else "file",
        category=category,
        sentiment_score=sentiment.score,
        sentiment_label=sentiment.label,
        is_spam=False,
        spam_score=spam_result.score,
    )
    db.session.add(msg)
    db.session.flush()

    # If flagged for administrative review, queue in ModerationReport
    if mod_verdict.flagged:
        report = ModerationReport(
            reporter_id=current_user.id,
            message_id=msg.id,
            reason=f"Automated [{mod_verdict.severity.upper()}]: {', '.join(mod_verdict.reasons)}",
            details=mod_verdict.explanation,
            status="pending",
        )
        db.session.add(report)

    # Link any pre-uploaded attachments
    if attachment_ids:
        attachments = Attachment.query.filter(Attachment.id.in_(attachment_ids)).all()
        for att in attachments:
            att.message_id = msg.id

    # Update conversation last activity
    conv.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # Prepare serialized response payload
    msg_dict = msg.to_dict()
    msg_dict["temp_id"] = temp_id

    # Ensure caller socket is in room and broadcast to conversation members
    join_room(f"conv_{conv_id}")
    emit("new_message", msg_dict, to=f"conv_{conv_id}")
    emit("message_confirmed", {"temp_id": temp_id, "message": msg_dict})

    # Emit notification to all conversation participants via their personal rooms
    for p in conv.participants:
        if p.user_id != current_user.id:
            notif = Notification(
                user_id=p.user_id,
                actor_id=current_user.id,
                type="direct_message" if conv.type == "direct" else "group_message",
                title=f"New message from {current_user.full_name or current_user.username}",
                content=filtered_content[:80] if filtered_content else "[Attachment]",
                link_url=f"/c/{conv_id}",
                is_read=False,
            )
            db.session.add(notif)
            emit(
                "message_notification",
                {
                    "conversation_id": conv_id,
                    "sender_name": current_user.full_name or current_user.username,
                    "message_snippet": (
                        filtered_content[:60]
                        if filtered_content
                        else "[Attachment]"
                    ),
                    "created_at": msg.created_at.isoformat(),
                },
                to=f"user_{p.user_id}",
            )
    db.session.commit()


@socketio.on("edit_message")
def handle_edit_message(data):
    """Edit an existing message via WebSocket with author verification."""
    if not current_user.is_authenticated:
        return

    message_id = data.get("message_id")
    new_content = data.get("content", "").strip()
    if not message_id or not new_content:
        emit("error_alert", {"message": "Invalid message edit payload"})
        return

    msg = Message.query.get(message_id)
    if not msg or msg.is_deleted:
        emit("error_alert", {"message": "Message not found or deleted"})
        return

    if msg.sender_id != current_user.id:
        emit("error_alert", {"message": "You can only edit your own messages"})
        return

    filtered_content, _ = processor.filter_profanity(new_content)
    sentiment = sentiment_analyzer.analyze(filtered_content)
    category, _ = categorizer.classify(filtered_content)

    msg.content = filtered_content
    msg.is_edited = True
    msg.sentiment_score = sentiment.score
    msg.sentiment_label = sentiment.label
    msg.category = category
    msg.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    emit("message_edited", msg.to_dict(), to=f"conv_{msg.conversation_id}")


@socketio.on("delete_message")
def handle_delete_message(data):
    """Soft delete message via WebSocket with author or admin authorization."""
    if not current_user.is_authenticated:
        return

    message_id = data.get("message_id")
    if not message_id:
        return

    msg = Message.query.get(message_id)
    if not msg:
        return

    if msg.sender_id != current_user.id and not current_user.is_admin:
        emit("error_alert", {"message": "Permission denied to delete message"})
        return

    msg.is_deleted = True
    db.session.commit()

    emit(
        "message_deleted",
        {"message_id": msg.id, "conversation_id": msg.conversation_id},
        to=f"conv_{msg.conversation_id}",
    )


@socketio.on("typing")
def handle_typing(data):
    """Broadcast typing status indicator to conversation participants."""
    if not current_user.is_authenticated:
        return

    conv_id = data.get("conversation_id")
    is_typing = bool(data.get("is_typing", False))
    if not conv_id:
        return

    socket_state.set_typing(
        current_user.id, conv_id, is_typing, datetime.now(timezone.utc).timestamp()
    )

    emit(
        "user_typing",
        {
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "username": current_user.full_name or current_user.username,
            "is_typing": is_typing,
        },
        to=f"conv_{conv_id}",
        include_self=False,
    )


@socketio.on("read_receipt")
def handle_read_receipt(data):
    """Mark a message as read by the current user."""
    if not current_user.is_authenticated:
        return

    conv_id = data.get("conversation_id")
    message_id = data.get("message_id")
    if not conv_id or not message_id:
        return

    # Check if receipt already exists
    existing = ReadReceipt.query.filter_by(
        message_id=message_id, user_id=current_user.id
    ).first()
    if not existing:
        receipt = ReadReceipt(
            message_id=message_id,
            user_id=current_user.id,
            delivered_at=datetime.now(timezone.utc),
            read_at=datetime.now(timezone.utc),
        )
        db.session.add(receipt)

        # Update participant last_read_message_id
        participant = ConversationParticipant.query.filter_by(
            conversation_id=conv_id, user_id=current_user.id
        ).first()
        if participant and message_id > participant.last_read_message_id:
            participant.last_read_message_id = message_id

        db.session.commit()

        emit(
            "message_read",
            {
                "conversation_id": conv_id,
                "message_id": message_id,
                "user_id": current_user.id,
                "username": current_user.username,
            },
            to=f"conv_{conv_id}",
        )


@socketio.on("add_reaction")
def handle_add_reaction(data):
    """Toggle an emoji reaction on a message."""
    if not current_user.is_authenticated:
        return

    message_id = data.get("message_id")
    reaction_char = data.get("reaction")
    if not message_id or not reaction_char:
        return

    msg = Message.query.get(message_id)
    if not msg:
        return

    # Check if user already placed this exact reaction -> toggle off
    existing = MessageReaction.query.filter_by(
        message_id=message_id, user_id=current_user.id, reaction=reaction_char
    ).first()

    if existing:
        db.session.delete(existing)
    else:
        new_reaction = MessageReaction(
            message_id=message_id, user_id=current_user.id, reaction=reaction_char
        )
        db.session.add(new_reaction)

    db.session.commit()

    # Re-fetch aggregated reactions for message
    updated_msg = Message.query.get(message_id)
    reactions_dict = updated_msg.to_dict()["reactions"]

    emit(
        "reaction_updated",
        {
            "message_id": message_id,
            "conversation_id": msg.conversation_id,
            "reactions": reactions_dict,
        },
        to=f"conv_{msg.conversation_id}",
    )
