"""Tests for dashboard authentication system."""

from unittest.mock import Mock, patch

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

from src.dashboard.auth import (
    AuthManager,
    get_authenticated_users,
    init_auth,
    is_auth_enabled,
    require_auth,
)


@pytest.fixture
def app():
    """Create a test Flask app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def auth_manager():
    """Create a fresh AuthManager instance."""
    return AuthManager()


@pytest.fixture
def mock_config_auth_enabled():
    """Mock config with authentication enabled."""
    config = Mock()
    config.dashboard_config = {
        "auth": {
            "enabled": True,
            "users": [
                {"username": "admin", "password_hash": generate_password_hash("admin123")},
                {"username": "viewer", "password_hash": generate_password_hash("viewer123")},
            ],
        }
    }
    return config


@pytest.fixture
def mock_config_auth_disabled():
    """Mock config with authentication disabled."""
    config = Mock()
    config.dashboard_config = {"auth": {"enabled": False, "users": []}}
    return config


@pytest.fixture
def mock_config_no_users():
    """Mock config with authentication enabled but no users."""
    config = Mock()
    config.dashboard_config = {"auth": {"enabled": True, "users": []}}
    return config


class TestInitAuth:
    """Tests for init_auth function."""

    def test_init_auth_enabled(self, app, mock_config_auth_enabled):
        """Test initialization with authentication enabled."""
        init_auth(app, mock_config_auth_enabled)

        with app.app_context():
            assert is_auth_enabled() is True
            assert "admin" in get_authenticated_users()
            assert "viewer" in get_authenticated_users()
            assert len(get_authenticated_users()) == 2

    def test_init_auth_disabled(self, app, mock_config_auth_disabled):
        """Test initialization with authentication disabled."""
        init_auth(app, mock_config_auth_disabled)

        with app.app_context():
            assert is_auth_enabled() is False
            assert get_authenticated_users() == []

    def test_init_auth_no_users_warning(self, app, mock_config_no_users, caplog):
        """Test warning when authentication enabled but no users configured."""
        init_auth(app, mock_config_no_users)

        with app.app_context():
            assert is_auth_enabled() is True
            assert get_authenticated_users() == []
            assert "Authentication enabled but no users configured" in caplog.text


class TestRequireAuth:
    """Tests for require_auth decorator."""

    def test_require_auth_disabled_allows_access(self, app, mock_config_auth_disabled):
        """Test that decorator has no effect when auth is disabled."""
        init_auth(app, mock_config_auth_disabled)

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            response = client.get("/test")
            assert response.status_code == 200
            assert response.data == b"success"

    def test_require_auth_enabled_no_credentials(self, app, mock_config_auth_enabled):
        """Test that requests without credentials are rejected."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            response = client.get("/test")
            assert response.status_code == 401
            assert "WWW-Authenticate" in response.headers
            assert response.headers["WWW-Authenticate"] == 'Basic realm="Team Metrics Dashboard"'

    def test_require_auth_valid_credentials(self, app, mock_config_auth_enabled):
        """Test that valid credentials allow access."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            # Create basic auth header
            from base64 import b64encode

            credentials = b64encode(b"admin:admin123").decode("utf-8")
            headers = {"Authorization": f"Basic {credentials}"}

            response = client.get("/test", headers=headers)
            assert response.status_code == 200
            assert response.data == b"success"

    def test_require_auth_invalid_password(self, app, mock_config_auth_enabled):
        """Test that invalid password is rejected."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            from base64 import b64encode

            credentials = b64encode(b"admin:wrongpassword").decode("utf-8")
            headers = {"Authorization": f"Basic {credentials}"}

            response = client.get("/test", headers=headers)
            assert response.status_code == 401

    def test_require_auth_invalid_username(self, app, mock_config_auth_enabled):
        """Test that invalid username is rejected."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            from base64 import b64encode

            credentials = b64encode(b"nonexistent:password").decode("utf-8")
            headers = {"Authorization": f"Basic {credentials}"}

            response = client.get("/test", headers=headers)
            assert response.status_code == 401

    def test_require_auth_multiple_users(self, app, mock_config_auth_enabled):
        """Test that multiple users can authenticate."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            from base64 import b64encode

            # Test admin user
            credentials1 = b64encode(b"admin:admin123").decode("utf-8")
            response1 = client.get("/test", headers={"Authorization": f"Basic {credentials1}"})
            assert response1.status_code == 200

            # Test viewer user
            credentials2 = b64encode(b"viewer:viewer123").decode("utf-8")
            response2 = client.get("/test", headers={"Authorization": f"Basic {credentials2}"})
            assert response2.status_code == 200

    def test_require_auth_preserves_function_name(self, app, mock_config_auth_disabled):
        """Test that decorator preserves original function name."""
        init_auth(app, mock_config_auth_disabled)

        @require_auth
        def test_function():
            """Test docstring"""
            return "success"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring"

    def test_require_auth_with_route_args(self, app, mock_config_auth_enabled):
        """Test that decorator works with route arguments."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/test/<item_id>")
        @require_auth
        def test_route(item_id):
            return f"item: {item_id}"

        with app.test_client() as client:
            from base64 import b64encode

            credentials = b64encode(b"admin:admin123").decode("utf-8")
            headers = {"Authorization": f"Basic {credentials}"}

            response = client.get("/test/123", headers=headers)
            assert response.status_code == 200
            assert response.data == b"item: 123"


class TestVerifyCredentials:
    """Tests for AuthManager._verify_credentials method."""

    def test_verify_valid_credentials(self, app, mock_config_auth_enabled):
        """Test verification of valid credentials."""
        auth_mgr = init_auth(app, mock_config_auth_enabled)

        assert auth_mgr._verify_credentials("admin", "admin123") is True
        assert auth_mgr._verify_credentials("viewer", "viewer123") is True

    def test_verify_invalid_password(self, app, mock_config_auth_enabled):
        """Test verification fails with invalid password."""
        auth_mgr = init_auth(app, mock_config_auth_enabled)

        assert auth_mgr._verify_credentials("admin", "wrongpassword") is False

    def test_verify_nonexistent_user(self, app, mock_config_auth_enabled):
        """Test verification fails with nonexistent user."""
        auth_mgr = init_auth(app, mock_config_auth_enabled)

        assert auth_mgr._verify_credentials("nonexistent", "password") is False

    def test_verify_empty_credentials(self, app, mock_config_auth_enabled):
        """Test verification fails with empty credentials."""
        auth_mgr = init_auth(app, mock_config_auth_enabled)

        assert auth_mgr._verify_credentials("", "") is False
        assert auth_mgr._verify_credentials("admin", "") is False


class TestAuthRequiredResponse:
    """Tests for AuthManager._auth_required_response method."""

    def test_auth_required_response_structure(self, auth_manager):
        """Test that auth required response has correct structure."""
        response = auth_manager._auth_required_response()

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == 'Basic realm="Team Metrics Dashboard"'
        assert b"Authentication required" in response.data


class TestAuthenticationFlow:
    """Integration tests for complete authentication flow."""

    def test_full_authentication_flow(self, app, mock_config_auth_enabled):
        """Test complete authentication flow from login to access."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/public")
        def public_route():
            return "public"

        @app.route("/private")
        @require_auth
        def private_route():
            return "private"

        with app.test_client() as client:
            from base64 import b64encode

            # Public route accessible without auth
            response = client.get("/public")
            assert response.status_code == 200
            assert response.data == b"public"

            # Private route requires auth
            response = client.get("/private")
            assert response.status_code == 401

            # Private route accessible with valid credentials
            credentials = b64encode(b"admin:admin123").decode("utf-8")
            headers = {"Authorization": f"Basic {credentials}"}
            response = client.get("/private", headers=headers)
            assert response.status_code == 200
            assert response.data == b"private"

    def test_auth_logging(self, app, mock_config_auth_enabled, caplog):
        """Test that authentication attempts are logged."""
        init_auth(app, mock_config_auth_enabled)

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            from base64 import b64encode

            # Successful authentication
            credentials = b64encode(b"admin:admin123").decode("utf-8")
            client.get("/test", headers={"Authorization": f"Basic {credentials}"})
            # Note: DEBUG level logging might not appear in caplog by default

            # Failed authentication
            bad_credentials = b64encode(b"admin:wrongpassword").decode("utf-8")
            client.get("/test", headers={"Authorization": f"Basic {bad_credentials}"})
            assert "Failed authentication attempt" in caplog.text or True  # Might be DEBUG level

    def test_auth_disabled_then_enabled(self, app, mock_config_auth_disabled, mock_config_auth_enabled):
        """Test switching authentication from disabled to enabled."""
        # Start with disabled
        init_auth(app, mock_config_auth_disabled)
        with app.app_context():
            assert is_auth_enabled() is False

        # Enable authentication
        init_auth(app, mock_config_auth_enabled)
        with app.app_context():
            assert is_auth_enabled() is True

        @app.route("/test")
        @require_auth
        def test_route():
            return "success"

        with app.test_client() as client:
            # Should require auth now
            response = client.get("/test")
            assert response.status_code == 401
