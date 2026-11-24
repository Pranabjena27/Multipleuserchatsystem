"""
Authentication and Profile Forms Module
=======================================
Defines Flask-WTF form classes with comprehensive field validations.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    TextAreaField,
    BooleanField,
    SelectField,
)
import re
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    ValidationError,
    Regexp,
)
from app.models.user import User

try:
    import email_validator  # noqa: F401
    EMAIL_VALIDATOR = Email
except ImportError:
    def EMAIL_VALIDATOR(message="Please provide a valid email address"):
        return Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message=message)



class RegistrationForm(FlaskForm):
    """User account registration form."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=32, message="Username must be between 3 and 32 characters"),
            Regexp(
                r"^[a-zA-Z0-9_]+$",
                message="Username may only contain letters, numbers, and underscores",
            ),
        ],
        render_kw={"placeholder": "e.g. alex_coder"},
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email address is required"),
            EMAIL_VALIDATOR(message="Please provide a valid email address"),
            Length(max=120),
        ],
        render_kw={"placeholder": "alex@example.com"},
    )
    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required"),
            Length(max=100),
        ],
        render_kw={"placeholder": "Alex Johnson"},
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required"),
            Length(min=6, max=128, message="Password must be at least 6 characters long"),
        ],
        render_kw={"placeholder": "Minimum 6 characters"},
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo("password", message="Passwords must match"),
        ],
        render_kw={"placeholder": "Re-type password"},
    )
    submit = SubmitField("Create ConnectX Account")

    def validate_username(self, field: StringField) -> None:
        """Validate uniqueness of username."""
        user = User.query.filter_by(username=field.data.strip().lower()).first()
        if user:
            raise ValidationError("This username is already taken. Please choose another.")

    def validate_email(self, field: StringField) -> None:
        """Validate uniqueness of email address."""
        user = User.query.filter_by(email=field.data.strip().lower()).first()
        if user:
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    """User account sign-in form supporting either username or email."""

    login_identifier = StringField(
        "Username or Email",
        validators=[DataRequired(message="Please enter your username or email")],
        render_kw={"placeholder": "Enter username or email"},
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required")],
        render_kw={"placeholder": "Enter your password"},
    )
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class ProfileForm(FlaskForm):
    """User profile and account settings update form."""

    full_name = StringField(
        "Full Name",
        validators=[DataRequired(message="Full name is required"), Length(max=100)],
        render_kw={"placeholder": "Your full name"},
    )
    status_message = StringField(
        "Status Message",
        validators=[Length(max=128)],
        render_kw={"placeholder": "e.g. Coding in Python 3.14"},
    )
    bio = TextAreaField(
        "Bio",
        validators=[Length(max=500)],
        render_kw={"placeholder": "Tell the community about yourself...", "rows": 3},
    )
    avatar = FileField(
        "Profile Picture",
        validators=[
            FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only! (jpg, png, gif, webp)")
        ],
    )
    # Account Preferences
    theme = SelectField(
        "Preferred Theme",
        choices=[("light", "Light Mode"), ("dark", "Dark Mode")],
        default="light",
    )
    sound_enabled = BooleanField("Enable Sound Cues", default=True)
    desktop_notifications = BooleanField("Enable Desktop Notifications", default=True)
    enter_is_send = BooleanField("Press Enter to Send Message", default=True)
    submit = SubmitField("Save Profile & Settings")


class ChangePasswordForm(FlaskForm):
    """Form to change existing account password."""

    old_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Current password is required")],
    )
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=6, max=128, message="Password must be at least 6 characters"),
        ],
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="New passwords must match"),
        ],
    )
    submit = SubmitField("Update Password")


class ForgotPasswordForm(FlaskForm):
    """Self-service password recovery request form."""

    email = StringField(
        "Registered Email Address",
        validators=[
            DataRequired(message="Email address is required"),
            EMAIL_VALIDATOR(message="Please enter a valid email address"),
        ],
        render_kw={"placeholder": "e.g. user@example.com"},
    )
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    """Set new account password using verified token."""

    password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required"),
            Length(min=6, max=128, message="Password must be at least 6 characters long"),
        ],
        render_kw={"placeholder": "Minimum 6 characters"},
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm your new password"),
            EqualTo("password", message="Passwords must match"),
        ],
        render_kw={"placeholder": "Re-type new password"},
    )
    submit = SubmitField("Update Password")
