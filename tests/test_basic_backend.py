"""
Basic Backend Routes Verification Test Suite
============================================
Validates fundamental backend routes: Home, Login, Registration, Dashboard, and Health-check.
"""


def test_health_check_endpoint(client, db_session):
    """Test /health returns 200 with healthy status and database connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data


def test_home_route_unauthenticated(client, db_session):
    """Test unauthenticated user accessing home route redirects to /auth/login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_login_route_accessible(client, db_session):
    """Test /auth/login page renders with HTTP 200 and form inputs."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data
    assert b"login_identifier" in response.data


def test_registration_route_accessible(client, db_session):
    """Test /auth/register page renders with HTTP 200 and registration form."""
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b"Create ConnectX Account" in response.data
    assert b"username" in response.data


def test_dashboard_route_redirect(auth_client):
    """Test /dashboard route for authenticated user redirects to main workstation."""
    response = auth_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] in ("/", "/admin/")

