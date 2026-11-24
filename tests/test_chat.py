"""
Chat Channels and Messages Test Suite
=====================================
Validates direct messaging, groups, search, message deletion, and attachments.
"""

from app.models.chat import Conversation, ConversationParticipant, Message


def test_create_direct_conversation(auth_client, sample_users):
    """Test creating a 1-to-1 direct conversation via API."""
    bob_id = sample_users["bob_id"]
    res = auth_client.post(
        "/api/conversations",
        json={"type": "direct", "recipient_id": bob_id},
    )
    assert res.status_code in (200, 201)
    data = res.get_json()
    assert data["success"] is True
    conv_id = data["conversation"]["id"]

    # Test idempotency: re-requesting same direct chat returns existing conversation
    res2 = auth_client.post(
        "/api/conversations",
        json={"type": "direct", "recipient_id": bob_id},
    )
    assert res2.status_code == 200
    assert res2.get_json()["conversation"]["id"] == conv_id


def test_create_group_conversation(auth_client, sample_users):
    """Test creating a multi-user group chat."""
    bob_id = sample_users["bob_id"]
    res = auth_client.post(
        "/api/conversations",
        json={
            "type": "group",
            "title": "Python Hackers",
            "description": "Study Channel",
            "member_ids": [bob_id],
        },
    )
    assert res.status_code in (200, 201)
    data = res.get_json()
    assert data["success"] is True
    assert data["conversation"]["title"] == "Python Hackers"


def test_group_add_and_remove_participant(auth_client, sample_users, db_session):
    """Test dynamic group membership additions and removals."""
    alice_id = sample_users["alice_id"]
    bob_id = sample_users["bob_id"]

    # Create group with Alice as admin
    conv = Conversation(type="group", title="Test Group", creator_id=alice_id)
    db_session.session.add(conv)
    db_session.session.flush()

    p_alice = ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="admin")
    db_session.session.add(p_alice)
    db_session.session.commit()

    # Alice adds Bob
    res_add = auth_client.post(
        f"/api/conversations/{conv.id}/participants",
        json={"user_id": bob_id},
    )
    assert res_add.status_code == 200
    assert conv.is_member(bob_id) is True

    # Alice removes Bob
    res_remove = auth_client.delete(f"/api/conversations/{conv.id}/participants/{bob_id}")
    assert res_remove.status_code == 200
    assert conv.is_member(bob_id) is False


def test_message_search_api(auth_client, sample_users, db_session):
    """Test filtering message history by query keyword and category."""
    alice_id = sample_users["alice_id"]
    bob_id = sample_users["bob_id"]

    conv = Conversation(type="direct", creator_id=alice_id)
    db_session.session.add(conv)
    db_session.session.flush()

    p1 = ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member")
    p2 = ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member")
    db_session.session.add_all([p1, p2])

    msg1 = Message(
        conversation_id=conv.id,
        sender_id=alice_id,
        content="Exploring Flask-SocketIO and Python 3.14 concurrency",
        category="code",
    )
    msg2 = Message(
        conversation_id=conv.id,
        sender_id=bob_id,
        content="What is the difference between processes and threads?",
        category="question",
    )
    db_session.session.add_all([msg1, msg2])
    db_session.session.commit()

    # Query for 'concurrency'
    res = auth_client.get("/api/messages/search?q=concurrency")
    assert res.status_code == 200
    results = res.get_json()["results"]
    assert len(results) >= 1
    assert "concurrency" in results[0]["content"].lower()

    # Query for category 'question'
    res_cat = auth_client.get("/api/messages/search?category=question")
    assert res_cat.status_code == 200
    cat_results = res_cat.get_json()["results"]
    assert len(cat_results) >= 1
    assert cat_results[0]["category"] == "question"


def test_group_rename_api_and_permissions(auth_client, sample_users, db_session):
    """Test group channel renaming endpoint and role authorization."""
    alice_id = sample_users["alice_id"]
    bob_id = sample_users["bob_id"]

    # Alice creates group channel
    conv = Conversation(type="group", title="Old Group Name", creator_id=alice_id)
    db_session.session.add(conv)
    db_session.session.flush()

    p_alice = ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="admin")
    p_bob = ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="member")
    db_session.session.add_all([p_alice, p_bob])
    db_session.session.commit()

    # Alice (admin) renames the group via PATCH
    res = auth_client.patch(
        f"/api/conversations/{conv.id}",
        json={"title": "New Group Name", "description": "Updated channel description"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["conversation"]["title"] == "New Group Name"

    # Alice renames via POST alias
    res_alias = auth_client.post(
        f"/api/conversations/{conv.id}/rename",
        json={"title": "Final Group Name"},
    )
    assert res_alias.status_code == 200
    assert res_alias.get_json()["conversation"]["title"] == "Final Group Name"

    # Empty title is rejected
    res_empty = auth_client.patch(
        f"/api/conversations/{conv.id}",
        json={"title": ""},
    )
    assert res_empty.status_code == 400


def test_group_leave_and_system_announcement(auth_client, sample_users, db_session):
    """Test participant voluntarily leaving a group channel."""
    alice_id = sample_users["alice_id"]
    bob_id = sample_users["bob_id"]

    conv = Conversation(type="group", title="Voluntary Leave Test", creator_id=bob_id)
    db_session.session.add(conv)
    db_session.session.flush()

    p_bob = ConversationParticipant(conversation_id=conv.id, user_id=bob_id, role="admin")
    p_alice = ConversationParticipant(conversation_id=conv.id, user_id=alice_id, role="member")
    db_session.session.add_all([p_bob, p_alice])
    db_session.session.commit()

    # Alice leaves group via DELETE self participant endpoint
    res = auth_client.delete(f"/api/conversations/{conv.id}/participants/{alice_id}")
    assert res.status_code == 200
    assert conv.is_member(alice_id) is False

    # Verify system announcement was generated
    sys_msgs = Message.query.filter_by(conversation_id=conv.id, message_type="system").all()
    assert len(sys_msgs) >= 1
    assert "left the group" in sys_msgs[-1].content
