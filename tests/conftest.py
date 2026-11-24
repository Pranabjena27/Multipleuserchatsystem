"""
Pytest Test Fixtures Configuration
==================================
Configures in-memory database, test client, and authenticated test users.
"""

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User


@pytest.fixture(scope="session")
def app():
    """Create and configure a Flask application for automated tests."""
    flask_app = create_app("testing")
    return flask_app


@pytest.fixture(scope="function")
def db_session(app):
    """Provide clean database session with fresh schema for each test."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(app, db_session):
    """Unauthenticated Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def sample_users(app, db_session):
    """Seed test users: admin, user1 (alice), user2 (bob) returning safe identifiers."""
    with app.app_context():
        admin = User(
            username="admin",
            email="admin@test.local",
            full_name="Admin Test",
            role="admin",
        )
        admin.set_password("Admin@123")

        alice = User(
            username="alice",
            email="alice@test.local",
            full_name="Alice Test",
            role="user",
        )
        alice.set_password("Alice@123")

        bob = User(
            username="bob",
            email="bob@test.local",
            full_name="Bob Test",
            role="user",
        )
        bob.set_password("Bob@123")

        db.session.add_all([admin, alice, bob])
        db.session.commit()

        # Capture IDs as integers to prevent detached instance expiration errors
        return {
            "admin_id": admin.id,
            "alice_id": alice.id,
            "bob_id": bob.id,
            "admin_username": admin.username,
            "alice_username": alice.username,
            "bob_username": bob.username,
        }


@pytest.fixture(scope="function")
def auth_client(client, sample_users):
    """Test client authenticated as 'alice'."""
    client.post(
        "/auth/login",
        data={"login_identifier": "alice", "password": "Alice@123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture(scope="function")
def admin_client(client, sample_users):
    """Test client authenticated as 'admin'."""
    client.post(
        "/auth/login",
        data={"login_identifier": "admin", "password": "Admin@123"},
        follow_redirects=True,
    )
    return client
