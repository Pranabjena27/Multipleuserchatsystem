"""
Input Validation Utilities Module
=================================
Validates email addresses, usernames, and file extensions.
"""

import re

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def is_valid_username(username: str) -> bool:
    """Validate username characters and length."""
    if not username:
        return False
    return bool(USERNAME_PATTERN.match(username.strip()))


def is_valid_email(email: str) -> bool:
    """Validate email syntax."""
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email.strip()))


def is_allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    """Check if uploaded file extension is permitted."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in allowed_extensions
