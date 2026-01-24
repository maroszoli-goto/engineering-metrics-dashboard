"""Authentication module for Team Metrics Dashboard.

Provides HTTP Basic Authentication for securing the dashboard.
Authentication is optional and disabled by default for backward compatibility.

Usage:
    from src.dashboard.auth import require_auth, init_auth

    # Initialize authentication
    auth = init_auth(app, config)

    # Protect a route
    @app.route('/secure')
    @require_auth
    def secure_route():
        return "This requires authentication"
"""

import functools
import logging
from typing import Callable, Optional

from flask import Flask, Response, request
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)

# Global auth configuration
_auth_enabled = False
_auth_users = {}


def init_auth(app: Flask, config) -> None:
    """Initialize authentication system.

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
    global _auth_enabled, _auth_users

    # Check if auth is configured and enabled
    dashboard_config = config.dashboard_config
    auth_config = dashboard_config.get("auth", {})

    _auth_enabled = auth_config.get("enabled", False)

    if _auth_enabled:
        # Load users from config
        users = auth_config.get("users", [])
        _auth_users = {user["username"]: user["password_hash"] for user in users}

        if not _auth_users:
            logger.warning("Authentication enabled but no users configured. All requests will be denied.")
        else:
            logger.info(f"Authentication enabled with {len(_auth_users)} user(s)")
    else:
        logger.info("Authentication disabled")


def require_auth(func: Callable) -> Callable:
    """Decorator to require HTTP Basic Authentication for a route.

    If authentication is disabled, this decorator has no effect and the
    route is accessible without authentication.

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
        # If auth is disabled, allow access
        if not _auth_enabled:
            return func(*args, **kwargs)

        # Check authentication
        auth = request.authorization

        if not auth:
            return _auth_required_response()

        # Verify credentials
        if _verify_credentials(auth.username, auth.password):
            logger.debug(f"Authenticated user: {auth.username}")
            return func(*args, **kwargs)
        else:
            logger.warning(f"Failed authentication attempt for user: {auth.username}")
            return _auth_required_response()

    return wrapper


def _verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against configured users.

    Args:
        username: Username to verify
        password: Plain text password to check

    Returns:
        True if credentials are valid, False otherwise
    """
    if username not in _auth_users:
        return False

    password_hash = _auth_users[username]
    return check_password_hash(password_hash, password)


def _auth_required_response() -> Response:
    """Generate HTTP 401 response requesting authentication.

    Returns:
        Response object with 401 status and WWW-Authenticate header
    """
    return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="Team Metrics Dashboard"'})


def is_auth_enabled() -> bool:
    """Check if authentication is currently enabled.

    Returns:
        True if authentication is enabled, False otherwise
    """
    return _auth_enabled


def get_authenticated_users() -> list:
    """Get list of configured usernames (for admin/debugging).

    Returns:
        List of usernames (without password hashes)
    """
    return list(_auth_users.keys())
