"""Rate limiting configuration for Flask application

Implements rate limiting to prevent abuse and brute force attacks.

Usage:
    from src.dashboard.rate_limiting import init_rate_limiting

    app = Flask(__name__)
    limiter = init_rate_limiting(app, config)
"""

from typing import Optional

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def get_rate_limit_key() -> str:
    """Get rate limiting key from request

    Uses remote address by default, or authenticated username if available.
    This allows per-user rate limiting when authentication is enabled.

    Returns:
        str: Rate limit key (IP address or username)
    """
    # Try to get authenticated username first
    if request.authorization and request.authorization.username:
        return f"user:{request.authorization.username}"

    # Fall back to IP address
    return get_remote_address()


def init_rate_limiting(app: Flask, config, storage_uri: Optional[str] = None) -> Limiter:
    """Initialize rate limiting for Flask application

    Args:
        app: Flask application instance
        config: Config object with rate limiting settings
        storage_uri: Optional storage URI (default: memory://)
                     Use redis://localhost:6379 for production

    Returns:
        Limiter: Flask-Limiter instance

    Configuration (config.yaml):
        dashboard:
          rate_limiting:
            enabled: true
            default_limit: "200 per hour"
            storage_uri: "memory://"  # or redis://localhost:6379

    Rate Limits Applied:
        - General browsing: 200 per hour (default)
        - API endpoints: 50 per hour
        - Authentication: 10 per minute (brute force protection)
        - Data collection: 5 per hour (expensive operation)
        - Export operations: 20 per hour
        - Cache operations: 30 per hour
    """
    # Get rate limiting config
    dashboard_config = config.dashboard_config
    rate_config = dashboard_config.get("rate_limiting", {})

    # Check if rate limiting is enabled
    if not rate_config.get("enabled", True):
        app.logger.info("Rate limiting disabled by configuration")
        # Return a disabled limiter
        limiter = Limiter(
            app=app,
            key_func=get_rate_limit_key,
            default_limits=[],
            storage_uri="memory://",
            enabled=False,
        )
        return limiter

    # Get configuration values
    default_limit = rate_config.get("default_limit", "200 per hour")
    if storage_uri is None:
        storage_uri = rate_config.get("storage_uri", "memory://")

    # Initialize limiter
    limiter = Limiter(
        app=app,
        key_func=get_rate_limit_key,
        default_limits=[default_limit],
        storage_uri=storage_uri,
        # Use app config for enabled state
        enabled=True,
    )

    app.logger.info(f"Rate limiting enabled: {default_limit} (storage: {storage_uri})")

    return limiter


def apply_route_limits(limiter: Limiter, app: Flask) -> None:
    """Apply specific rate limits to routes

    This function applies more restrictive limits to specific routes
    that are expensive or security-sensitive.

    Args:
        limiter: Flask-Limiter instance
        app: Flask application instance

    Note:
        This must be called after all blueprints are registered,
        otherwise route decorators won't be found.
    """
    if not limiter.enabled:
        app.logger.info("Rate limiting disabled - skipping route-specific limits")
        return

    # Authentication endpoints (brute force protection)
    limiter.limit("10 per minute")(app.view_functions.get("api.api_metrics"))  # type: ignore[arg-type]
    limiter.limit("10 per minute")(app.view_functions.get("api.api_refresh"))  # type: ignore[arg-type]

    # Data collection (expensive operation)
    limiter.limit("5 per hour")(app.view_functions.get("api.collect"))  # type: ignore[arg-type]

    # Export operations
    for route_name in [
        "export.export_team_csv",
        "export.export_team_json",
        "export.export_person_csv",
        "export.export_person_json",
        "export.export_comparison_csv",
        "export.export_comparison_json",
        "export.export_team_members_csv",
        "export.export_team_members_json",
    ]:
        if route_name in app.view_functions:
            limiter.limit("20 per hour")(app.view_functions[route_name])

    # Cache operations
    limiter.limit("30 per hour")(app.view_functions.get("api.cache_clear"))  # type: ignore[arg-type]
    limiter.limit("30 per hour")(app.view_functions.get("api.cache_warm"))  # type: ignore[arg-type]
    limiter.limit("60 per hour")(app.view_functions.get("api.api_reload_cache"))  # type: ignore[arg-type]

    app.logger.info("Route-specific rate limits applied")


def get_rate_limit_config_example() -> str:
    """Get example configuration for rate limiting

    Returns:
        str: Example YAML configuration
    """
    return """
dashboard:
  rate_limiting:
    enabled: true
    default_limit: "200 per hour"
    storage_uri: "memory://"  # Use redis://localhost:6379 for production

    # Optional: Custom limits per route (applied automatically)
    # - General browsing: 200/hour (default)
    # - API endpoints: 10/minute (auth protection)
    # - Data collection: 5/hour (expensive)
    # - Exports: 20/hour
    # - Cache operations: 30/hour
"""
