"""
ConnectX - Messaging System Diagnostic & Verification Test Suite
================================================================
Module: Private Chat, Group Chat, and Reliable Real-Time Message Delivery

Verifies the 8 core test scenarios:
TEST 1: User A sends a private message to User B (access restricted to A & B).
TEST 2: User B replies to User A (User A receives the reply instantly).
TEST 3: User A creates a group containing User B and User C (all 3 can communicate).
TEST 4: User A sends a group message (User B and User C receive it).
TEST 5: User outside the group attempts to access it (access rejected).
TEST 6: Refresh simulation (messages retrieved accurately from database).
TEST 7: Disconnect and reconnect a user (reconnects, receives subsequent messages, no duplicates).
TEST 8: Send multiple messages rapidly (persisted and ordered chronologically).
"""

import pytest
from app.extensions import db, socketio
from app.models.user import User
from app.models.chat import Conversation, ConversationParticipant, Message


@pytest.fixture
def messaging_fixture(app, db_session):
    """
    Setup 4 distinct accounts:
    - User A: 'user_a' (Alice)
    - User B: 'user_b' (Bob)
    - User C: 'user_c' (Charlie)
    - Outsider: 'user_d' (David/Outsider)
    """
    with app.app_context():
        u_a = User(username="user_a", email="user_a@connectx.local", full_name="User A (Alice)")
        u_a.set_password("Pass@123456")
        u_b = User(username="user_b", email="user_b@connectx.local", full_name="User B (Bob)")
        u_b.set_password("Pass@123456")
        u_c = User(username="user_c", email="user_c@connectx.local", full_name="User C (Charlie)")
        u_c.set_password("Pass@123456")
        u_d = User(username="user_d", email="user_d@connectx.local", full_name="User D (Outsider)")
        u_d.set_password("Pass@123456")

        db.session.add_all([u_a, u_b, u_c, u_d])
        db.session.commit()

        u_a_id = u_a.id
        u_b_id = u_b.id
        u_c_id = u_c.id
        u_d_id = u_d.id

    client_a = app.test_client()
    client_a.post("/auth/login", data={"login_identifier": "user_a", "password": "Pass@123456"})

    client_b = app.test_client()
    client_b.post("/auth/login", data={"login_identifier": "user_b", "password": "Pass@123456"})

    client_c = app.test_client()
    client_c.post("/auth/login", data={"login_identifier": "user_c", "password": "Pass@123456"})

    client_d = app.test_client()
    client_d.post("/auth/login", data={"login_identifier": "user_d", "password": "Pass@123456"})

    return {
        "a_id": u_a_id,
        "b_id": u_b_id,
        "c_id": u_c_id,
        "d_id": u_d_id,
        "client_a": client_a,
        "client_b": client_b,
        "client_c": client_c,
        "client_d": client_d,
    }


def test_1_private_message_isolation(app, messaging_fixture):
    """
    TEST 1: User A sends a private message to User B.
    Expected: Only User A and User B can access the conversation; outsider cannot.
    """
    a_id = messaging_fixture["a_id"]
    b_id = messaging_fixture["b_id"]
    d_id = messaging_fixture["d_id"]
    client_a = messaging_fixture["client_a"]
    client_b = messaging_fixture["client_b"]
    client_d = messaging_fixture["client_d"]

    # 1. User A creates private conversation with User B via API
    res = client_a.post("/api/conversations", json={"type": "direct", "recipient_id": b_id})
    assert res.status_code in (200, 201)
    conv_id = res.get_json()["conversation"]["id"]

    # 2. Both connect via sockets
    s_a = socketio.test_client(app, flask_test_client=client_a)
    s_b = socketio.test_client(app, flask_test_client=client_b)
    s_d = socketio.test_client(app, flask_test_client=client_d)
    s_a.get_received()
    s_b.get_received()
    s_d.get_received()

    # 3. User A sends private message
    s_a.emit("send_message", {
        "conversation_id": conv_id,
        "content": "Secret note for User B",
        "temp_id": "temp_t1",
    })

    events_a = [e for e in s_a.get_received() if e["name"] == "new_message"]
    events_b = [e for e in s_b.get_received() if e["name"] == "new_message"]
    events_d = [e for e in s_d.get_received() if e["name"] == "new_message"]

    assert len(events_a) == 1
    assert len(events_b) == 1
    assert len(events_d) == 0  # Outsider receives nothing

    # Outsider cannot fetch messages via REST API
    res_d = client_d.get(f"/api/conversations/{conv_id}/messages")
    assert res_d.status_code == 403

    # Both A and B can fetch
    assert client_a.get(f"/api/conversations/{conv_id}/messages").status_code == 200
    assert client_b.get(f"/api/conversations/{conv_id}/messages").status_code == 200


def test_2_user_b_replies_instantly(app, messaging_fixture):
    """
    TEST 2: User B replies to User A.
    Expected: User A receives the reply instantly over WebSocket.
    """
    b_id = messaging_fixture["b_id"]
    client_a = messaging_fixture["client_a"]
    client_b = messaging_fixture["client_b"]

    res = client_a.post("/api/conversations", json={"type": "direct", "recipient_id": b_id})
    conv_id = res.get_json()["conversation"]["id"]

    s_a = socketio.test_client(app, flask_test_client=client_a)
    s_b = socketio.test_client(app, flask_test_client=client_b)
    s_a.get_received()
    s_b.get_received()

    # User B replies
    s_b.emit("send_message", {
        "conversation_id": conv_id,
        "content": "Got your note User A! Reply received instantly.",
        "temp_id": "temp_t2",
    })

    events_a = [e for e in s_a.get_received() if e["name"] == "new_message"]
    assert len(events_a) == 1
    assert "Reply received instantly" in events_a[0]["args"][0]["content"]


def test_3_user_a_creates_group_with_b_and_c(app, messaging_fixture):
    """
    TEST 3: User A creates a group containing User B and User C.
    Expected: All three authorized members can communicate.
    """
    b_id = messaging_fixture["b_id"]
    c_id = messaging_fixture["c_id"]
    client_a = messaging_fixture["client_a"]
    client_b = messaging_fixture["client_b"]
    client_c = messaging_fixture["client_c"]

    res = client_a.post("/api/conversations", json={
        "type": "group",
        "title": "Study Triad ABC",
        "description": "Collaborative Study Group",
        "member_ids": [b_id, c_id],
    })
    assert res.status_code in (200, 201)
    conv_id = res.get_json()["conversation"]["id"]

    # Verify all 3 can access conversation messages
    assert client_a.get(f"/api/conversations/{conv_id}/messages").status_code == 200
    assert client_b.get(f"/api/conversations/{conv_id}/messages").status_code == 200
    assert client_c.get(f"/api/conversations/{conv_id}/messages").status_code == 200


def test_4_group_message_broadcast(app, messaging_fixture):
    """
    TEST 4: User A sends a group message.
    Expected: User B and User C receive it in real-time.
    """
    b_id = messaging_fixture["b_id"]
    c_id = messaging_fixture["c_id"]
    client_a = messaging_fixture["client_a"]
    client_b = messaging_fixture["client_b"]
    client_c = messaging_fixture["client_c"]

    res = client_a.post("/api/conversations", json={
        "type": "group",
        "title": "Project Team Group",
        "member_ids": [b_id, c_id],
    })
    conv_id = res.get_json()["conversation"]["id"]

    s_a = socketio.test_client(app, flask_test_client=client_a)
    s_b = socketio.test_client(app, flask_test_client=client_b)
    s_c = socketio.test_client(app, flask_test_client=client_c)

    # Clear join events
    s_a.get_received()
    s_b.get_received()
    s_c.get_received()

    # User A sends group message
    s_a.emit("send_message", {
        "conversation_id": conv_id,
        "content": "Attention Team: All hands meeting at 10 AM",
        "temp_id": "temp_t4",
    })

    events_b = [e for e in s_b.get_received() if e["name"] == "new_message"]
    events_c = [e for e in s_c.get_received() if e["name"] == "new_message"]

    assert len(events_b) == 1
    assert "All hands meeting" in events_b[0]["args"][0]["content"]

    assert len(events_c) == 1
    assert "All hands meeting" in events_c[0]["args"][0]["content"]


def test_5_outsider_rejected(app, messaging_fixture):
    """
    TEST 5: User outside the group attempts to access it.
    Expected: Access is rejected via HTTP and Socket room join.
    """
    b_id = messaging_fixture["b_id"]
    c_id = messaging_fixture["c_id"]
    client_a = messaging_fixture["client_a"]
    client_d = messaging_fixture["client_d"]  # Outsider

    res = client_a.post("/api/conversations", json={
        "type": "group",
        "title": "Private Team Alpha",
        "member_ids": [b_id, c_id],
    })
    conv_id = res.get_json()["conversation"]["id"]

    # 1. HTTP API access rejection
    res_d = client_d.get(f"/api/conversations/{conv_id}/messages")
    assert res_d.status_code == 403

    # 2. Socket join rejection
    s_d = socketio.test_client(app, flask_test_client=client_d)
    s_d.get_received()
    s_d.emit("join_conversation", {"conversation_id": conv_id})
    events = s_d.get_received()
    error_events = [e for e in events if e["name"] == "error_alert"]
    assert len(error_events) >= 1
    assert "Access denied" in error_events[0]["args"][0]["message"]


def test_6_persistence_after_browser_refresh(app, messaging_fixture):
    """
    TEST 6: Refresh the browser.
    Expected: Previous messages are accurately loaded from the database in chronological order.
    """
    b_id = messaging_fixture["b_id"]
    client_a = messaging_fixture["client_a"]
    client_b = messaging_fixture["client_b"]

    res = client_a.post("/api/conversations", json={"type": "direct", "recipient_id": b_id})
    conv_id = res.get_json()["conversation"]["id"]

    s_a = socketio.test_client(app, flask_test_client=client_a)
    s_a.emit("send_message", {"conversation_id": conv_id, "content": "Message 1 before refresh"})
    s_a.emit("send_message", {"conversation_id": conv_id, "content": "Message 2 before refresh"})

    # Simulate refresh: create brand new HTTP client and fetch history
    refresh_client = app.test_client()
    refresh_client.post("/auth/login", data={"login_identifier": "user_a", "password": "Pass@123456"})

    res_history = refresh_client.get(f"/api/conversations/{conv_id}/messages")
    assert res_history.status_code == 200
    msgs = res_history.get_json()["messages"]
    assert len(msgs) >= 2
    assert msgs[-2]["content"] == "Message 1 before refresh"
    assert msgs[-1]["content"] == "Message 2 before refresh"


def test_7_disconnect_and_reconnect_no_duplicates(app, messaging_fixture):
    """
    TEST 7: Disconnect and reconnect a user.
    Expected: User reconnects and receives subsequent messages without duplicate events.
    """
    b_id = messaging_fixture["b_id"]
    client_a = messaging_fixture["client_a"]
    client_b = messaging_fixture["client_b"]

    res = client_a.post("/api/conversations", json={"type": "direct", "recipient_id": b_id})
    conv_id = res.get_json()["conversation"]["id"]

    s_a = socketio.test_client(app, flask_test_client=client_a)
    s_b = socketio.test_client(app, flask_test_client=client_b)
    assert s_b.is_connected()

    # User B disconnects
    s_b.disconnect()
    assert not s_b.is_connected()

    # User B reconnects with a fresh socket connection
    s_b_reconnected = socketio.test_client(app, flask_test_client=client_b)
    assert s_b_reconnected.is_connected()
    s_b_reconnected.get_received()

    # User A sends a message after User B's reconnection
    s_a.emit("send_message", {
        "conversation_id": conv_id,
        "content": "Message after reconnection",
        "temp_id": "temp_reconnect",
    })

    b_events = [e for e in s_b_reconnected.get_received() if e["name"] == "new_message"]
    # Exactly one new_message event received (no duplicates)
    assert len(b_events) == 1
    assert b_events[0]["args"][0]["content"] == "Message after reconnection"


def test_8_rapid_message_sending_order(app, messaging_fixture):
    """
    TEST 8: Send multiple messages rapidly.
    Expected: Messages are persisted and displayed in the correct chronological order.
    """
    b_id = messaging_fixture["b_id"]
    client_a = messaging_fixture["client_a"]

    res = client_a.post("/api/conversations", json={"type": "direct", "recipient_id": b_id})
    conv_id = res.get_json()["conversation"]["id"]

    s_a = socketio.test_client(app, flask_test_client=client_a)
    s_a.get_received()

    rapid_contents = [f"Burst sequence packet #{i}" for i in range(1, 6)]
    for content in rapid_contents:
        s_a.emit("send_message", {
            "conversation_id": conv_id,
            "content": content,
            "temp_id": f"temp_rapid_{content}",
        })

    # Fetch from database to verify strict FIFO ordering
    res = client_a.get(f"/api/conversations/{conv_id}/messages")
    assert res.status_code == 200
    stored_msgs = res.get_json()["messages"]

    extracted = [m["content"] for m in stored_msgs if "Burst sequence packet" in m["content"]]
    assert extracted == rapid_contents

