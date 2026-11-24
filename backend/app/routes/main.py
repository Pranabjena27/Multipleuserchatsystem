"""
Main and Health Check Routes Module
===================================
Provides landing view, user dashboard redirect, and system health status endpoint.
"""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text
from app.extensions import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/health", methods=["GET"])
def health_check():
    """
    System Health-Check Route.
    Verifies application responsiveness, database connectivity, and environment metadata.
    """
    db_status = "connected"
    try:
        # Perform lightweight database query to confirm live connection
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "ConnectX Real-Time Chat Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "environment": "active",
        "version": "1.0.0",
    }), (200 if db_status == "connected" else 503)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """
    User Dashboard Route.
    Directs authenticated users to their conversation workstation or profile.
    """
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("chat.index"))

