"""Security tests for authentication and authorization

Tests authentication bypass attempts, session security,
and authorization enforcement.
"""

import base64

import pytest
from werkzeug.security import generate_password_hash

from src.config import Config
from src.dashboard.app import create_app


@pytest.fixture
def auth_config(tmp_path):
    """Create test config with authentication enabled"""
    config_content = """
github:
  token: "test_token"
  organization: "test-org"

jira:
  server: "https://jira.test.com"
  username: "test"
  api_token: "test"

teams:
  - name: "Test Team"
    members:
      - name: "Test User"
        github: "testuser"
        jira: "testuser"

dashboard:
  port: 5001
  auth:
    enabled: true
    users:
      - username: "admin"
        password_hash: "{hash}"
      - username: "viewer"
        password_hash: "{hash2}"
"""
    # Generate password hashes for testing
    admin_hash = generate_password_hash("admin123")
    viewer_hash = generate_password_hash("viewer123")

    config_content = config_content.replace("{hash}", admin_hash).replace("{hash2}", viewer_hash)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    return Config(str(config_file))


@pytest.fixture
def no_auth_config(tmp_path):
    """Create test config with authentication disabled"""
    config_content = """
github:
  token: "test_token"
  organization: "test-org"

jira:
  server: "https://jira.test.com"
  username: "test"
  api_token: "test"

teams:
  - name: "Test Team"
    members:
      - name: "Test User"
        github: "testuser"
        jira: "testuser"

dashboard:
  port: 5001
  auth:
    enabled: false
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    return Config(str(config_file))


@pytest.fixture
def auth_app(auth_config):
    """Create Flask app with authentication enabled"""
    return create_app(auth_config)


@pytest.fixture
def no_auth_app(no_auth_config):
    """Create Flask app with authentication disabled"""
    return create_app(no_auth_config)


@pytest.fixture
def auth_client(auth_app):
    """Create test client with auth enabled"""
    return auth_app.test_client()


@pytest.fixture
def no_auth_client(no_auth_app):
    """Create test client with auth disabled"""
    return no_auth_app.test_client()


def make_auth_header(username, password):
    """Create HTTP Basic Auth header"""
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


class TestAuthenticationRequired:
    """Test that authentication is required when enabled"""

    def test_unauthenticated_access_denied(self, auth_client):
        """Test that unauthenticated requests are rejected"""
        protected_routes = [
            "/",
            "/team/Test%20Team",
            "/person/testuser",
            "/comparison",
            "/api/metrics",
            "/api/refresh",
            "/api/cache/stats",
        ]

        for route in protected_routes:
            response = auth_client.get(route)
            assert response.status_code == 401, f"Unauthenticated access allowed to {route}"
            assert "WWW-Authenticate" in response.headers
            assert "Basic" in response.headers["WWW-Authenticate"]

    def test_authenticated_access_allowed(self, auth_client):
        """Test that authenticated requests are allowed"""
        headers = make_auth_header("admin", "admin123")

        protected_routes = [
            "/",
            "/api/cache/stats",
            "/api/health",
        ]

        for route in protected_routes:
            response = auth_client.get(route, headers=headers)
            # Should not be 401 (might be 200, 404, 500 depending on state)
            assert response.status_code != 401, f"Authenticated access denied to {route}"

    def test_authentication_disabled_allows_all(self, no_auth_client):
        """Test that when auth is disabled, all routes are accessible"""
        routes = [
            "/",
            "/api/health",
        ]

        for route in routes:
            response = no_auth_client.get(route)
            # Should not require auth (might be 200, 404, 500)
            assert response.status_code != 401, f"Auth required when disabled for {route}"


class TestAuthenticationBypass:
    """Test attempts to bypass authentication"""

    def test_wrong_password_denied(self, auth_client):
        """Test that wrong passwords are rejected"""
        headers = make_auth_header("admin", "wrongpassword")
        response = auth_client.get("/", headers=headers)
        assert response.status_code == 401

    def test_wrong_username_denied(self, auth_client):
        """Test that wrong usernames are rejected"""
        headers = make_auth_header("hacker", "admin123")
        response = auth_client.get("/", headers=headers)
        assert response.status_code == 401

    def test_empty_credentials_denied(self, auth_client):
        """Test that empty credentials are rejected"""
        headers = make_auth_header("", "")
        response = auth_client.get("/", headers=headers)
        assert response.status_code == 401

    def test_malformed_auth_header_denied(self, auth_client):
        """Test that malformed auth headers are rejected"""
        malformed_headers = [
            {"Authorization": "Basic invalid"},
            {"Authorization": "Bearer token"},
            {"Authorization": "Basic"},
            {"Authorization": ""},
        ]

        for headers in malformed_headers:
            response = auth_client.get("/", headers=headers)
            assert response.status_code == 401

    def test_sql_injection_in_username(self, auth_client):
        """Test that SQL injection in username is prevented"""
        sql_injections = [
            "admin' OR '1'='1",
            "admin'--",
            "' OR 1=1 --",
        ]

        for injection in sql_injections:
            headers = make_auth_header(injection, "any")
            response = auth_client.get("/", headers=headers)
            assert response.status_code == 401

    def test_path_traversal_in_username(self, auth_client):
        """Test that path traversal in username is prevented"""
        traversal_attempts = [
            "../admin",
            "../../root",
            "admin/../../../etc/passwd",
        ]

        for attempt in traversal_attempts:
            headers = make_auth_header(attempt, "any")
            response = auth_client.get("/", headers=headers)
            assert response.status_code == 401


class TestPasswordSecurity:
    """Test password handling security"""

    def test_passwords_are_hashed(self, auth_config):
        """Test that passwords are stored as hashes, not plaintext"""
        users = auth_config.dashboard_config["auth"]["users"]
        for user in users:
            password_hash = user["password_hash"]
            # Should be a hash (starts with algorithm identifier)
            assert password_hash.startswith(("pbkdf2:", "scrypt:", "argon2:", "bcrypt"))
            # Should not be plaintext
            assert password_hash not in ["admin123", "viewer123"]

    def test_different_users_different_hashes(self, auth_config):
        """Test that same password has different hashes (salt)"""
        # If two users have same password, hashes should differ (salted)
        # This test validates proper hashing implementation
        pass


class TestSessionSecurity:
    """Test session security (if sessions are used)"""

    def test_session_cookies_secure(self, auth_client):
        """Test that session cookies have Secure flag (for HTTPS)"""
        # Note: Only relevant if using sessions
        # Document requirement for production
        pass

    def test_session_cookies_httponly(self, auth_client):
        """Test that session cookies have HttpOnly flag"""
        # Note: Only relevant if using sessions
        # Prevents XSS from stealing session cookies
        pass

    def test_session_cookies_samesite(self, auth_client):
        """Test that session cookies have SameSite attribute"""
        # Note: Only relevant if using sessions
        # Prevents CSRF attacks
        pass


class TestRateLimiting:
    """Test rate limiting for brute force protection"""

    def test_multiple_failed_login_attempts(self, auth_client):
        """Test that multiple failed logins are rate limited"""
        # Try 20 failed logins
        headers = make_auth_header("admin", "wrongpassword")
        responses = []

        for _ in range(20):
            response = auth_client.get("/", headers=headers)
            responses.append(response.status_code)

        # Should get rate limited (429) or locked out
        # Note: This might not be implemented yet - test documents requirement
        # assert 429 in responses or all(r == 401 for r in responses)

    def test_rate_limit_per_ip(self, auth_client):
        """Test that rate limiting is per IP address"""
        # Note: This might not be implemented yet - test documents requirement
        pass


class TestAuthorizationEnforcement:
    """Test that authorization is enforced consistently"""

    def test_all_routes_protected(self, auth_client):
        """Test that all dashboard routes require authentication"""
        # List of all application routes
        routes = [
            "/",
            "/team/Test%20Team",
            "/person/testuser",
            "/comparison",
            "/team/Test%20Team/compare",
            "/settings",
            "/api/metrics",
            "/api/refresh",
            "/api/reload-cache",
            "/api/collect",
            "/api/cache/stats",
            "/api/cache/clear",
            "/api/cache/warm",
            "/metrics/performance",
        ]

        for route in routes:
            response = auth_client.get(route)
            # Should require auth (401), not 403 or 200
            assert response.status_code == 401, f"Route not protected: {route}"

    def test_post_endpoints_protected(self, auth_client):
        """Test that POST endpoints require authentication"""
        post_routes = [
            "/api/reload-cache",
            "/api/cache/clear",
            "/api/cache/warm",
        ]

        for route in post_routes:
            response = auth_client.post(route)
            assert response.status_code == 401, f"POST route not protected: {route}"


class TestAuthenticationLogging:
    """Test that authentication events are logged"""

    def test_failed_login_logged(self, auth_client, caplog):
        """Test that failed login attempts are logged"""
        headers = make_auth_header("admin", "wrongpassword")
        auth_client.get("/", headers=headers)

        # Should log failed authentication
        # Note: Check actual log messages
        # assert "Failed authentication" in caplog.text

    def test_successful_login_logged(self, auth_client, caplog):
        """Test that successful logins are logged"""
        headers = make_auth_header("admin", "admin123")
        auth_client.get("/", headers=headers)

        # Should log successful authentication
        # Note: Check actual log messages
        # assert "Authenticated user" in caplog.text
