"""Blueprint registration module for dashboard

Provides centralized blueprint registration and initialization.
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all blueprints with the Flask application

    This function registers all dashboard blueprints with their appropriate
    URL prefixes and configurations. Blueprints are registered in dependency
    order to avoid circular imports.

    Args:
        app: Flask application instance

    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> register_blueprints(app)
        >>> # All blueprints now registered
    """
    # Import blueprints here to avoid circular imports
    from .api import api_bp
    from .dashboard import dashboard_bp
    from .export import export_bp
    from .metrics_bp import metrics_bp
    from .settings import settings_bp

    # Register API blueprint with /api prefix
    app.register_blueprint(api_bp, url_prefix="/api")

    # Register export blueprint with /api/export prefix
    app.register_blueprint(export_bp, url_prefix="/api/export")

    # Register dashboard blueprint at root level (no prefix)
    app.register_blueprint(dashboard_bp)

    # Register settings blueprint with /settings prefix
    app.register_blueprint(settings_bp, url_prefix="/settings")

    # Register metrics blueprint with /metrics prefix
    app.register_blueprint(metrics_bp, url_prefix="/metrics")


def init_blueprint_dependencies(app: Flask, config, metrics_cache, cache_service, refresh_service) -> None:
    """Initialize dependencies shared across blueprints

    Stores shared dependencies in Flask app extensions so blueprints
    can access them without circular imports.

    Args:
        app: Flask application instance
        config: Application configuration
        metrics_cache: Global metrics cache dictionary
        cache_service: CacheService instance
        refresh_service: MetricsRefreshService instance

    Example:
        >>> app = Flask(__name__)
        >>> init_blueprint_dependencies(app, config, cache, cache_svc, refresh_svc)
        >>> # Dependencies now available via current_app.extensions
    """
    # Store dependencies in app.extensions (Flask's standard pattern)
    if not hasattr(app, "extensions"):
        app.extensions = {}

    app.extensions["metrics_cache"] = metrics_cache
    app.extensions["cache_service"] = cache_service
    app.extensions["refresh_service"] = refresh_service
    app.extensions["app_config"] = config
