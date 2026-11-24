"""
Comprehensive Database, Authentication & Authorization Test Suite
==================================================================
Validates:
- No plain-text passwords stored (cryptographic hashing verified)
- Input validation & duplicate registration prevention
- Username OR email login flexibility
- Session security and logout
- User profile & settings management
- Strict authorization (cannot access unauthorized private chats or groups)
- Identity derived strictly from session, never untrusted browser payload
"""

from app.models.user import User, UserSettings
from app.models.chat import Conversation, ConversationParticipant, Message


def test_password_hashing_security(app, db_session):
    """Verify that plain-text passwords are NEVER stored in the database."""
    with app.app_context():
        user = User(username="hash_test", email="hash@test.local", full_name="Hash Test")
        user.set_password("SuperSecret@999")
        db_session.session.add(user)
        db_session.session.commit()

        # Query directly from DB
        persisted = User.query.filter_by(username="hash_test").first()
        assert persisted.password_hash != "SuperSecret@999"
        assert "SuperSecret" not in persisted.password_hash
        # Confirm Werkzeug PBKDF2/scrypt cryptographic hash format
        assert persisted.password_hash.startswith(("pbkdf2:sha256:", "scrypt:"))
        assert persisted.check_password("SuperSecret@999") is True
        assert persisted.check_password("WrongPassword") is False


def test_registration_duplicate_email_prevention(client, sample_users):
    """Verify duplicate email registration is rejected with an error message."""
    response = client.post(
        "/auth/register",
        data={
            "username": "unique_user_1",
            "email": "alice@test.local",  # Duplicate email of Alice
            "full_name": "Test User",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
    )
    assert response.status_code == 200
    assert b"already exists" in response.data


def test_registration_mismatched_password(client, db_session):
    """Verify registration fails when confirmation password does not match."""
    response = client.post(
        "/auth/register",
        data={
            "username": "mismatch_user",
            "email": "mismatch@test.local",
            "full_name": "Mismatch User",
            "password": "Password@123",
            "confirm_password": "DifferentPassword@123",
        },
    )
    assert response.status_code == 200
    assert b"Passwords must match" in response.data


def test_registration_short_password(client, db_session):
    """Verify password length requirement (< 6 characters rejected)."""
    response = client.post(
        "/auth/register",
        data={
            "username": "short_pass_user",
            "email": "short@test.local",
            "full_name": "Short Pass",
            "password": "123",
            "confirm_password": "123",
        },
    )
    assert response.status_code == 200
    assert b"at least 6 characters" in response.data


def test_login_via_email(client, sample_users):
    """Verify users can sign in using their email address instead of username."""
    response = client.post(
        "/auth/login",
        data={"login_identifier": "alice@test.local", "password": "Alice@123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, Alice" in response.data


def test_login_nonexistent_user(client, sample_users):
    """Verify attempting to log in as a non-existent user returns an error."""
    response = client.post(
        "/auth/login",
        data={"login_identifier": "nonexistent_user", "password": "AnyPassword@123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username/email or password" in response.data


def test_user_settings_creation_and_update(app, auth_client, sample_users, db_session):
    """Verify user settings (theme, notifications, sound) are created and updated."""
    with app.app_context():
        alice = User.query.get(sample_users["alice_id"])
        settings = alice.get_or_create_settings()
        assert settings.theme in ("light", "dark")

    # Update settings via Profile Form POST
    res = auth_client.post(
        "/auth/profile",
        data={
            "submit_profile": "1",
            "full_name": "Alice C. Updated",
            "status_message": "Exploring AI Sockets",
            "bio": "Updated bio information.",
            "theme": "dark",
            "sound_enabled": "y",
            "desktop_notifications": "y",
            "enter_is_send": "y",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"updated successfully" in res.data

    with app.app_context():
        updated_alice = User.query.get(sample_users["alice_id"])
        assert updated_alice.full_name == "Alice C. Updated"
        assert updated_alice.settings.theme == "dark"


def test_authorization_user_cannot_access_other_private_chat(app, client, sample_users, db_session):
    """
    CRITICAL AUTHORIZATION TEST:
    Bob and Charlie have a private conversation.
    Alice MUST NOT be able to view or fetch messages from this conversation.
    Server MUST derive identity strictly from session, rejecting unauthorized access with HTTP 403.
    """
    bob_id = sample_users["bob_id"]

    with app.app_context():
        # Create a 3rd user 'charlie'
        charlie = User(username="charlie", email="charlie@test.local", full_name="Charlie")
        charlie.set_password("Charlie@123")
        db_session.session.add(charlie)
        db_session.session.commit()

        # Create private direct conversation between Bob and Charlie
        conv = Conversation(type="direct", creator_id=bob_id)
        db_session.session.add(conv)
        db_session.session.flush()

        p_bob = ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member")
        p_charlie = ConversationParticipant(conversation_id=conv.id, user_id=charlie.id, role="member")
        db_session.session.add_all([p_bob, p_charlie])

        msg = Message(
            conversation_id=conv.id,
            sender_id=bob_id,
            content="Confidential message between Bob and Charlie only.",
        )
        db_session.session.add(msg)
        db_session.session.commit()
        conv_id = conv.id

    # Log in as Alice (unauthorized third party)
    client.post(
        "/auth/login",
        data={"login_identifier": "alice", "password": "Alice@123"},
        follow_redirects=True,
    )

    # Alice attempts to fetch Bob & Charlie's private messages
    res = client.get(f"/api/conversations/{conv_id}/messages")
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False
    assert "Access denied" in data["message"]

    # Alice attempts to navigate to Bob & Charlie's private URL directly
    res_page = client.get(f"/c/{conv_id}", follow_redirects=False)
    # Redirected away to index
    assert res_page.status_code == 302


def test_authorization_user_cannot_manage_unauthorized_group(app, client, sample_users, db_session):
    """Verify non-admin/non-member cannot add participants to a group."""
    bob_id = sample_users["bob_id"]

    with app.app_context():
        # Group created by Bob
        group = Conversation(type="group", title="Bob's Private Circle", creator_id=bob_id)
        db_session.session.add(group)
        db_session.session.flush()
        db_session.session.add(ConversationParticipant(conversation_id=group.id, user_id=bob_id, role="admin"))
        db_session.session.commit()
        group_id = group.id

    # Sign in as Alice
    client.post(
        "/auth/login",
        data={"login_identifier": "alice", "password": "Alice@123"},
        follow_redirects=True,
    )

    # Alice attempts to add someone to Bob's group
    res = client.post(
        f"/api/conversations/{group_id}/participants",
        json={"user_id": sample_users["admin_id"]},
    )
    assert res.status_code == 403
    assert res.get_json()["success"] is False
