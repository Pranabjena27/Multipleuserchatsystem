"""
Group Channel Routes Module
===========================
Handles multi-user group creation, membership management, and administrative channel controls.
"""

from flask import Blueprint, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.chat import Conversation, ConversationParticipant, Message
from app.models.audit import AuditLog

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


@groups_bp.route("/create", methods=["POST"])
@login_required
def create_group():
    """Create a new group channel."""
    title = request.form.get("title", "").strip() or request.json.get("title", "").strip() if request.is_json else request.form.get("title", "").strip()
    description = request.form.get("description", "").strip() if not request.is_json else request.json.get("description", "").strip()

    if not title:
        if request.is_json:
            return jsonify({"success": False, "message": "Group title is required"}), 400
        flash("Group title is required.", "danger")
        return redirect(url_for("chat.index"))

    conv = Conversation(
        type="group",
        title=title,
        description=description,
        creator_id=current_user.id,
        icon="default_group.svg",
    )
    db.session.add(conv)
    db.session.flush()

    # Add creator as group administrator
    creator_part = ConversationParticipant(
        conversation_id=conv.id,
        user_id=current_user.id,
        role="admin",
    )
    db.session.add(creator_part)

    # Inject system announcement into the group channel
    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=None,
        content=f"Channel '{title}' created by {current_user.full_name or current_user.username}",
        message_type="system",
        category="announcement",
    )
    db.session.add(sys_msg)

    # Log administrative audit entry
    audit = AuditLog(
        user_id=current_user.id,
        action="GROUP_CREATE",
        target_type="group",
        target_id=conv.id,
        details=f"Created group '{title}'",
        ip_address=request.remote_addr,
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({
            "success": True,
            "conversation": conv.to_dict(current_user_id=current_user.id),
        }), 201

    flash(f"Group '{title}' created successfully!", "success")
    return redirect(url_for("chat.open_conversation", conversation_id=conv.id))


@groups_bp.route("/<int:conv_id>/leave", methods=["POST"])
@login_required
def leave_group(conv_id: int):
    """Leave a group conversation."""
    conv = Conversation.query.get_or_404(conv_id)
    if conv.type != "group":
        flash("Invalid operation for direct chats.", "danger")
        return redirect(url_for("chat.index"))

    membership = ConversationParticipant.query.filter_by(
        conversation_id=conv.id, user_id=current_user.id
    ).first()

    if not membership:
        flash("You are not a member of this group.", "warning")
        return redirect(url_for("chat.index"))

    db.session.delete(membership)

    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=None,
        content=f"{current_user.full_name or current_user.username} has left the group",
        message_type="system",
        category="announcement",
    )
    db.session.add(sys_msg)
    db.session.commit()

    from app.extensions import socketio
    socketio.emit(
        "new_message",
        sys_msg.to_dict(),
        to=f"conv_{conv.id}",
    )

    if request.is_json:
        return jsonify({"success": True, "message": "Left the group successfully"})

    flash("You have left the group.", "info")
    return redirect(url_for("chat.index"))


@groups_bp.route("/<int:conv_id>/rename", methods=["POST"])
@login_required
def rename_group(conv_id: int):
    """Rename a group channel."""
    conv = Conversation.query.get_or_404(conv_id)
    if conv.type != "group":
        if request.is_json:
            return jsonify({"success": False, "message": "Only groups can be renamed"}), 400
        flash("Only groups can be renamed.", "danger")
        return redirect(url_for("chat.index"))

    user_role = conv.get_participant_role(current_user.id)
    if user_role not in ("admin", "moderator") and not current_user.is_admin:
        if request.is_json:
            return jsonify({"success": False, "message": "Admin privileges required to rename group"}), 403
        flash("Admin privileges required to rename this group.", "danger")
        return redirect(url_for("chat.open_conversation", conversation_id=conv.id))

    data = request.get_json() if request.is_json else request.form
    new_title = (data.get("title") or "").strip()
    new_desc = data.get("description")

    if not new_title:
        if request.is_json:
            return jsonify({"success": False, "message": "Group title cannot be empty"}), 400
        flash("Group title cannot be empty.", "warning")
        return redirect(url_for("chat.open_conversation", conversation_id=conv.id))

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
    socketio.emit(
        "conversation_updated",
        conv.to_dict(current_user_id=current_user.id),
        to=f"conv_{conv.id}",
    )
    socketio.emit(
        "new_message",
        sys_msg.to_dict(),
        to=f"conv_{conv.id}",
    )

    if request.is_json:
        return jsonify({
            "success": True,
            "message": f"Group renamed to '{new_title}'",
            "conversation": conv.to_dict(current_user_id=current_user.id),
        })

    flash(f"Group renamed to '{new_title}'.", "success")
    return redirect(url_for("chat.open_conversation", conversation_id=conv.id))


@groups_bp.route("/<int:conv_id>/members/add", methods=["POST"])
@login_required
def add_member(conv_id: int):
    """Add a member to group via form POST."""
    conv = Conversation.query.get_or_404(conv_id)
    if conv.type != "group":
        flash("Invalid operation for direct chats.", "danger")
        return redirect(url_for("chat.index"))

    user_role = conv.get_participant_role(current_user.id)
    if user_role not in ("admin", "moderator") and not current_user.is_admin:
        flash("Admin privileges required to add members.", "danger")
        return redirect(url_for("chat.open_conversation", conversation_id=conv.id))

    user_id = request.form.get("user_id", type=int)
    target_user = User.query.get(user_id) if user_id else None
    if not target_user:
        flash("User not found.", "danger")
        return redirect(url_for("chat.open_conversation", conversation_id=conv.id))

    if conv.is_member(target_user.id):
        flash(f"{target_user.username} is already in the group.", "warning")
        return redirect(url_for("chat.open_conversation", conversation_id=conv.id))

    new_part = ConversationParticipant(
        conversation_id=conv.id, user_id=target_user.id, role="member"
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

    flash(f"{target_user.username} added successfully.", "success")
    return redirect(url_for("chat.open_conversation", conversation_id=conv.id))


@groups_bp.route("/<int:conv_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(conv_id: int, user_id: int):
    """Remove a member from group via form POST."""
    conv = Conversation.query.get_or_404(conv_id)
    if conv.type != "group":
        flash("Invalid operation for direct chats.", "danger")
        return redirect(url_for("chat.index"))

    user_role = conv.get_participant_role(current_user.id)
    if user_role not in ("admin", "moderator") and not current_user.is_admin:
        flash("Admin privileges required to remove members.", "danger")
        return redirect(url_for("chat.open_conversation", conversation_id=conv.id))

    part = ConversationParticipant.query.filter_by(
        conversation_id=conv.id, user_id=user_id
    ).first()
    if not part:
        flash("User is not in the group.", "warning")
        return redirect(url_for("chat.open_conversation", conversation_id=conv.id))

    target_user = User.query.get(user_id)
    db.session.delete(part)

    sys_msg = Message(
        conversation_id=conv.id,
        sender_id=None,
        content=f"{target_user.full_name or target_user.username if target_user else 'A member'} was removed from the group",
        message_type="system",
        category="announcement",
    )
    db.session.add(sys_msg)
    db.session.commit()

    from app.extensions import socketio
    socketio.emit("new_message", sys_msg.to_dict(), to=f"conv_{conv.id}")

    flash("Member removed.", "info")
    return redirect(url_for("chat.open_conversation", conversation_id=conv.id))


