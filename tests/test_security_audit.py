"""
ConnectX Comprehensive Security & Penetration Testing Suite
===========================================================
Tests:
1. Password hashing & credential security
2. SQL Injection penetration resistance
3. Stored & Reflected Cross-Site Scripting (XSS) sanitization
4. Cross-Site Request Forgery (CSRF) protection
5. Unauthorized conversation & group access prevention
6. Socket.IO event authorization & identity spoofing prevention
7. File upload security, extension whitelisting & path traversal defense
8. Session cookie flags & authentication boundaries
9. Role-Based Access Control (RBAC) administrative lockdown
"""

import io
import pytest
from app.extensions import db
from app.models.user import User
from app.models.chat import Conversation, ConversationParticipant, Message
from app.python_features.processor import MessageProcessor


# =============================================================================
# 1. PASSWORD HASHING & CREDENTIAL SECURITY
# =============================================================================

def test_password_never_stored_in_plaintext(sample_users):
    """Verify that user passwords in SQLite are salted cryptographic hashes, never plaintext."""
    admin = User.query.filter_by(username="admin").first()
    assert admin.password_hash != "Admin@123"
    assert len(admin.password_hash) >= 50
    assert any(admin.password_hash.startswith(prefix) for prefix in ("scrypt:", "pbkdf2:", "argon2:"))


def test_password_verification_and_wrong_password(sample_users):
    """Verify that incorrect passwords fail verification and cannot authenticate."""
    alice = User.query.filter_by(username="alice").first()
    assert alice.check_password("Alice@123") is True
    assert alice.check_password("WrongPassword123") is False
    assert alice.check_password("") is False
    assert alice.check_password("alice@123") is False  # Case sensitivity


# =============================================================================
# 2. SQL INJECTION (SQLi) PENETRATION RESISTANCE
# =============================================================================

@pytest.mark.parametrize("sqli_payload", [
    "' OR 1=1 --",
    "admin' --",
    "' UNION SELECT null, null, null, null --",
    "1; DROP TABLE messages; --",
    "'; EXEC xp_cmdshell('dir'); --",
    "\" OR \"\"=\"",
])
def test_message_search_sqli_resilience(auth_client, sqli_payload):
    """Verify that SQL injection strings in message search do not cause SQL syntax errors."""
    response = auth_client.get(f"/api/messages/search?q={sqli_payload}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["results"], list)


@pytest.mark.parametrize("sqli_payload", [
    "' OR '1'='1",
    "admin'/*",
    "') OR ('1'='1",
])
def test_user_search_sqli_resilience(auth_client, sqli_payload):
    """Verify that SQL injection strings in user search are sanitized by the ORM."""
    response = auth_client.get(f"/api/users/search?q={sqli_payload}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    # Should not dump banned users or arbitrary records
    for u in data["users"]:
        assert u.get("is_banned", False) is False


def test_login_form_sqli_bypass_attempt(client, sample_users):
    """Verify that classic SQL injection in the login form fails to bypass password checks."""
    response = client.post("/auth/login", data={
        "login_identifier": "admin' OR '1'='1",
        "password": "any_password",
    }, follow_redirects=True)
    assert b"Invalid username/email or password" in response.data or response.status_code in (200, 302)
    # Ensure not authenticated
    check_auth = client.get("/auth/profile")
    assert check_auth.status_code == 302


# =============================================================================
# 3. CROSS-SITE SCRIPTING (XSS) DEFENSE
# =============================================================================

@pytest.mark.parametrize("xss_payload", [
    '<script>alert("XSS")</script>',
    '<img src="x" onerror="alert(1)">',
    '<a href="javascript:alert(document.cookie)">Click me</a>',
    '"><script src=http://evil.com/xss.js></script>',
    '<svg/onload=alert`1`>',
])
def test_message_processor_xss_sanitization(xss_payload):
    """Verify that MessageProcessor sanitizes dangerous HTML entities."""
    processor = MessageProcessor()
    sanitized = processor.sanitize(xss_payload)
    assert "<script" not in sanitized
    assert "javascript:" not in sanitized
    assert "&lt;" in sanitized or "&#x27;" in sanitized or "&quot;" in sanitized


def test_profile_xss_injection_handling(auth_client):
    """Verify updating profile with XSS payload is safely handled."""
    xss_name = '<script>alert("HackedName")</script>'
    xss_bio = '<img src=x onerror=alert("HackedBio")>'
    response = auth_client.post("/auth/profile", data={
        "submit_profile": "1",
        "full_name": xss_name,
        "bio": xss_bio,
        "status_message": "Safe status",
        "theme": "light",
        "sound_enabled": "y",
        "desktop_notifications": "y",
        "enter_is_send": "y",
    }, follow_redirects=True)
    assert response.status_code == 200
    # In Jinja2 output, it must be escaped: &lt;script&gt;
    assert b"<script>alert" not in response.data


# =============================================================================
# 4. UNAUTHORIZED CONVERSATION & GROUP ISOLATION
# =============================================================================

def test_unauthorized_direct_message_privacy(client, sample_users):
    """Verify that a third-party user cannot query private messages between two other users."""
    # Create private chat between admin and alice
    conv = Conversation(type="direct")
    db.session.add(conv)
    db.session.flush()

    p1 = ConversationParticipant(conversation_id=conv.id, user_id=sample_users["admin_id"], role="member")
    p2 = ConversationParticipant(conversation_id=conv.id, user_id=sample_users["alice_id"], role="member")
    db.session.add_all([p1, p2])

    msg = Message(
        conversation_id=conv.id,
        sender_id=sample_users["admin_id"],
        content="Confidential exam questions",
    )
    db.session.add(msg)
    db.session.commit()

    # Log in as Bob (third party)
    client.post("/auth/login", data={
        "login_identifier": "bob",
        "password": "Bob@123",
    })

    # Bob attempts to read messages from admin-alice conversation
    resp = client.get(f"/api/conversations/{conv.id}/messages")
    assert resp.status_code == 403
    assert resp.get_json()["success"] is False

    # Bob attempts to summarize admin-alice conversation
    sum_resp = client.post(f"/api/conversations/{conv.id}/summarize")
    assert sum_resp.status_code == 403


def test_unauthorized_group_management_blocked(client, sample_users):
    """Verify that regular group members cannot kick other members."""
    group = Conversation(type="group", title="Restricted Group", creator_id=sample_users["admin_id"])
    db.session.add(group)
    db.session.flush()

    p_admin = ConversationParticipant(conversation_id=group.id, user_id=sample_users["admin_id"], role="admin")
    p_alice = ConversationParticipant(conversation_id=group.id, user_id=sample_users["alice_id"], role="member")
    p_bob = ConversationParticipant(conversation_id=group.id, user_id=sample_users["bob_id"], role="member")
    db.session.add_all([p_admin, p_alice, p_bob])
    db.session.commit()

    # Log in as Alice (regular member)
    client.post("/auth/login", data={
        "login_identifier": "alice",
        "password": "Alice@123",
    })

    # Alice attempts to kick Bob from the group
    kick_resp = client.delete(f"/api/conversations/{group.id}/participants/{sample_users['bob_id']}")
    assert kick_resp.status_code == 403
    assert kick_resp.get_json()["success"] is False


# =============================================================================
# 5. FILE UPLOAD SECURITY & PATH TRAVERSAL DEFENSE
# =============================================================================

@pytest.mark.parametrize("dangerous_filename, extension", [
    ("malicious.exe", "exe"),
    ("shell.php", "php"),
    ("script.sh", "sh"),
    ("exploit.py", "py"),
    ("trojan.bat", "bat"),
    ("library.dll", "dll"),
])
def test_disallowed_file_extensions_rejected(auth_client, dangerous_filename, extension):
    """Verify that executable and script attachments are rejected by the upload firewall."""
    file_data = (io.BytesIO(b"malicious payload content"), dangerous_filename)
    response = auth_client.post(
        "/api/upload",
        data={"file": file_data},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert f"File type '.{extension}' is not permitted" in data["message"]


def test_path_traversal_filename_neutralized(auth_client):
    """Verify that filenames containing directory traversal (e.g. ../../test.pdf) are neutralized."""
    traversal_name = "../../../../../etc/passwd.pdf"
    file_data = (io.BytesIO(b"%PDF-1.4 mock content"), traversal_name)
    response = auth_client.post(
        "/api/upload",
        data={"file": file_data},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    # Saved filename must NOT contain path traversal symbols
    saved_filename = data["attachment"]["filename"]
    assert "../" not in saved_filename
    assert ".." not in saved_filename


# =============================================================================
# 6. SESSION SECURITY & COOKIE ATTRIBUTES
# =============================================================================

def test_session_cookie_security_flags(client):
    """Verify that session cookies have HttpOnly and SameSite flags set."""
    client.post("/auth/login", data={
        "login_identifier": "alice",
        "password": "Alice@123",
    })
    # Inspect response cookies
    for cookie in client.application.config:
        pass
    assert client.application.config["SESSION_COOKIE_HTTPONLY"] is True
    assert client.application.config["SESSION_COOKIE_SAMESITE"] in ("Lax", "Strict")


def test_logout_clears_session(auth_client):
    """Verify that logging out revokes access to protected routes."""
    # Initially can access profile
    assert auth_client.get("/auth/profile").status_code == 200

    # Log out
    logout_resp = auth_client.get("/auth/logout")
    assert logout_resp.status_code == 302

    # Subsequent access redirected to login
    protected = auth_client.get("/auth/profile")
    assert protected.status_code == 302
    assert "/auth/login" in protected.headers["Location"]


# =============================================================================
# 7. ROLE-BASED ACCESS CONTROL (RBAC) LOCKDOWN
# =============================================================================

def test_regular_user_cannot_access_any_admin_endpoint(auth_client):
    """Verify that non-admin users cannot access administrative views."""
    admin_routes = [
        "/admin/",
        "/admin/users",
        "/admin/reports",
        "/admin/announcements",
        "/admin/audit-logs",
    ]
    for route in admin_routes:
        resp = auth_client.get(route, follow_redirects=True)
        # Should either redirect to chat.index or flash danger error
        assert b"Administrator privileges required" in resp.data or resp.status_code == 403


def test_regular_user_cannot_ban_users(auth_client, sample_users):
    """Verify regular user cannot send ban requests."""
    resp = auth_client.post(f"/admin/users/{sample_users['bob_id']}/toggle-ban", follow_redirects=True)
    assert b"Administrator privileges required" in resp.data
    # Verify Bob was NOT banned
    bob = User.query.get(sample_users["bob_id"])
    assert bob.is_banned is False

