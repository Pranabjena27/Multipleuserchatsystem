"""
ConnectX Realistic Seed Data Generator
======================================
Pre-populates sample academic accounts, channels, discussion threads,
sentiment-scored dialogues, and system announcements.
"""

from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.chat import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReaction,
    ReadReceipt,
)
from app.models.audit import AuditLog, SystemAnnouncement
from app.python_features.sentiment import SentimentAnalyzer
from app.python_features.categorizer import MessageCategorizer

app = create_app("development")
sentiment_eng = SentimentAnalyzer()
categorizer_eng = MessageCategorizer()


def seed_database():
    with app.app_context():
        print("[Seed] Resetting and re-creating database tables...")
        db.drop_all()
        db.create_all()

        now = datetime.now(timezone.utc)

        # 1. Create Core Users
        users_info = [
            {
                "username": "admin",
                "email": "admin@connectx.local",
                "full_name": "Dr. Rajesh Admin",
                "role": "admin",
                "bio": "Lead System Architect & Academic Proctor.",
                "status_message": "Monitoring system health",
                "password": "Admin@123456",
            },
            {
                "username": "prof_sharma",
                "email": "sharma@university.edu",
                "full_name": "Prof. A. K. Sharma",
                "role": "moderator",
                "bio": "Professor of Computer Science & Engineering.",
                "status_message": "Office hours: Tue/Thu 3-5 PM",
                "password": "Prof@123456",
            },
            {
                "username": "alice",
                "email": "alice@student.university.edu",
                "full_name": "Alice Cooper",
                "role": "user",
                "bio": "B.Tech 3rd Semester CSE. Passionate about Python, Flask & Socket.IO.",
                "status_message": "Writing test cases for ConnectX 🚀",
                "password": "Alice@123456",
            },
            {
                "username": "bob",
                "email": "bob@student.university.edu",
                "full_name": "Bob Martin",
                "role": "user",
                "bio": "B.Tech CSE student. Backend enthusiast & database optimizer.",
                "status_message": "Working on SQLite indexing",
                "password": "Bob@123456",
            },
            {
                "username": "charlie",
                "email": "charlie@student.university.edu",
                "full_name": "Charlie Davis",
                "role": "user",
                "bio": "Frontend coder, CSS flexbox/grid fan, and UI designer.",
                "status_message": "Testing dark mode themes ✨",
                "password": "Charlie@123456",
            },
        ]

        created_users = {}
        for u_data in users_info:
            u = User(
                username=u_data["username"],
                email=u_data["email"],
                full_name=u_data["full_name"],
                role=u_data["role"],
                bio=u_data["bio"],
                status_message=u_data["status_message"],
                avatar="default_avatar.svg",
                is_online=True,
            )
            u.set_password(u_data["password"])
            db.session.add(u)
            created_users[u_data["username"]] = u

        db.session.commit()
        print(f"[Seed] Created {len(created_users)} verified user accounts.")

        # 2. Create System Announcements
        ann1 = SystemAnnouncement(
            title="Project Submission Notice",
            content="Final code defense and viva examinations commence next week. Ensure all pytest test cases pass.",
            priority="info",
            created_by_id=created_users["admin"].id,
            is_active=True,
        )
        ann2 = SystemAnnouncement(
            title="Real-Time WebSocket Optimization Complete",
            content="ConnectX now runs thread-safe presence state managers and automatic entropy-based spam detection.",
            priority="warning",
            created_by_id=created_users["admin"].id,
            is_active=True,
        )
        db.session.add_all([ann1, ann2])
        db.session.commit()

        # 3. Create Group Conversation: "Project Discussion Group"
        group_conv = Conversation(
            type="group",
            title="Project Discussion Group",
            description="Official project discussion channel.",
            icon="default_group.svg",
            creator_id=created_users["prof_sharma"].id,
            created_at=now - timedelta(days=2),
            updated_at=now,
        )
        db.session.add(group_conv)
        db.session.flush()

        # Enroll participants in group
        for u in [created_users["prof_sharma"], created_users["alice"], created_users["bob"], created_users["charlie"]]:
            role = "admin" if u.username == "prof_sharma" else "member"
            p = ConversationParticipant(
                conversation_id=group_conv.id,
                user_id=u.id,
                role=role,
                joined_at=now - timedelta(days=2),
            )
            db.session.add(p)

        db.session.commit()

        # Group Discussion Dialogue with diverse semantic categories
        group_messages = [
            (
                "prof_sharma",
                "Welcome everyone to the official project discussion channel!",
                now - timedelta(hours=5),
            ),
            (
                "alice",
                "Hello Professor! We have structured ConnectX with an application factory and modular blueprints.",
                now - timedelta(hours=4, minutes=45),
            ),
            (
                "bob",
                "How do I configure the SQLite database in-memory for the automated Pytest fixtures?",
                now - timedelta(hours=4, minutes=30),
            ),
            (
                "alice",
                "You can set SQLALCHEMY_DATABASE_URI to `sqlite:///:memory:` in TestingConfig! Here is the code snippet:\n```python\nclass TestingConfig(Config):\n    TESTING = True\n    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'\n```",
                now - timedelta(hours=4, minutes=15),
            ),
            (
                "bob",
                "That works perfectly! Thank you so much Alice, that solved the test isolation issue completely! 🎉",
                now - timedelta(hours=3, minutes=50),
            ),
            (
                "charlie",
                "Action item: I will finalize the responsive 3-pane chat interface and dark mode CSS variables by tonight.",
                now - timedelta(hours=3, minutes=20),
            ),
            (
                "prof_sharma",
                "Excellent work team. Make sure your Python message intelligence algorithms run without external paid APIs.",
                now - timedelta(hours=2),
            ),
            (
                "alice",
                "Yes Professor! We implemented pure Python VADER sentiment analysis, Shannon entropy spam detection, and extractive TF-IDF summarization.",
                now - timedelta(hours=1, minutes=10),
            ),
        ]

        for sender_name, text, ts in group_messages:
            sentiment = sentiment_eng.analyze(text)
            category, _ = categorizer_eng.classify(text)
            msg = Message(
                conversation_id=group_conv.id,
                sender_id=created_users[sender_name].id,
                content=text,
                message_type="text",
                category=category,
                sentiment_score=sentiment.score,
                sentiment_label=sentiment.label,
                is_spam=False,
                created_at=ts,
            )
            db.session.add(msg)

        db.session.commit()

        # 4. Create 1-to-1 Direct Conversation: Alice <-> Bob
        direct_conv = Conversation(
            type="direct",
            creator_id=created_users["alice"].id,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(minutes=15),
        )
        db.session.add(direct_conv)
        db.session.flush()

        p1 = ConversationParticipant(
            conversation_id=direct_conv.id,
            user_id=created_users["alice"].id,
            role="member",
        )
        p2 = ConversationParticipant(
            conversation_id=direct_conv.id,
            user_id=created_users["bob"].id,
            role="member",
        )
        db.session.add_all([p1, p2])
        db.session.commit()

        direct_dialogue = [
            ("alice", "Hey Bob! Have you checked the recursive thread hierarchy logic in processor.py?", now - timedelta(hours=2)),
            ("bob", "Yes, Alice! The `build_nested_thread_tree` function handles arbitrary reply depths recursively. It works nicely!", now - timedelta(hours=1, minutes=40)),
            ("alice", "Awesome! Let us run `pytest` to verify all test suites before the lab demonstration.", now - timedelta(minutes=15)),
        ]

        for sender_name, text, ts in direct_dialogue:
            sentiment = sentiment_eng.analyze(text)
            category, _ = categorizer_eng.classify(text)
            msg = Message(
                conversation_id=direct_conv.id,
                sender_id=created_users[sender_name].id,
                content=text,
                category=category,
                sentiment_score=sentiment.score,
                sentiment_label=sentiment.label,
                created_at=ts,
            )
            db.session.add(msg)

        db.session.commit()

        # Add sample reaction
        latest_direct_msg = Message.query.filter_by(conversation_id=direct_conv.id).first()
        if latest_direct_msg:
            rx = MessageReaction(
                message_id=latest_direct_msg.id,
                user_id=created_users["bob"].id,
                reaction="🚀",
            )
            db.session.add(rx)

        # 5. Create Audit Logs
        audit1 = AuditLog(
            user_id=created_users["admin"].id,
            action="SYSTEM_INIT",
            target_type="system",
            target_id=1,
            details="ConnectX Database Initialized with Academic Seed Data",
            ip_address="127.0.0.1",
        )
        db.session.add(audit1)
        db.session.commit()

        print("[Seed] Successfully populated ConnectX with realistic channels, messages, and users!")


if __name__ == "__main__":
    seed_database()
