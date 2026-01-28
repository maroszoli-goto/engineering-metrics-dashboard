"""Input validation middleware for Flask application

Provides validation decorators and utilities to prevent injection attacks.

Usage:
    from src.dashboard.input_validation import validate_route_params

    @app.route("/person/<username>")
    @validate_route_params(username=validate_identifier)
    def person_dashboard(username):
        # username is validated before this runs
        pass
"""

import functools
import re
from typing import Any, Callable, Dict, Optional

from flask import abort, request

from src.dashboard.utils.validation import validate_identifier


def validate_team_name(value: str) -> bool:
    """Validate team name parameter

    Args:
        value: Team name to validate

    Returns:
        bool: True if valid, False otherwise

    Valid team names:
        - Alphanumeric characters
        - Spaces, hyphens, underscores
        - 1-100 characters
    """
    if not value or len(value) > 100:
        return False

    # Allow alphanumeric, spaces, hyphens, underscores
    pattern = r"^[a-zA-Z0-9 _-]+$"
    return bool(re.match(pattern, value))


def validate_username(value: str) -> bool:
    """Validate username parameter

    Args:
        value: Username to validate

    Returns:
        bool: True if valid, False otherwise

    Valid usernames:
        - Alphanumeric characters
        - Hyphens, underscores, dots
        - 1-39 characters (GitHub max)
    """
    if not value or len(value) > 39:
        return False

    # Allow alphanumeric, hyphens, underscores, dots
    pattern = r"^[a-zA-Z0-9._-]+$"
    return bool(re.match(pattern, value))


def validate_range_param(value: str) -> bool:
    """Validate date range parameter

    Args:
        value: Date range string (e.g., "90d", "Q1-2025")

    Returns:
        bool: True if valid, False otherwise

    Valid formats:
        - Days: 30d, 90d, 180d, 365d
        - Quarters: Q1-2025, Q2-2024
        - Years: 2024, 2025
        - Custom: YYYY-MM-DD:YYYY-MM-DD
    """
    if not value or len(value) > 50:
        return False

    # Days format (e.g., "90d")
    if re.match(r"^\d{1,4}d$", value):
        days = int(value[:-1])
        return 1 <= days <= 3650  # Max 10 years

    # Quarter format (e.g., "Q1-2025")
    if re.match(r"^Q[1-4]-\d{4}$", value):
        return True

    # Year format (e.g., "2024")
    if re.match(r"^\d{4}$", value):
        year = int(value)
        return 2000 <= year <= 2100

    # Custom date range (e.g., "2024-01-01:2024-12-31")
    if ":" in value:
        parts = value.split(":")
        if len(parts) == 2:
            return all(re.match(r"^\d{4}-\d{2}-\d{2}$", p) for p in parts)

    return False


def validate_env_param(value: str) -> bool:
    """Validate environment parameter

    Args:
        value: Environment name (e.g., "prod", "uat")

    Returns:
        bool: True if valid, False otherwise

    Valid environments:
        - Lowercase alphanumeric
        - Hyphens, underscores
        - 1-20 characters
    """
    if not value or len(value) > 20:
        return False

    pattern = r"^[a-z0-9_-]+$"
    return bool(re.match(pattern, value))


def validate_route_params(**validators: Callable[[str], bool]) -> Callable:
    """Decorator to validate route parameters

    Args:
        **validators: Keyword arguments mapping parameter names to validator functions

    Returns:
        Callable: Decorated function

    Example:
        @app.route("/person/<username>")
        @validate_route_params(username=validate_username)
        def person_dashboard(username):
            # username is validated before this runs
            pass

    Raises:
        400 Bad Request if validation fails
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Validate each parameter
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        abort(400, description=f"Invalid parameter: {param_name}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_query_params(**validators: Callable[[str], bool]) -> Callable:
    """Decorator to validate query string parameters

    Args:
        **validators: Keyword arguments mapping parameter names to validator functions

    Returns:
        Callable: Decorated function

    Example:
        @app.route("/")
        @validate_query_params(range=validate_range_param, env=validate_env_param)
        def index():
            # range and env are validated before this runs
            pass

    Raises:
        400 Bad Request if validation fails
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Validate each query parameter
            for param_name, validator in validators.items():
                value = request.args.get(param_name)
                if value is not None:
                    if not validator(value):
                        abort(400, description=f"Invalid query parameter: {param_name}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for safe file operations

    Args:
        filename: Filename to sanitize
        max_length: Maximum filename length (default: 255)

    Returns:
        str: Sanitized filename

    Removes:
        - Path traversal characters (../, .\\)
        - Null bytes
        - Control characters
        - Leading/trailing whitespace
    """
    if not filename:
        return ""

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Remove path traversal
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")

    # Remove control characters
    filename = "".join(c for c in filename if ord(c) >= 32)

    # Trim and limit length
    filename = filename.strip()[:max_length]

    return filename


def validate_export_params(team_name: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
    """Validate export parameters

    Args:
        team_name: Team name to validate (optional)
        username: Username to validate (optional)

    Returns:
        Dict[str, Any]: Validation results {"valid": bool, "error": str}

    Example:
        result = validate_export_params(team_name=team_name)
        if not result["valid"]:
            return jsonify({"error": result["error"]}), 400
    """
    if team_name is not None:
        if not validate_team_name(team_name):
            return {"valid": False, "error": f"Invalid team name: {team_name}"}

    if username is not None:
        if not validate_username(username):
            return {"valid": False, "error": f"Invalid username: {username}"}

    return {"valid": True, "error": None}


def get_validation_error_message(param_name: str, value: str) -> str:
    """Get user-friendly validation error message

    Args:
        param_name: Parameter name
        value: Invalid value

    Returns:
        str: Error message
    """
    messages = {
        "username": "Username must be alphanumeric with hyphens, underscores, or dots (max 39 chars)",
        "team_name": "Team name must be alphanumeric with spaces, hyphens, or underscores (max 100 chars)",
        "range": "Invalid date range format. Use: 90d, Q1-2025, 2024, or YYYY-MM-DD:YYYY-MM-DD",
        "env": "Environment must be lowercase alphanumeric with hyphens or underscores (max 20 chars)",
    }

    default_message = f"Invalid parameter: {param_name}"
    return messages.get(param_name, default_message)
