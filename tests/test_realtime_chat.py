"""
ConnectX Multi-User Real-Time Chat Test Suite
=============================================
Module: WebSocket Real-Time Chat & Multi-User Room Isolation

Verifies:
1. Private 1-to-1 messaging delivery and room isolation between multiple users.
2. Group messaging delivery and authorization (only authorized members receive).
3. Unauthorized room join rejection and access enforcement.
4. Message persistence across server reloads and chronological retrieval.
5. Message editing restricted to author and real-time update broadcast.
6. Soft message deletion restricted to author/admin and real-time deletion broadcast.
7. Real-time typing indicators with sender exclusion.
8. Real-time read receipts and database status tracking.
9. Emoji reactions toggling and broadcast.
10. Unauthenticated socket connection rejection.
11. Cursor-based pagination on conversation messages endpoint.
"""

import pytest
from app.extensions import db, socketio
from app.models.user import User
from app.models.chat import Conversation, ConversationParticipant, Message, ReadReceipt, MessageReaction


@pytest.fixture
def multi_user_setup(app, db_session):
    """
    Create 4 distinct users:
    - Alice (User)
    - Bob (User)
    - Charlie (User)
    - Eve (Unauthorized outsider)
    Returns their authenticated Flask test clients and user IDs.
    """
    with app.app_context():
        u_alice = User(username="alice", email="alice@test.local", full_name="Alice Wonderland")
        u_alice.set_password("Alice@123")
        u_bob = User(username="bob", email="bob@test.local", full_name="Bob Builder")
        u_bob.set_password("Bob@123")
        u_charlie = User(username="charlie", email="charlie@test.local", full_name="Charlie Chaplin")
        u_charlie.set_password("Charlie@123")
        u_eve = User(username="eve", email="eve@test.local", full_name="Eve Eavesdropper")
        u_eve.set_password("Eve@123")

        db.session.add_all([u_alice, u_bob, u_charlie, u_eve])
        db.session.commit()

        alice_id = u_alice.id
        bob_id = u_bob.id
        charlie_id = u_charlie.id
        eve_id = u_eve.id

    client_alice = app.test_client()
    client_alice.post("/auth/login", data={"login_identifier": "alice", "password": "Alice@123"})

    client_bob = app.test_client()
    client_bob.post("/auth/login", data={"login_identifier": "bob", "password": "Bob@123"})

    client_charlie = app.test_client()
    client_charlie.post("/auth/login", data={"login_identifier": "charlie", "password": "Charlie@123"})

    client_eve = app.test_client()
    client_eve.post("/auth/login", data={"login_identifier": "eve", "password": "Eve@123"})

    return {
        "alice_id": alice_id,
        "bob_id": bob_id,
        "charlie_id": charlie_id,
        "eve_id": eve_id,
        "client_alice": client_alice,
        "client_bob": client_bob,
        "client_charlie": client_charlie,
        "client_eve": client_eve,
    }


def test_unauthenticated_socket_connection_rejected(app):
    """E. Socket.IO security: Unauthenticated client is disconnected immediately."""
    unauth_client = app.test_client()
    socket_client = socketio.test_client(app, flask_test_client=unauth_client)
    assert not socket_client.is_connected()


def test_realtime_private_messaging_delivery_and_isolation(app, multi_user_setup):
    """
    A. Private chat & Room Isolation:
    Alice and Bob are in a private 1-to-1 conversation.
    Eve is an outsider.
    Alice sends a message via SocketIO -> Alice and Bob receive in room `conv_{id}`.
    Eve does NOT receive the message in any room.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    # 1. Create direct conversation in DB
    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        db.session.commit()
        conv_id = conv.id

    # 2. Connect Alice, Bob, and Eve sockets
    s_alice = socketio.test_client(app, flask_test_client=multi_user_setup["client_alice"])
    s_bob = socketio.test_client(app, flask_test_client=multi_user_setup["client_bob"])
    s_eve = socketio.test_client(app, flask_test_client=multi_user_setup["client_eve"])

    assert s_alice.is_connected()
    assert s_bob.is_connected()
    assert s_eve.is_connected()

    # Clear initial connection ack events
    s_alice.get_received()
    s_bob.get_received()
    s_eve.get_received()

    # 3. Alice and Bob join conversation room
    s_alice.emit("join_conversation", {"conversation_id": conv_id})
    s_bob.emit("join_conversation", {"conversation_id": conv_id})

    # Clear room_joined events
    s_alice.get_received()
    s_bob.get_received()

    # 4. Alice sends private message
    msg_text = "Hello Bob! This is our private end-to-end conversation."
    s_alice.emit("send_message", {
        "conversation_id": conv_id,
        "content": msg_text,
        "temp_id": "temp_101",
    })

    # 5. Verify Alice receives broadcasted new_message
    alice_events = s_alice.get_received()
    alice_msg_events = [e for e in alice_events if e["name"] == "new_message"]
    assert len(alice_msg_events) == 1
    sent_msg = alice_msg_events[0]["args"][0]
    assert sent_msg["content"] == msg_text
    assert sent_msg["sender_id"] == alice_id
    assert sent_msg["conversation_id"] == conv_id

    # 6. Verify Bob receives new_message and notification
    bob_events = s_bob.get_received()
    bob_msg_events = [e for e in bob_events if e["name"] == "new_message"]
    assert len(bob_msg_events) == 1
    assert bob_msg_events[0]["args"][0]["content"] == msg_text

    # Bob also receives direct notification in user_bob room
    bob_notif_events = [e for e in bob_events if e["name"] == "message_notification"]
    assert len(bob_notif_events) == 1
    assert bob_notif_events[0]["args"][0]["conversation_id"] == conv_id

    # 7. Verify Eve receives ZERO messages or notifications
    eve_events = s_eve.get_received()
    assert len(eve_events) == 0

    s_alice.disconnect()
    s_bob.disconnect()
    s_eve.disconnect()


def test_unauthorized_room_join_rejected(app, multi_user_setup):
    """
    E. Socket.IO security:
    Eve attempts to join Alice and Bob's private conversation room.
    The server rejects her with error_alert and denies access.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob Private")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        db.session.commit()
        conv_id = conv.id

    s_eve = socketio.test_client(app, flask_test_client=multi_user_setup["client_eve"])
    s_eve.get_received()  # clear ack

    # Eve tries to spy by joining conv_id
    s_eve.emit("join_conversation", {"conversation_id": conv_id})
    eve_events = s_eve.get_received()

    error_events = [e for e in eve_events if e["name"] == "error_alert"]
    assert len(error_events) == 1
    assert "Access denied" in error_events[0]["args"][0]["message"]

    s_eve.disconnect()


def test_group_chat_delivery_and_member_authorization(app, multi_user_setup):
    """
    B. Group chat:
    Alice, Bob, and Charlie are members of "Python Study Group".
    Eve is not a member.
    Bob sends a message -> Alice and Charlie receive it; Eve does not.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]
    charlie_id = multi_user_setup["charlie_id"]

    with app.app_context():
        group = Conversation(
            type="group",
            title="Study Group",
            description="Capstone Engineering Team",
            creator_id=alice_id,
        )
        db.session.add(group)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=group.id, user_id=alice_id, role="admin"),
            ConversationParticipant(conversation_id=group.id, user_id=bob_id, role="member"),
            ConversationParticipant(conversation_id=group.id, user_id=charlie_id, role="member"),
        ])
        db.session.commit()
        group_id = group.id

    s_alice = socketio.test_client(app, flask_test_client=multi_user_setup["client_alice"])
    s_bob = socketio.test_client(app, flask_test_client=multi_user_setup["client_bob"])
    s_charlie = socketio.test_client(app, flask_test_client=multi_user_setup["client_charlie"])
    s_eve = socketio.test_client(app, flask_test_client=multi_user_setup["client_eve"])

    # Clear initial events
    for s in (s_alice, s_bob, s_charlie, s_eve):
        s.get_received()

    # Members join room
    s_alice.emit("join_conversation", {"conversation_id": group_id})
    s_bob.emit("join_conversation", {"conversation_id": group_id})
    s_charlie.emit("join_conversation", {"conversation_id": group_id})

    for s in (s_alice, s_bob, s_charlie):
        s.get_received()

    # Bob sends group message
    s_bob.emit("send_message", {
        "conversation_id": group_id,
        "content": "Welcome team! Has everyone reviewed the SocketIO architecture?",
        "temp_id": "temp_group_1",
    })

    # Verify Alice received
    alice_msgs = [e for e in s_alice.get_received() if e["name"] == "new_message"]
    assert len(alice_msgs) == 1
    assert "Welcome team!" in alice_msgs[0]["args"][0]["content"]

    # Verify Charlie received
    charlie_msgs = [e for e in s_charlie.get_received() if e["name"] == "new_message"]
    assert len(charlie_msgs) == 1
    assert "Welcome team!" in charlie_msgs[0]["args"][0]["content"]

    # Verify Eve received nothing
    assert len(s_eve.get_received()) == 0

    s_alice.disconnect()
    s_bob.disconnect()
    s_charlie.disconnect()
    s_eve.disconnect()


def test_message_persistence_and_database_retrieval(app, multi_user_setup):
    """
    A. Persistent message history:
    Messages sent via WebSocket must be saved to SQLite and retrievable via REST API.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        db.session.commit()
        conv_id = conv.id

    s_alice = socketio.test_client(app, flask_test_client=multi_user_setup["client_alice"])
    s_alice.get_received()
    s_alice.emit("join_conversation", {"conversation_id": conv_id})
    s_alice.get_received()

    # Send 3 distinct messages
    texts = [
        "First message: Introduction to Python SocketIO",
        "Second message: Real-time event broadcasting",
        "Third message: Persistent storage verification",
    ]
    for text in texts:
        s_alice.emit("send_message", {
            "conversation_id": conv_id,
            "content": text,
        })

    s_alice.disconnect()

    # Verify directly in SQLite Database
    with app.app_context():
        db_messages = (
            Message.query.filter_by(conversation_id=conv_id)
            .order_by(Message.id.asc())
            .all()
        )
        assert len(db_messages) == 3
        for i, text in enumerate(texts):
            assert db_messages[i].content == text
            assert db_messages[i].sender_id == alice_id
            assert db_messages[i].created_at is not None

    # Verify retrieval via authenticated REST API
    res = multi_user_setup["client_bob"].get(f"/api/conversations/{conv_id}/messages")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["messages"]) == 3
    assert data["messages"][0]["content"] == texts[0]
    assert data["messages"][2]["content"] == texts[2]


def test_realtime_message_editing_author_only(app, multi_user_setup):
    """
    D. Message management - Edit:
    Author (Alice) can edit her message; change broadcasts via `message_edited`.
    Non-author (Bob) cannot edit Alice's message; rejected with error_alert.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        msg = Message(
            conversation_id=conv.id,
            sender_id=alice_id,
            content="Original message with typo: Pythn is gr8",
        )
        db.session.add(msg)
        db.session.commit()
        conv_id = conv.id
        msg_id = msg.id

    s_alice = socketio.test_client(app, flask_test_client=multi_user_setup["client_alice"])
    s_bob = socketio.test_client(app, flask_test_client=multi_user_setup["client_bob"])
    s_alice.get_received()
    s_bob.get_received()

    s_alice.emit("join_conversation", {"conversation_id": conv_id})
    s_bob.emit("join_conversation", {"conversation_id": conv_id})
    s_alice.get_received()
    s_bob.get_received()

    # Bob attempts to edit Alice's message -> Must fail
    s_bob.emit("edit_message", {
        "message_id": msg_id,
        "content": "Bob maliciously trying to rewrite Alice's message",
    })
    bob_events = s_bob.get_received()
    bob_errors = [e for e in bob_events if e["name"] == "error_alert"]
    assert len(bob_errors) == 1
    assert "only edit your own" in bob_errors[0]["args"][0]["message"]

    # Alice edits her own message -> Must succeed and broadcast
    corrected_content = "Corrected message: Python is great!"
    s_alice.emit("edit_message", {
        "message_id": msg_id,
        "content": corrected_content,
    })

    # Verify Bob receives message_edited broadcast
    bob_events_2 = s_bob.get_received()
    edit_events = [e for e in bob_events_2 if e["name"] == "message_edited"]
    assert len(edit_events) == 1
    assert edit_events[0]["args"][0]["content"] == corrected_content
    assert edit_events[0]["args"][0]["is_edited"] is True

    # Verify database state
    with app.app_context():
        updated_msg = Message.query.get(msg_id)
        assert updated_msg.content == corrected_content
        assert updated_msg.is_edited is True

    s_alice.disconnect()
    s_bob.disconnect()


def test_realtime_message_deletion_permissions(app, multi_user_setup):
    """
    D. Message management - Delete:
    Author (Alice) can soft delete her message; broadcasts `message_deleted`.
    Non-author (Bob) cannot delete Alice's message.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        msg = Message(
            conversation_id=conv.id,
            sender_id=alice_id,
            content="Message that will be deleted",
        )
        db.session.add(msg)
        db.session.commit()
        conv_id = conv.id
        msg_id = msg.id

    s_alice = socketio.test_client(app, flask_test_client=multi_user_setup["client_alice"])
    s_bob = socketio.test_client(app, flask_test_client=multi_user_setup["client_bob"])
    s_alice.get_received()
    s_bob.get_received()

    s_alice.emit("join_conversation", {"conversation_id": conv_id})
    s_bob.emit("join_conversation", {"conversation_id": conv_id})
    s_alice.get_received()
    s_bob.get_received()

    # Bob attempts to delete Alice's message -> Rejection
    s_bob.emit("delete_message", {"message_id": msg_id})
    bob_events = s_bob.get_received()
    assert any(e["name"] == "error_alert" for e in bob_events)

    # Alice deletes her message -> Success
    s_alice.emit("delete_message", {"message_id": msg_id})

    # Bob receives message_deleted broadcast
    bob_events_2 = s_bob.get_received()
    del_events = [e for e in bob_events_2 if e["name"] == "message_deleted"]
    assert len(del_events) == 1
    assert del_events[0]["args"][0]["message_id"] == msg_id

    # Verify soft deleted in database
    with app.app_context():
        db_msg = Message.query.get(msg_id)
        assert db_msg.is_deleted is True

    s_alice.disconnect()
    s_bob.disconnect()


def test_realtime_typing_indicator(app, multi_user_setup):
    """
    C. Real-time features - Typing indicator:
    When Alice types, Bob in the same conversation receives `user_typing`.
    Alice does not receive her own typing event (include_self=False).
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        db.session.commit()
        conv_id = conv.id

    s_alice = socketio.test_client(app, flask_test_client=multi_user_setup["client_alice"])
    s_bob = socketio.test_client(app, flask_test_client=multi_user_setup["client_bob"])
    s_alice.get_received()
    s_bob.get_received()

    s_alice.emit("join_conversation", {"conversation_id": conv_id})
    s_bob.emit("join_conversation", {"conversation_id": conv_id})
    s_alice.get_received()
    s_bob.get_received()

    # Alice starts typing
    s_alice.emit("typing", {"conversation_id": conv_id, "is_typing": True})

    # Alice does not get event back
    alice_events = s_alice.get_received()
    assert not any(e["name"] == "user_typing" for e in alice_events)

    # Bob receives user_typing event
    bob_events = s_bob.get_received()
    typing_events = [e for e in bob_events if e["name"] == "user_typing"]
    assert len(typing_events) == 1
    assert typing_events[0]["args"][0]["user_id"] == alice_id
    assert typing_events[0]["args"][0]["is_typing"] is True

    s_alice.disconnect()
    s_bob.disconnect()


def test_realtime_read_receipts(app, multi_user_setup):
    """
    C. Real-time features - Read receipts:
    Bob emits `read_receipt` for Alice's message.
    Server records ReadReceipt and emits `message_read` back to room.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        msg = Message(
            conversation_id=conv.id,
            sender_id=alice_id,
            content="Please read this assignment prompt.",
        )
        db.session.add(msg)
        db.session.commit()
        conv_id = conv.id
        msg_id = msg.id

    s_alice = socketio.test_client(app, flask_test_client=multi_user_setup["client_alice"])
    s_bob = socketio.test_client(app, flask_test_client=multi_user_setup["client_bob"])
    s_alice.get_received()
    s_bob.get_received()

    s_alice.emit("join_conversation", {"conversation_id": conv_id})
    s_bob.emit("join_conversation", {"conversation_id": conv_id})
    s_alice.get_received()
    s_bob.get_received()

    # Bob reads the message
    s_bob.emit("read_receipt", {
        "conversation_id": conv_id,
        "message_id": msg_id,
    })

    # Alice receives message_read notification
    alice_events = s_alice.get_received()
    read_events = [e for e in alice_events if e["name"] == "message_read"]
    assert len(read_events) == 1
    assert read_events[0]["args"][0]["message_id"] == msg_id
    assert read_events[0]["args"][0]["user_id"] == bob_id

    # Verify ReadReceipt in database
    with app.app_context():
        receipt = ReadReceipt.query.filter_by(message_id=msg_id, user_id=bob_id).first()
        assert receipt is not None
        assert receipt.read_at is not None

    s_alice.disconnect()
    s_bob.disconnect()


def test_realtime_reactions_toggle(app, multi_user_setup):
    """
    Message reactions:
    Adding an emoji adds it to the message; sending the same emoji again removes it (toggle).
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Alice & Bob")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        msg = Message(
            conversation_id=conv.id,
            sender_id=alice_id,
            content="Let's celebrate passing all tests! 🎉",
        )
        db.session.add(msg)
        db.session.commit()
        conv_id = conv.id
        msg_id = msg.id

    s_bob = socketio.test_client(app, flask_test_client=multi_user_setup["client_bob"])
    s_bob.get_received()
    s_bob.emit("join_conversation", {"conversation_id": conv_id})
    s_bob.get_received()

    # 1. Bob adds reaction '🔥'
    s_bob.emit("add_reaction", {"message_id": msg_id, "reaction": "🔥"})
    bob_events = s_bob.get_received()
    rx_events = [e for e in bob_events if e["name"] == "reaction_updated"]
    assert len(rx_events) == 1
    reactions = rx_events[0]["args"][0]["reactions"]
    assert "🔥" in reactions
    assert len(reactions["🔥"]) == 1

    # 2. Bob toggles the same reaction '🔥' -> removed
    s_bob.emit("add_reaction", {"message_id": msg_id, "reaction": "🔥"})
    bob_events_2 = s_bob.get_received()
    rx_events_2 = [e for e in bob_events_2 if e["name"] == "reaction_updated"]
    assert len(rx_events_2) == 1
    reactions_2 = rx_events_2[0]["args"][0]["reactions"]
    assert "🔥" not in reactions_2 or len(reactions_2["🔥"]) == 0

    s_bob.disconnect()


def test_cursor_pagination_messages_api(app, multi_user_setup):
    """
    D. Message pagination:
    Validates cursor-based pagination with `limit` and `before_id`.
    Chronological ordering is strictly preserved.
    """
    alice_id = multi_user_setup["alice_id"]
    bob_id = multi_user_setup["bob_id"]

    with app.app_context():
        conv = Conversation(type="direct", title="Pagination Channel")
        db.session.add(conv)
        db.session.flush()
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member"),
            ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member"),
        ])
        # Create 60 sequential messages
        for i in range(1, 61):
            db.session.add(
                Message(
                    conversation_id=conv.id,
                    sender_id=alice_id,
                    content=f"Numbered message #{i:03d}",
                )
            )
        db.session.commit()
        conv_id = conv.id

    client = multi_user_setup["client_alice"]

    # 1. Fetch latest 20 messages (default order reversed to chronological)
    res = client.get(f"/api/conversations/{conv_id}/messages?limit=20")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["messages"]) == 20
    assert data["has_more"] is True
    assert data["messages"][0]["content"] == "Numbered message #041"
    assert data["messages"][-1]["content"] == "Numbered message #060"

    # 2. Fetch previous batch before message #041
    oldest_id = data["messages"][0]["id"]
    res_page2 = client.get(f"/api/conversations/{conv_id}/messages?limit=20&before_id={oldest_id}")
    assert res_page2.status_code == 200
    data_page2 = res_page2.get_json()
    assert len(data_page2["messages"]) == 20
    assert data_page2["has_more"] is True
    assert data_page2["messages"][0]["content"] == "Numbered message #021"
    assert data_page2["messages"][-1]["content"] == "Numbered message #040"

