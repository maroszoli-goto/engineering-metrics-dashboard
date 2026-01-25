"""Authentication module for Team Metrics Dashboard.

Provides HTTP Basic Authentication for securing the dashboard.
Authentication is optional and disabled by default for backward compatibility.

Usage:
    from src.dashboard.auth import AuthManager

    # Create auth manager and initialize with app
    auth_manager = AuthManager()
    auth_manager.init_app(app, config)

    # Protect a route
    @app.route('/secure')
    @auth_manager.require_auth
    def secure_route():
        return "This requires authentication"

    # Or use the decorator directly (pulls from current_app)
    from src.dashboard.auth import require_auth

    @app.route('/secure')
    @require_auth
    def secure_route():
        return "This requires authentication"
"""

import functools
import logging
from typing import Callable, Dict

from flask import Flask, Response, current_app, request
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages HTTP Basic Authentication for Flask app.

    This class provides instance-based authentication management,
    allowing multiple Flask app instances to have independent auth configs.
    """

    def __init__(self):
        """Initialize AuthManager with default disabled state."""
        self.enabled = False
        self.users: Dict[str, str] = {}  # username -> password_hash

    def init_app(self, app: Flask, config) -> None:
        """Initialize authentication system for a Flask app.

        Args:
            app: Flask application instance
            config: Config object with dashboard.auth settings

        Note:
            Authentication is disabled by default. Enable via config:
            dashboard:
              auth:
                enabled: true
                users:
                  - username: admin
                    password_hash: pbkdf2:sha256:...
        """
        # Check if auth is configured and enabled
        dashboard_config = config.dashboard_config
        auth_config = dashboard_config.get("auth", {})

        self.enabled = auth_config.get("enabled", False)

        if self.enabled:
            # Load users from config
            users = auth_config.get("users", [])
            self.users = {user["username"]: user["password_hash"] for user in users}

            if not self.users:
                logger.warning("Authentication enabled but no users configured. All requests will be denied.")
            else:
                logger.info(f"Authentication enabled with {len(self.users)} user(s)")
        else:
            logger.info("Authentication disabled")

        # Store auth manager in app extensions
        app.extensions["auth_manager"] = self

    def require_auth(self, func: Callable) -> Callable:
        """Decorator to require HTTP Basic Authentication for a route.

        If authentication is disabled, this decorator has no effect and the
        route is accessible without authentication.

        Args:
            func: Route function to protect

        Returns:
            Wrapped function that checks authentication

        Example:
            @app.route('/secure')
            @auth_manager.require_auth
            def secure_route():
                return "Protected content"
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If auth is disabled, allow access
            if not self.enabled:
                return func(*args, **kwargs)

            # Check authentication
            auth = request.authorization

            if not auth or not auth.username or not auth.password:
                return self._auth_required_response()

            # Verify credentials
            if self._verify_credentials(auth.username, auth.password):
                logger.debug(f"Authenticated user: {auth.username}")
                return func(*args, **kwargs)
            else:
                logger.warning(f"Failed authentication attempt for user: {auth.username}")
                return self._auth_required_response()

        return wrapper

    def _verify_credentials(self, username: str, password: str) -> bool:
        """Verify username and password against configured users.

        Args:
            username: Username to verify
            password: Plain text password to check

        Returns:
            True if credentials are valid, False otherwise
        """
        if username not in self.users:
            return False

        password_hash = self.users[username]
        return check_password_hash(password_hash, password)

    def _auth_required_response(self) -> Response:
        """Generate HTTP 401 response requesting authentication.

        Returns:
            Response object with 401 status and WWW-Authenticate header
        """
        return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="Team Metrics Dashboard"'})

    def is_enabled(self) -> bool:
        """Check if authentication is currently enabled.

        Returns:
            True if authentication is enabled, False otherwise
        """
        return self.enabled

    def get_authenticated_users(self) -> list:
        """Get list of configured usernames (for admin/debugging).

        Returns:
            List of usernames (without password hashes)
        """
        return list(self.users.keys())


# Convenience decorator that uses current_app's auth manager
def require_auth(func: Callable) -> Callable:
    """Decorator to require HTTP Basic Authentication for a route.

    This is a convenience wrapper that uses the auth manager from
    current_app.extensions['auth_manager']. Use this when you want
    to decorate routes without having direct access to the AuthManager instance.

    If authentication is disabled, this decorator has no effect.

    Args:
        func: Route function to protect

    Returns:
        Wrapped function that checks authentication

    Example:
        @app.route('/secure')
        @require_auth
        def secure_route():
            return "Protected content"
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get auth manager from current app
        auth_manager = current_app.extensions.get("auth_manager")

        if not auth_manager:
            # No auth manager configured - allow access (backward compatibility)
            logger.warning("require_auth decorator used but no AuthManager configured")
            return func(*args, **kwargs)

        # Use the auth manager's require_auth logic
        return auth_manager.require_auth(func)(*args, **kwargs)

    return wrapper


# Backward compatibility functions (use current_app's auth manager)
def init_auth(app: Flask, config) -> AuthManager:
    """Initialize authentication system (backward compatibility wrapper).

    Args:
        app: Flask application instance
        config: Config object with dashboard.auth settings

    Returns:
        AuthManager instance

    Note:
        This function is provided for backward compatibility.
        Prefer creating AuthManager directly and calling init_app().
    """
    auth_manager = AuthManager()
    auth_manager.init_app(app, config)
    return auth_manager


def is_auth_enabled() -> bool:
    """Check if authentication is currently enabled (backward compatibility).

    Returns:
        True if authentication is enabled, False otherwise
    """
    auth_manager = current_app.extensions.get("auth_manager")
    return auth_manager.is_enabled() if auth_manager else False


def get_authenticated_users() -> list:
    """Get list of configured usernames (backward compatibility).

    Returns:
        List of usernames (without password hashes)
    """
    auth_manager = current_app.extensions.get("auth_manager")
    return auth_manager.get_authenticated_users() if auth_manager else []
