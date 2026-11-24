"""
RESTful API Routes Module
=========================
Supplies JSON endpoints powering dynamic chat UI, member management,
message searches, file uploads, summaries, and real-time analytics.
"""

import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.user import User, UserSettings
from app.models.chat import (
    Conversation,
    ConversationParticipant,
    Message,
    Attachment,
    MessageReaction,
    Notification,
)
from app.models.audit import AuditLog, ModerationReport
from app.python_features.summarizer import ConversationSummarizer
from app.python_features.analytics import ChatAnalyticsEngine

api_bp = Blueprint("api", __name__, url_prefix="/api")
summarizer = ConversationSummarizer()


# -----------------------------------------------------------------------------
# CONVERSATION ENDPOINTS
# -----------------------------------------------------------------------------
@api_bp.route("/conversations", methods=["GET"])
@login_required
def get_conversations():
    """Retrieve all active conversations for the authenticated user."""
    participations = (
        ConversationParticipant.query.filter_by(user_id=current_user.id)
        .join(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    conversations_data = []
    for part in participations:
        conv = part.conversation
        # Count unread messages
        unread_count = (
            Message.query.filter(
                Message.conversation_id == conv.id,
                Message.id > part.last_read_message_id,
                Message.sender_id != current_user.id,
                Message.is_deleted == False,
            ).count()
        )

        conv_dict = conv.to_dict(current_user_id=current_user.id)
        conv_dict["unread_count"] = unread_count
        conv_dict["my_role"] = part.role
        conversations_data.append(conv_dict)

    return jsonify({"success": True, "conversations": conversations_data})


@api_bp.route("/conversations", methods=["POST"])
@login_required
def create_conversation():
    """
    Create a new 1-on-1 direct conversation or multi-user group chat.
    """
    data = request.get_json() or {}
    conv_type = data.get("type", "direct")

    if conv_type == "direct":
        recipient_id = data.get("recipient_id")
        if not recipient_id or recipient_id == current_user.id:
            return jsonify({"success": False, "message": "Invalid recipient"}), 400

        recipient = User.query.get(recipient_id)
        if not recipient:
            return jsonify({"success": False, "message": "Recipient not found"}), 404

        # Check for existing direct chat between these two users
        existing_conv = (
            Conversation.query.filter_by(type="direct")
            .filter(Conversation.participants.any(user_id=current_user.id))
            .filter(Conversation.participants.any(user_id=recipient_id))
            .first()
        )
        if existing_conv:
            return jsonify({
                "success": True,
                "conversation": existing_conv.to_dict(current_user_id=current_user.id),
                "already_existed": True,
            })

        # Create new direct conversation
        conv = Conversation(
            type="direct",
            creator_id=current_user.id,
        )
        db.session.add(conv)
        db.session.flush()

        part1 = ConversationParticipant(
            conversation_id=conv.id, user_id=current_user.id, role="member"
        )
        part2 = ConversationParticipant(
            conversation_id=conv.id, user_id=recipient_id, role="member"
        )
        db.session.add_all([part1, part2])
        db.session.commit()

        from app.extensions import socketio
        socketio.emit(
            "conversation_created",
            conv.to_dict(current_user_id=recipient_id),
            to=f"user_{recipient_id}",
        )

        return jsonify({
            "success": True,
            "conversation": conv.to_dict(current_user_id=current_user.id),
        }), 201

    elif conv_type == "group":
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        member_ids = data.get("member_ids", [])

        if not title:
            return jsonify({"success": False, "message": "Group title is required"}), 400

        conv = Conversation(
            type="group",
            title=title,
            description=description,
            creator_id=current_user.id,
            icon="default_group.svg",
        )
        db.session.add(conv)
        db.session.flush()

        # Add creator as group admin
        creator_part = ConversationParticipant(
            conversation_id=conv.id, user_id=current_user.id, role="admin"
        )
        db.session.add(creator_part)

        # Add initial members
        for uid in set(member_ids):
            if uid != current_user.id and User.query.get(uid):
                part = ConversationParticipant(
                    conversation_id=conv.id, user_id=uid, role="member"
                )
                db.session.add(part)

        # Initial system announcement message inside group
        sys_msg = Message(
            conversation_id=conv.id,
            sender_id=None,
            content=f"Group '{title}' created by {current_user.full_name or current_user.username}",
            message_type="system",
            category="announcement",
        )
        db.session.add(sys_msg)

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="GROUP_CREATE",
            target_type="group",
            target_id=conv.id,
            details=f"Created group '{title}' with {len(member_ids) + 1} members",
            ip_address=request.remote_addr,
        )
        db.session.add(audit)
        db.session.commit()

        from app.extensions import socketio
        for uid in set(member_ids):
            socketio.emit(
                "conversation_created",
                conv.to_dict(current_user_id=uid),
                to=f"user_{uid}",
            )

        return jsonify({
            "success": True,
            "conversation": conv.to_dict(current_user_id=current_user.id),
        }), 201

    return jsonify({"success": False, "message": "Unsupported conversation type"}), 400


@api_bp.route("/conversations/<int:conv_id>/messages", methods=["GET"])
@login_required
def get_conversation_messages(conv_id: int):
    """Retrieve paginated messages for a conversation."""
    conv = Conversation.query.get_or_404(conv_id)
    if not conv.is_member(current_user.id) and not current_user.is_admin:
        return jsonify({"success": False, "message": "Access denied"}), 403

    limit = min(int(request.args.get("limit", 50)), 100)
    before_id = request.args.get("before_id", type=int)

    query = Message.query.filter_by(conversation_id=conv_id)
    if before_id:
        query = query.filter(Message.id < before_id)

    # Order descending to get newest first, then reverse to chronological order
    messages = query.order_by(Message.id.desc()).limit(limit).all()
    messages.reverse()

    return jsonify({
        "success": True,
        "conversation": conv.to_dict(current_user_id=current_user.id),
        "messages": [m.to_dict() for m in messages],
        "has_more": len(messages) == limit,
    })


@api_bp.route("/conversations/<int:conv_id>/messages", methods=["POST"])
@login_required
def post_conversation_message(conv_id: int):
    """
    REST API endpoint for sending a message in a conversation.
    Acts as a persistent fallback for real-time WebSockets and provides standard HTTP interface.
    """
    if current_user.is_banned:
        return jsonify({"success": False, "message": "Your account has been suspended"}), 403

    conv = Conversation.query.get_or_404(conv_id)
    if not conv.is_member(current_user.id) and not current_user.is_admin:
        return jsonify({"success": False, "message": "Access denied"}), 403

    data = request.get_json() or {}
    raw_content = (data.get("content") or "").strip()
    parent_id = data.get("parent_id")
    temp_id = data.get("temp_id")
    attachment_ids = data.get("attachment_ids", [])

    if not raw_content and not attachment_ids:
        return jsonify({"success": False, "message": "Message content cannot be empty"}), 400

    from app.python_features.spam_detector import SpamDetector
    from app.python_features.sentiment import SentimentAnalyzer
    from app.python_features.categorizer import MessageCategorizer
    from app.python_features.moderation import ContentModerator

    spam_detector = SpamDetector()
    sentiment_analyzer = SentimentAnalyzer()
    categorizer = MessageCategorizer()
    moderator = ContentModerator()

    # 1. Spam evaluation
    spam_result = spam_detector.evaluate(raw_content, user_id=current_user.id)
    if spam_result.is_spam:
        return jsonify({
            "success": False,
            "message": f"Message blocked by spam filter: {', '.join(spam_result.reasons)}",
            "temp_id": temp_id,
        }), 400

    # 2. Content moderation
    mod_verdict = moderator.evaluate(raw_content, user_id=current_user.id)
    if mod_verdict.severity == "critical":
        return jsonify({
            "success": False,
            "message": f"Message blocked by moderation policy: {'; '.join(mod_verdict.reasons)}",
            "temp_id": temp_id,
        }), 400

    filtered_content = mod_verdict.cleaned_content or raw_content
    sentiment = sentiment_analyzer.analyze(filtered_content)
    category, _ = categorizer.classify(filtered_content)

    msg = Message(
        conversation_id=conv.id,
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

    if mod_verdict.flagged:
        report = ModerationReport(
            reporter_id=current_user.id,
            message_id=msg.id,
            reason=f"Automated [{mod_verdict.severity.upper()}]: {', '.join(mod_verdict.reasons)}",
            details=mod_verdict.explanation,
            status="pending",
        )
        db.session.add(report)

    if attachment_ids:
        attachments = Attachment.query.filter(Attachment.id.in_(attachment_ids)).all()
        for att in attachments:
            att.message_id = msg.id

    conv.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    msg_dict = msg.to_dict()
    msg_dict["temp_id"] = temp_id

    # Broadcast to active room members
    from app.extensions import socketio
    socketio.emit("new_message", msg_dict, to=f"conv_{conv.id}")

    # Emit notification to all conversation participants via personal rooms
    for p in conv.participants:
        if p.user_id != current_user.id:
            notif = Notification(
                user_id=p.user_id,
                actor_id=current_user.id,
                type="direct_message" if conv.type == "direct" else "group_message",
                title=f"New message from {current_user.full_name or current_user.username}",
                content=filtered_content[:80] if filtered_content else "[Attachment]",
                link_url=f"/c/{conv.id}",
                is_read=False,
            )
            db.session.add(notif)
            socketio.emit(
                "message_notification",
                {
                    "conversation_id": conv.id,
                    "sender_name": current_user.full_name or current_user.username,
                    "message_snippet": filtered_content[:60] if filtered_content else "[Attachment]",
                    "created_at": msg.created_at.isoformat(),
                },
                to=f"user_{p.user_id}",
            )
    db.session.commit()

    return jsonify({"success": True, "message": msg_dict}), 201


# -----------------------------------------------------------------------------
# GROUP MEMBERSHIP MANAGEMENT
# -----------------------------------------------------------------------------
@api_bp.route("/conversations/<int:conv_id>/participants", methods=["POST"])
@login_required
def add_participant(conv_id: int):
    """Add a member to a group conversation."""
    conv = Conversation.query.get_or_404(conv_id)
    if conv.type != "group":
        return jsonify({"success": False, "message": "Only groups have dynamic participants"}), 400

    user_role = conv.get_participant_role(current_user.id)
    if user_role not in ("admin", "moderator") and not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin privileges required"}), 403

    data = request.get_json() or {}
    new_user_id = data.get("user_id")
    target_user = User.query.get(new_user_id)
    if not target_user:
        return jsonify({"success": False, "message": "User not found"}), 404

    if conv.is_member(new_user_id):
        return jsonify({"success": False, "message": "User is already a member"}), 400

    new_part = ConversationParticipant(
        conversation_id=conv.id, user_id=new_user_id, role="member"
    )
    db.session.add(new_part)

    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=None,
        content=f"{target_user.full_name or target_user.username} was added to the group",
        message_type="system",
        category="announcement",
    )
    db.session.add(sys_msg)
    db.session.commit()

    from app.extensions import socketio
    socketio.emit("new_message", sys_msg.to_dict(), to=f"conv_{conv.id}")
    socketio.emit("conversation_updated", conv.to_dict(current_user_id=current_user.id), to=f"conv_{conv.id}")

    return jsonify({"success": True, "message": "Member added successfully"})


@api_bp.route("/conversations/<int:conv_id>/participants/<int:target_user_id>", methods=["DELETE"])
@login_required
def remove_participant(conv_id: int, target_user_id: int):
    """Remove a member or leave a group."""
    conv = Conversation.query.get_or_404(conv_id)
    if conv.type != "group":
        return jsonify({"success": False, "message": "Invalid operation on direct chat"}), 400

    current_role = conv.get_participant_role(current_user.id)
    is_self_leaving = target_user_id == current_user.id

    if not is_self_leaving and current_role not in ("admin", "moderator") and not current_user.is_admin:
        return jsonify({"success": False, "message": "Permission denied"}), 403

    participant = ConversationParticipant.query.filter_by(
        conversation_id=conv.id, user_id=target_user_id
    ).first()
    if not participant:
        return jsonify({"success": False, "message": "Member not in group"}), 404

    db.session.delete(participant)

    target_user = User.query.get(target_user_id)
    name = (
        target_user.full_name or target_user.username
        if target_user
        else "A member"
    )
    action_text = "left the group" if is_self_leaving else "was removed from the group"

    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=None,
        content=f"{name} {action_text}",
        message_type="system",
        category="announcement",
    )
    db.session.add(sys_msg)
    db.session.commit()

    from app.extensions import socketio
    socketio.emit("new_message", sys_msg.to_dict(), to=f"conv_{conv.id}")
    socketio.emit("conversation_updated", conv.to_dict(current_user_id=current_user.id), to=f"conv_{conv.id}")

    return jsonify({"success": True, "message": "Member removed successfully"})


@api_bp.route("/conversations/<int:conv_id>", methods=["PATCH", "PUT"])
@api_bp.route("/conversations/<int:conv_id>/rename", methods=["POST"])
@login_required
def update_conversation(conv_id: int):
    """Rename or update group channel metadata."""
    conv = Conversation.query.get_or_404(conv_id)
    if conv.type != "group":
        return jsonify({"success": False, "message": "Only group conversations can be updated"}), 400

    user_role = conv.get_participant_role(current_user.id)
    if user_role not in ("admin", "moderator") and not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin privileges required"}), 403

    data = request.get_json() or {}
    new_title = data.get("title", "").strip()
    new_desc = data.get("description")

    if not new_title:
        return jsonify({"success": False, "message": "Group title cannot be empty"}), 400

    old_title = conv.title
    conv.title = new_title
    if new_desc is not None:
        conv.description = new_desc.strip()

    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=None,
        content=f"{current_user.full_name or current_user.username} renamed group '{old_title}' to '{new_title}'",
        message_type="system",
        category="announcement",
    )
    db.session.add(sys_msg)

    audit = AuditLog(
        user_id=current_user.id,
        action="GROUP_RENAME",
        target_type="group",
        target_id=conv.id,
        details=f"Renamed group from '{old_title}' to '{new_title}'",
        ip_address=request.remote_addr,
    )
    db.session.add(audit)
    db.session.commit()

    from app.extensions import socketio
    socketio.emit("conversation_updated", conv.to_dict(current_user_id=current_user.id), to=f"conv_{conv.id}")
    socketio.emit("new_message", sys_msg.to_dict(), to=f"conv_{conv.id}")

    return jsonify({
        "success": True,
        "message": f"Group renamed to '{new_title}'",
        "conversation": conv.to_dict(current_user_id=current_user.id),
    })


# -----------------------------------------------------------------------------
# PYTHON ACADEMIC FEATURES: SUMMARIZATION & ANALYTICS
# -----------------------------------------------------------------------------
@api_bp.route("/conversations/<int:conv_id>/summarize", methods=["POST"])
@login_required
def summarize_conversation(conv_id: int):
    """
    Trigger pure Python extractive summarizer on conversation messages.
    """
    conv = Conversation.query.get_or_404(conv_id)
    if not conv.is_member(current_user.id) and not current_user.is_admin:
        return jsonify({"success": False, "message": "Access denied"}), 403

    # Fetch last 100 messages
    messages = (
        Message.query.filter_by(conversation_id=conv_id)
        .order_by(Message.id.desc())
        .limit(100)
        .all()
    )
    messages.reverse()

    serialized = [m.to_dict() for m in messages]
    summary_data = summarizer.summarize(serialized)

    return jsonify({"success": True, "summary": summary_data})


@api_bp.route("/conversations/<int:conv_id>/analytics", methods=["GET"])
@login_required
def get_conversation_analytics(conv_id: int):
    """
    Compute pure Python chat analytics and metrics for conversation.
    """
    conv = Conversation.query.get_or_404(conv_id)
    if not conv.is_member(current_user.id) and not current_user.is_admin:
        return jsonify({"success": False, "message": "Access denied"}), 403

    messages = (
        Message.query.filter_by(conversation_id=conv_id)
        .order_by(Message.id.asc())
        .limit(300)
        .all()
    )

    serialized = [m.to_dict() for m in messages]
    metrics = ChatAnalyticsEngine.compute_analytics(serialized)

    return jsonify({"success": True, "analytics": metrics})


@api_bp.route("/analytics/overview", methods=["GET"])
@login_required
def get_global_analytics():
    """
    Compute system-wide pure Python chat analytics:
    total messages, daily trend, active users, most active groups, conversation activity,
    and category distribution.
    """
    all_msgs = Message.query.filter_by(is_deleted=False).limit(1000).all()
    serialized = [m.to_dict() for m in all_msgs]

    all_convs = Conversation.query.all()
    conv_meta = [
        {
            "id": c.id,
            "type": c.type,
            "title": c.title,
            "participant_count": len(c.participants),
        }
        for c in all_convs
    ]

    metrics = ChatAnalyticsEngine.compute_analytics(
        serialized, conversations_metadata=conv_meta
    )
    return jsonify({"success": True, "analytics": metrics})


# -----------------------------------------------------------------------------
# FILE AND IMAGE ATTACHMENT UPLOAD
# -----------------------------------------------------------------------------
@api_bp.route("/upload", methods=["POST"])
@login_required
def upload_file():
    """
    Secure file upload endpoint for chat attachments.
    Demonstrates file handling, validation of extensions, and UUID naming.
    """
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return jsonify({
            "success": False,
            "message": f"File type '.{ext}' is not permitted.",
        }), 400

    # Categorize file type
    if ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        file_category = "image"
    elif ext in current_app.config["ALLOWED_AUDIO_EXTENSIONS"]:
        file_category = "audio"
    else:
        file_category = "document"

    unique_filename = f"attach_{current_user.id}_{uuid.uuid4().hex[:10]}.{ext}"
    os.makedirs(current_app.config["ATTACHMENT_FOLDER"], exist_ok=True)
    save_path = os.path.join(current_app.config["ATTACHMENT_FOLDER"], unique_filename)
    file.save(save_path)

    file_size = os.path.getsize(save_path)
    file_url = f"/static/uploads/attachments/{unique_filename}"

    # Create unattached Attachment record (attached on message send)
    attachment = Attachment(
        message_id=0,  # Will be updated when message is created
        filename=unique_filename,
        original_filename=filename,
        file_type=file_category,
        mime_type=file.mimetype or "application/octet-stream",
        file_size=file_size,
        file_url=file_url,
    )
    db.session.add(attachment)
    db.session.commit()

    return jsonify({
        "success": True,
        "attachment": attachment.to_dict(),
    }), 201


# -----------------------------------------------------------------------------
# SEARCH & MODERATION
# -----------------------------------------------------------------------------
@api_bp.route("/messages/search", methods=["GET"])
@login_required
def search_messages():
    """Search messages across all conversations the user belongs to."""
    query_text = request.args.get("q", "").strip()
    category = request.args.get("category")
    sentiment = request.args.get("sentiment")

    if not query_text and not category and not sentiment:
        return jsonify({"success": True, "results": []})

    # Get conversation IDs user is participant of
    user_conv_ids = [
        p.conversation_id
        for p in ConversationParticipant.query.filter_by(user_id=current_user.id).all()
    ]

    stmt = Message.query.filter(
        Message.conversation_id.in_(user_conv_ids),
        Message.is_deleted == False,
    )

    if query_text:
        stmt = stmt.filter(Message.content.ilike(f"%{query_text}%"))
    if category:
        stmt = stmt.filter_by(category=category)
    if sentiment:
        stmt = stmt.filter_by(sentiment_label=sentiment)

    results = stmt.order_by(Message.id.desc()).limit(50).all()

    return jsonify({
        "success": True,
        "results": [m.to_dict() for m in results],
    })


@api_bp.route("/users/search", methods=["GET"])
@login_required
def search_users():
    """Search registered users by username or full name."""
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify({"success": True, "users": []})

    users = (
        User.query.filter(
            User.id != current_user.id,
            User.is_banned == False,
            (User.username.ilike(f"%{q}%")) | (User.full_name.ilike(f"%{q}%")),
        )
        .limit(20)
        .all()
    )

    return jsonify({
        "success": True,
        "users": [u.to_dict() for u in users],
    })


@api_bp.route("/messages/<int:msg_id>", methods=["PUT"])
@login_required
def edit_message(msg_id: int):
    """Edit message content. Only the author can edit their own message."""
    msg = Message.query.get_or_404(msg_id)
    if msg.sender_id != current_user.id:
        return jsonify({"success": False, "message": "Only the author can edit their message"}), 403

    if msg.is_deleted:
        return jsonify({"success": False, "message": "Cannot edit a deleted message"}), 400

    data = request.get_json() or {}
    new_content = data.get("content", "").strip()
    if not new_content:
        return jsonify({"success": False, "message": "Message content cannot be empty"}), 400

    from app.python_features.processor import MessageProcessor
    from app.python_features.sentiment import SentimentAnalyzer
    from app.python_features.categorizer import MessageCategorizer

    processor = MessageProcessor()
    sentiment_analyzer = SentimentAnalyzer()
    categorizer = MessageCategorizer()

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

    from app.extensions import socketio
    socketio.emit(
        "message_edited",
        msg.to_dict(),
        to=f"conv_{msg.conversation_id}",
    )

    return jsonify({"success": True, "message": msg.to_dict()})


@api_bp.route("/messages/<int:msg_id>", methods=["DELETE"])
@login_required
def delete_message(msg_id: int):
    """Soft delete message."""
    msg = Message.query.get_or_404(msg_id)
    is_sender = msg.sender_id == current_user.id
    is_admin = current_user.is_admin

    if not is_sender and not is_admin:
        return jsonify({"success": False, "message": "Permission denied"}), 403

    msg.is_deleted = True
    db.session.commit()

    from app.extensions import socketio
    socketio.emit(
        "message_deleted",
        {"message_id": msg.id, "conversation_id": msg.conversation_id},
        to=f"conv_{msg.conversation_id}",
    )

    return jsonify({"success": True, "message": "Message deleted"})


@api_bp.route("/messages/<int:msg_id>/report", methods=["POST"])
@login_required
def report_message(msg_id: int):
    """Submit a moderation report for a message."""
    data = request.get_json() or {}
    reason = data.get("reason", "spam")
    details = data.get("details", "")

    msg = Message.query.get_or_404(msg_id)
    report = ModerationReport(
        reporter_id=current_user.id,
        message_id=msg.id,
        reason=reason,
        details=details,
        status="pending",
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({"success": True, "message": "Report submitted for moderation"})


# -----------------------------------------------------------------------------
# NOTIFICATIONS & USER PREFERENCES
# -----------------------------------------------------------------------------
@api_bp.route("/notifications", methods=["GET"])
@login_required
def get_notifications():
    """Retrieve user notifications list and unread count."""
    notifs = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(25)
        .all()
    )
    unread_count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()

    return jsonify({
        "success": True,
        "unread_count": unread_count,
        "notifications": [n.to_dict() for n in notifs],
    })


@api_bp.route("/notifications/read", methods=["POST"])
@login_required
def mark_notifications_read():
    """Mark all or a specific notification as read."""
    data = request.get_json() or {}
    notif_id = data.get("notification_id")

    if notif_id:
        notif = Notification.query.filter_by(
            id=notif_id, user_id=current_user.id
        ).first()
        if notif:
            notif.is_read = True
    else:
        Notification.query.filter_by(
            user_id=current_user.id, is_read=False
        ).update({"is_read": True})

    db.session.commit()
    return jsonify({"success": True, "message": "Notifications updated"})


@api_bp.route("/users/settings", methods=["POST"])
@login_required
def update_user_settings():
    """Update user preferences dynamically (theme, sound, notifications, enter_is_send)."""
    data = request.get_json() or {}
    settings = current_user.get_or_create_settings()

    if "theme" in data and data["theme"] in ("light", "dark"):
        settings.theme = data["theme"]
    if "sound_enabled" in data:
        settings.sound_enabled = bool(data["sound_enabled"])
    if "desktop_notifications" in data:
        settings.desktop_notifications = bool(data["desktop_notifications"])
    if "enter_is_send" in data:
        settings.enter_is_send = bool(data["enter_is_send"])

    db.session.commit()
    return jsonify({
        "success": True,
        "settings": {
            "theme": settings.theme,
            "sound_enabled": settings.sound_enabled,
            "desktop_notifications": settings.desktop_notifications,
            "enter_is_send": settings.enter_is_send,
        },
    })


@api_bp.route("/users/online", methods=["GET"])
@login_required
def get_online_users():
    """Retrieve list of currently online contacts for sidebar quick-chat."""
    users = (
        User.query.filter(
            User.id != current_user.id,
            User.is_online == True,
            User.is_banned == False,
        )
        .order_by(User.username.asc())
        .limit(20)
        .all()
    )

    online_list = []
    for u in users:
        conv = (
            Conversation.query.filter_by(type="direct")
            .filter(Conversation.participants.any(user_id=current_user.id))
            .filter(Conversation.participants.any(user_id=u.id))
            .first()
        )
        online_list.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name or u.username,
            "avatar": u.avatar,
            "status_message": u.status_message or "Active now",
            "conversation_id": conv.id if conv else None,
        })

    return jsonify({"success": True, "users": online_list})

