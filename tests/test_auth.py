"""
Authentication and Profile Test Suite
=====================================
Validates registration, credentials hashing, login/logout, and permissions.
"""

from app.models.user import User


def test_user_registration(client, db_session):
    """Test standard account registration."""
    response = client.post(
        "/auth/register",
        data={
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    user = User.query.filter_by(username="newuser").first()
    assert user is not None
    assert user.check_password("Password@123") is True
    assert user.role == "user"


def test_user_registration_duplicate_username(client, sample_users):
    """Test duplicate username rejection."""
    response = client.post(
        "/auth/register",
        data={
            "username": "alice",  # already exists
            "email": "other@example.com",
            "full_name": "Another Alice",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
    )
    assert b"already taken" in response.data or response.status_code == 200


def test_login_success(client, sample_users):
    """Test valid credentials login."""
    response = client.post(
        "/auth/login",
        data={"login_identifier": "alice", "password": "Alice@123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Alice" in response.data


def test_login_invalid_password(client, sample_users):
    """Test invalid password rejection."""
    response = client.post(
        "/auth/login",
        data={"login_identifier": "alice", "password": "WrongPassword!"},
        follow_redirects=True,
    )
    assert b"Invalid username" in response.data or b"danger" in response.data


def test_banned_user_login(client, sample_users, db_session):
    """Test suspended accounts cannot log in."""
    user = User.query.get(sample_users["bob_id"])
    user.is_banned = True
    db_session.session.commit()

    response = client.post(
        "/auth/login",
        data={"login_identifier": "bob", "password": "Bob@123"},
        follow_redirects=True,
    )
    assert b"suspended" in response.data


def test_logout(auth_client):
    """Test ending user session."""
    response = auth_client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"signed out" in response.data
