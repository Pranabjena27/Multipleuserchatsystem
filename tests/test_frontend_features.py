"""
ConnectX Premium Frontend & Auxiliary Endpoints Test Suite
==========================================================
Verifies:
1. Forgot password request & token generation.
2. Password reset via secure timed token.
3. Invalid / expired reset token rejection.
4. Notifications API retrieval and unread counter.
5. Marking notifications as read.
6. Dynamic user settings updates (theme, audio, notifications, enter_is_send).
7. Online contacts list retrieval for sidebar ribbon.
"""

import pytest
from itsdangerous import URLSafeTimedSerializer
from flask import url_for
from app.extensions import db
from app.models.user import User, UserSettings
from app.models.chat import Notification


@pytest.fixture
def test_user(app, db_session):
    """Seed single test user for frontend feature tests."""
    with app.app_context():
        user = User(
            username="frontend_tester",
            email="tester@example.com",
            full_name="Frontend Tester",
        )
        user.set_password("OldPass@123")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "email": user.email, "username": user.username}


def test_forgot_password_request_valid_email(client, test_user):
    """Test requesting a password reset link with a valid registered email."""
    res = client.post(
        "/auth/forgot-password",
        data={"email": test_user["email"]},
        follow_redirects=True,
    )
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "A password reset link has been generated" in html
    assert "/auth/reset-password/" in html


def test_forgot_password_request_unknown_email(client):
    """Test requesting a password reset link with an unregistered email."""
    res = client.post(
        "/auth/forgot-password",
        data={"email": "nonexistent@example.com"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "If an account is associated" in html


def test_reset_password_with_valid_token(app, client, test_user):
    """Test resetting password using a valid cryptographic token."""
    with app.app_context():
        serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        token = serializer.dumps(test_user["email"], salt="connectx-password-reset")

    # GET reset password form
    res_get = client.get(f"/auth/reset-password/{token}")
    assert res_get.status_code == 200
    assert "Set New Password" in res_get.get_data(as_text=True)

    # POST new password
    res_post = client.post(
        f"/auth/reset-password/{token}",
        data={"password": "NewSecret@123", "confirm_password": "NewSecret@123"},
        follow_redirects=True,
    )
    assert res_post.status_code == 200
    assert "Your password has been successfully reset" in res_post.get_data(as_text=True)

    # Verify user can log in with new password
    res_login = client.post(
        "/auth/login",
        data={"login_identifier": test_user["username"], "password": "NewSecret@123"},
        follow_redirects=True,
    )
    assert res_login.status_code == 200
    assert "Welcome back" in res_login.get_data(as_text=True)


def test_reset_password_with_tampered_token(client):
    """Test that a tampered or invalid reset token is rejected."""
    res = client.get("/auth/reset-password/tampered-invalid-token", follow_redirects=True)
    assert res.status_code == 200
    assert "Invalid or corrupted password reset token" in res.get_data(as_text=True)


def test_notifications_api(app, client, test_user):
    """Test retrieving and marking notifications as read."""
    # Log in
    client.post(
        "/auth/login",
        data={"login_identifier": test_user["username"], "password": "OldPass@123"},
    )

    with app.app_context():
        n1 = Notification(
            user_id=test_user["id"],
            type="direct_message",
            title="Direct Message",
            content="Hello there!",
            link_url="/c/1",
            is_read=False,
        )
        n2 = Notification(
            user_id=test_user["id"],
            type="mention",
            title="Channel Mention",
            content="You were mentioned in #general",
            link_url="/c/2",
            is_read=False,
        )
        db.session.add_all([n1, n2])
        db.session.commit()

    # 1. Fetch notifications
    res = client.get("/api/notifications")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["unread_count"] == 2
    assert len(data["notifications"]) == 2

    # 2. Mark all notifications as read
    res_read = client.post("/api/notifications/read", json={})
    assert res_read.status_code == 200
    assert res_read.get_json()["success"] is True

    # 3. Verify unread count is now 0
    res_verify = client.get("/api/notifications")
    assert res_verify.get_json()["unread_count"] == 0


def test_update_user_settings_api(client, test_user):
    """Test dynamically saving user settings preferences."""
    client.post(
        "/auth/login",
        data={"login_identifier": test_user["username"], "password": "OldPass@123"},
    )

    res = client.post(
        "/api/users/settings",
        json={
            "theme": "dark",
            "sound_enabled": False,
            "desktop_notifications": False,
            "enter_is_send": True,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["settings"]["theme"] == "dark"
    assert data["settings"]["sound_enabled"] is False
    assert data["settings"]["desktop_notifications"] is False
    assert data["settings"]["enter_is_send"] is True


def test_online_users_api(app, client, test_user):
    """Test online contacts API for sidebar online ribbon."""
    with app.app_context():
        online_friend = User(
            username="online_friend",
            email="friend@connectx.local",
            full_name="Online Friend",
            is_online=True,
        )
        online_friend.set_password("Friend@123")
        db.session.add(online_friend)
        db.session.commit()

    client.post(
        "/auth/login",
        data={"login_identifier": test_user["username"], "password": "OldPass@123"},
    )

    res = client.get("/api/users/online")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    usernames = [u["username"] for u in data["users"]]
    assert "online_friend" in usernames
