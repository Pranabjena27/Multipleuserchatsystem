"""
Administration and Moderation Test Suite
========================================
Validates role-based authorization, user suspensions, and announcements.
"""

from app.models.user import User
from app.models.audit import SystemAnnouncement


def test_regular_user_cannot_access_admin_dashboard(auth_client):
    """Ensure non-admin users receive 302 redirect / 403 access denial."""
    res = auth_client.get("/admin/", follow_redirects=False)
    # Redirects to home page with danger flash
    assert res.status_code == 302


def test_admin_can_access_dashboard(admin_client):
    """Ensure authorized administrator can view the dashboard."""
    res = admin_client.get("/admin/")
    assert res.status_code == 200
    assert b"Administration" in res.data
    assert b"TOTAL USERS" in res.data


def test_admin_toggle_user_ban(admin_client, sample_users, db_session):
    """Test administrator suspending and reactivating an account."""
    bob_id = sample_users["bob_id"]
    bob = User.query.get(bob_id)
    assert bob.is_banned is False

    # Ban Bob
    res = admin_client.post(f"/admin/users/{bob_id}/toggle-ban", follow_redirects=True)
    assert res.status_code == 200
    bob_updated = User.query.get(bob_id)
    assert bob_updated.is_banned is True

    # Unban Bob
    res2 = admin_client.post(f"/admin/users/{bob_id}/toggle-ban", follow_redirects=True)
    assert res2.status_code == 200
    bob_restored = User.query.get(bob_id)
    assert bob_restored.is_banned is False


def test_admin_create_announcement(admin_client, db_session):
    """Test administrator publishing system announcements."""
    res = admin_client.post(
        "/admin/announcements",
        data={
            "title": "Exam Schedule",
            "content": "Lab exams will be held in Hall A.",
            "priority": "warning",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    ann = SystemAnnouncement.query.filter_by(title="Exam Schedule").first()
    assert ann is not None
    assert ann.priority == "warning"
    assert ann.is_active is True
