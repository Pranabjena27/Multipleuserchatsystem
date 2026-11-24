"""
Admin and Moderation Blueprint Module
=====================================
Provides administrative oversight, user moderation, report resolution,
audit log inspection, and global system announcement broadcasting.
"""

from functools import wraps
from datetime import datetime, timezone
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.chat import Conversation, Message
from app.models.audit import AuditLog, ModerationReport, SystemAnnouncement

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator ensuring that current_user has administrator role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Administrator privileges required.", "danger")
            return redirect(url_for("chat.index"))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    """Admin dashboard overview with key platform metrics."""
    total_users = User.query.count()
    banned_users = User.query.filter_by(is_banned=True).count()
    total_conversations = Conversation.query.count()
    total_messages = Message.query.count()
    spam_messages = Message.query.filter_by(is_spam=True).count()
    pending_reports = ModerationReport.query.filter_by(status="pending").count()

    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        banned_users=banned_users,
        total_conversations=total_conversations,
        total_messages=total_messages,
        spam_messages=spam_messages,
        pending_reports=pending_reports,
        recent_users=recent_users,
        recent_logs=recent_logs,
    )


@admin_bp.route("/users")
@login_required
@admin_required
def users_list():
    """List and manage all registered users."""
    search_q = request.args.get("q", "").strip()
    query = User.query

    if search_q:
        query = query.filter(
            (User.username.ilike(f"%{search_q}%"))
            | (User.email.ilike(f"%{search_q}%"))
            | (User.full_name.ilike(f"%{search_q}%"))
        )

    users = query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", users=users, search_q=search_q)


@admin_bp.route("/users/<int:user_id>/toggle-ban", methods=["POST"])
@login_required
@admin_required
def toggle_ban_user(user_id: int):
    """Suspend or restore a user account."""
    if user_id == current_user.id:
        flash("You cannot ban your own administrative account.", "warning")
        return redirect(url_for("admin.users_list"))

    user = User.query.get_or_404(user_id)
    user.is_banned = not user.is_banned
    action_name = "USER_BAN" if user.is_banned else "USER_UNBAN"

    audit = AuditLog(
        user_id=current_user.id,
        action=action_name,
        target_type="user",
        target_id=user.id,
        details=f"Admin {current_user.username} changed ban status of {user.username} to {user.is_banned}",
        ip_address=request.remote_addr,
    )
    db.session.add(audit)
    db.session.commit()

    flash(
        f"User '{user.username}' has been {'suspended' if user.is_banned else 'reactivated'}.",
        "success",
    )
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/set-role", methods=["POST"])
@login_required
@admin_required
def set_user_role(user_id: int):
    """Change role of a user account (admin, moderator, user)."""
    new_role = request.form.get("role")
    if new_role not in ("admin", "moderator", "user"):
        flash("Invalid role selection.", "danger")
        return redirect(url_for("admin.users_list"))

    user = User.query.get_or_404(user_id)
    user.role = new_role
    db.session.commit()

    flash(f"Updated role for {user.username} to {new_role}.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/reports")
@login_required
@admin_required
def reports_list():
    """List moderation reports submitted by users."""
    reports = ModerationReport.query.order_by(ModerationReport.created_at.desc()).all()
    return render_template("admin/reports.html", reports=reports)


@admin_bp.route("/reports/<int:report_id>/resolve", methods=["POST"])
@login_required
@admin_required
def resolve_report(report_id: int):
    """Resolve or dismiss a moderation report."""
    report = ModerationReport.query.get_or_404(report_id)
    action = request.form.get("action", "resolved")
    delete_message_flag = request.form.get("delete_message") == "1"
    admin_note = request.form.get("admin_note", "").strip()

    report.status = action
    report.resolved_at = datetime.now(timezone.utc)
    if admin_note:
        report.details = (
            f"{report.details or ''}\n[Admin Review by @{current_user.username}]: {admin_note}".strip()
        )

    if delete_message_flag and report.message:
        report.message.is_deleted = True

    audit = AuditLog(
        user_id=current_user.id,
        action="REPORT_RESOLVE",
        target_type="report",
        target_id=report.id,
        details=(
            f"Admin {current_user.username} marked report {report.id} as {action}. "
            f"Deleted: {delete_message_flag}. Note: {admin_note or 'None provided'}"
        ),
        ip_address=request.remote_addr,
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Report #{report.id} marked as {action}.", "success")
    return redirect(url_for("admin.reports_list"))


@admin_bp.route("/announcements", methods=["GET", "POST"])
@login_required
@admin_required
def announcements():
    """Create and manage global system announcements."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        priority = request.form.get("priority", "info")

        if title and content:
            announcement = SystemAnnouncement(
                title=title,
                content=content,
                priority=priority,
                created_by_id=current_user.id,
            )
            db.session.add(announcement)
            db.session.commit()
            flash("System announcement published!", "success")
            return redirect(url_for("admin.announcements"))

    all_announcements = (
        SystemAnnouncement.query.order_by(SystemAnnouncement.created_at.desc()).all()
    )
    return render_template("admin/announcements.html", announcements=all_announcements)


@admin_bp.route("/announcements/<int:ann_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_announcement(ann_id: int):
    """Toggle announcement visibility."""
    ann = SystemAnnouncement.query.get_or_404(ann_id)
    ann.is_active = not ann.is_active
    db.session.commit()
    flash(
        f"Announcement is now {'active' if ann.is_active else 'archived'}.",
        "info",
    )
    return redirect(url_for("admin.announcements"))


@admin_bp.route("/audit-logs")
@login_required
@admin_required
def audit_logs():
    """View system audit logs."""
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template("admin/audit_logs.html", logs=logs)

