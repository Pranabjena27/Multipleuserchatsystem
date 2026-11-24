"""
Authentication and Profile Routes Module
========================================
Handles user registration, login sessions, logout, profile updates, and avatar uploads.
"""

import os
import uuid
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db, login_manager
from app.models.user import User, UserSettings
from app.models.audit import AuditLog
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.blueprints.auth.forms import (
    RegistrationForm,
    LoginForm,
    ProfileForm,
    ChangePasswordForm,
    ForgotPasswordForm,
    ResetPasswordForm,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Flask-Login callback to reload user object from session user_id."""
    return User.query.get(int(user_id))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user account with duplicate prevention and validation."""
    if current_user.is_authenticated:
        return redirect(url_for("chat.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip().lower(),
            email=form.email.data.strip().lower(),
            full_name=form.full_name.data.strip(),
            avatar="default_avatar.svg",
            role="user",
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()

        # Initialize default settings
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)

        # Log system audit event
        audit = AuditLog(
            user_id=user.id,
            action="USER_REGISTER",
            target_type="user",
            target_id=user.id,
            details=f"User {user.username} registered account successfully",
            ip_address=request.remote_addr,
        )
        db.session.add(audit)
        db.session.commit()

        flash("Your account has been created! You may now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate and log in an existing user via username or email."""
    if current_user.is_authenticated:
        return redirect(url_for("chat.index"))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.login_identifier.data.strip().lower()
        password = form.password.data

        # Allow sign in via either username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(password):
            if user.is_banned:
                flash("This account has been suspended by an administrator.", "danger")
                return render_template("auth/login.html", form=form)

            login_user(user, remember=form.remember.data)
            user.update_presence(True)

            audit = AuditLog(
                user_id=user.id,
                action="USER_LOGIN",
                target_type="user",
                target_id=user.id,
                details=f"User {user.username} logged in",
                ip_address=request.remote_addr,
            )
            db.session.add(audit)
            db.session.commit()

            flash(f"Welcome back, {user.full_name or user.username}!", "success")
            next_page = request.args.get("next")
            # Guard against invalid next parameter or literal 'None' string
            if not next_page or next_page.strip().lower() in ("none", "null", ""):
                next_page = url_for("chat.index")
            elif not next_page.startswith("/") or next_page.startswith("//"):
                next_page = url_for("chat.index")
            return redirect(next_page)
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """End active user session and update presence status."""
    user = current_user
    if user:
        user.update_presence(False)
        audit = AuditLog(
            user_id=user.id,
            action="USER_LOGOUT",
            target_type="user",
            target_id=user.id,
            details=f"User {user.username} signed out",
            ip_address=request.remote_addr,
        )
        db.session.add(audit)
        db.session.commit()

    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and update profile information, avatar, and account settings."""
    user_settings = current_user.get_or_create_settings()
    profile_form = ProfileForm(
        obj=current_user,
        theme=user_settings.theme,
        sound_enabled=user_settings.sound_enabled,
        desktop_notifications=user_settings.desktop_notifications,
        enter_is_send=user_settings.enter_is_send,
    )
    password_form = ChangePasswordForm()

    if "submit_profile" in request.form and profile_form.validate_on_submit():
        current_user.full_name = profile_form.full_name.data.strip()
        current_user.bio = profile_form.bio.data.strip()
        current_user.status_message = profile_form.status_message.data.strip()

        # Update Account Settings
        user_settings.theme = profile_form.theme.data
        user_settings.sound_enabled = profile_form.sound_enabled.data
        user_settings.desktop_notifications = profile_form.desktop_notifications.data
        user_settings.enter_is_send = profile_form.enter_is_send.data

        # Handle avatar file upload (only if a valid image was submitted)
        avatar_file = profile_form.avatar.data
        if avatar_file and hasattr(avatar_file, "filename") and avatar_file.filename:
            file = avatar_file
            filename = secure_filename(file.filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
                unique_filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                os.makedirs(current_app.config["AVATAR_FOLDER"], exist_ok=True)
                save_path = os.path.join(current_app.config["AVATAR_FOLDER"], unique_filename)
                file.save(save_path)
                current_user.avatar = unique_filename

        db.session.commit()
        flash("Profile and preferences updated successfully!", "success")
        return redirect(url_for("auth.profile"))

    if "submit_password" in request.form and password_form.validate_on_submit():
        if not current_user.check_password(password_form.old_password.data):
            flash("Current password was incorrect.", "danger")
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Your password has been changed successfully!", "success")
            return redirect(url_for("auth.profile"))

    return render_template(
        "auth/profile.html",
        profile_form=profile_form,
        password_form=password_form,
        user=current_user,
        settings=user_settings,
    )


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Self-service password reset request."""
    if current_user.is_authenticated:
        return redirect(url_for("chat.index"))

    form = ForgotPasswordForm()
    reset_url = None

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
            token = serializer.dumps(user.email, salt="connectx-password-reset")
            reset_url = url_for("auth.reset_password", token=token, _external=True)

            flash(
                "A password reset link has been generated! For local/offline testing, use the button below.",
                "success",
            )
        else:
            flash(
                "If an account is associated with this email address, a password recovery link has been prepared.",
                "info",
            )

    return render_template("auth/forgot_password.html", form=form, reset_url=reset_url)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    """Set new password using secure timed serializer token."""
    if current_user.is_authenticated:
        return redirect(url_for("chat.index"))

    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token, salt="connectx-password-reset", max_age=1800)
    except SignatureExpired:
        flash("The password reset link has expired. Please request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash("Invalid or corrupted password reset token.", "danger")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User associated with this token was not found.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)

        audit = AuditLog(
            user_id=user.id,
            action="PASSWORD_RESET",
            target_type="user",
            target_id=user.id,
            details=f"User {user.username} successfully reset password via security token",
            ip_address=request.remote_addr,
        )
        db.session.add(audit)
        db.session.commit()

        flash("Your password has been successfully reset! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, user=user)
