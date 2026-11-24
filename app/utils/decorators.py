"""
Utility Decorators Module
=========================
Role-based authorization and validation decorators.
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """Ensure current authenticated user possesses administrator role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Administrator privileges required.", "danger")
            return redirect(url_for("chat.index"))
        return f(*args, **kwargs)
    return decorated_function


def moderator_required(f):
    """Ensure current authenticated user possesses moderator or administrator role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_moderator:
            flash("Moderator privileges required.", "danger")
            return redirect(url_for("chat.index"))
        return f(*args, **kwargs)
    return decorated_function
