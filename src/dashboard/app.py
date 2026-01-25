import csv
import io
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from flask import Flask, Response, jsonify, make_response, redirect, render_template, request

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd

from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector
from src.config import Config
from src.dashboard.auth import init_auth, require_auth
from src.dashboard.blueprints import init_blueprint_dependencies, register_blueprints
from src.dashboard.services.cache_service import CacheService
from src.dashboard.services.metrics_refresh_service import MetricsRefreshService
from src.dashboard.utils.data import flatten_dict
from src.dashboard.utils.data_filtering import filter_github_data_by_date, filter_jira_data_by_date
from src.dashboard.utils.error_handling import handle_api_error, set_logger
from src.dashboard.utils.export import create_csv_response, create_json_response
from src.dashboard.utils.formatting import format_time_ago, format_value_for_csv
from src.dashboard.utils.performance import timed_route
from src.dashboard.utils.validation import validate_identifier
from src.models.metrics import MetricsCalculator
from src.utils.date_ranges import get_cache_filename, get_preset_ranges
from src.utils.logging import get_logger

# ============================================================================
# Helper Functions
# ============================================================================


def get_config() -> Config:
    """Load configuration"""
    return Config()


def get_display_name(username: str, member_names: Optional[Dict[str, str]] = None) -> str:
    """Get display name for a GitHub username, fallback to username."""
    if member_names and username in member_names:
        return member_names[username]
    return username


# ============================================================================
# Application Factory
# ============================================================================


def create_app(config: Optional[Config] = None) -> Flask:
    """Create and configure Flask application instance.

    Args:
        config: Config object (optional). If None, loads from default location.

    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)

    # Load config if not provided
    if config is None:
        config = get_config()

    # Initialize logger
    dashboard_logger = get_logger("team_metrics.dashboard")

    # Set logger for error handling utility
    set_logger(dashboard_logger)

    # Initialize cache service
    data_dir = Path(__file__).parent.parent.parent / "data"
    cache_service = CacheService(data_dir, dashboard_logger)

    # Initialize metrics refresh service
    refresh_service = MetricsRefreshService(config, dashboard_logger)

    # Initialize metrics cache
    metrics_cache: Dict[str, Any] = {"data": None, "timestamp": None}

    # Try to load default cache on startup (90d, prod environment)
    loaded_cache = cache_service.load_cache("90d", "prod")
    if loaded_cache:
        metrics_cache.update(loaded_cache)

    # Register format_time_ago as Jinja filter
    app.jinja_env.filters["time_ago"] = format_time_ago

    # Initialize blueprint dependencies
    init_blueprint_dependencies(app, config, metrics_cache, cache_service, refresh_service)

    # Register blueprints
    register_blueprints(app)

    # Initialize authentication
    init_auth(app, config)

    # Context processor to inject template globals
    @app.context_processor
    def inject_template_globals() -> Dict[str, Any]:
        """Inject global template variables"""
        range_key = request.args.get("range", "90d")
        date_range_info: Dict[str, Any] = metrics_cache.get("date_range", {})

        # Get team list from cache or config
        teams = []
        cache_data = metrics_cache.get("data")
        if cache_data and "teams" in cache_data:
            teams = sorted(cache_data["teams"].keys())
        else:
            # Fallback to config
            teams = [team["name"] for team in config.teams]

        # Extract environment metadata from cache
        environment = metrics_cache.get("environment", "prod")
        time_offset_days = metrics_cache.get("time_offset_days", 0)
        jira_server = metrics_cache.get("jira_server", "")

        return {
            "current_year": datetime.now().year,
            "current_range": range_key,
            "available_ranges": cache_service.get_available_ranges(),
            "date_range_info": date_range_info,
            "team_list": teams,
            # Environment context
            "environment": environment,
            "time_offset_days": time_offset_days,
            "jira_server": jira_server,
        }

    return app


# Dashboard routes moved to src/dashboard/blueprints/dashboard.py
# - /
# - /team/<team_name>
# - /person/<username>
# - /team/<team_name>/compare
# - /documentation
# - /comparison


# API routes moved to src/dashboard/blueprints/api.py
# - /api/metrics
# - /api/refresh
# - /api/reload-cache
# - /collect


# All remaining routes have been moved to blueprints.
# See src/dashboard/blueprints/ for route implementations.

# Helper functions (get_config, get_display_name) are at top of file (lines 52-61)


# Export Helper Functions
# ============================================================================


# flatten_dict, format_value_for_csv, create_csv_response, create_json_response
# moved to src.dashboard.utils modules


# ============================================================================
# Export Routes
# ============================================================================


# Export routes moved to src/dashboard/blueprints/export.py
# - /api/export/team/<team_name>/csv
# - /api/export/team/<team_name>/json
# - /api/export/person/<username>/csv
# - /api/export/person/<username>/json
# - /api/export/comparison/csv
# - /api/export/comparison/json
# - /api/export/team-members/<team_name>/csv
# - /api/export/team-members/<team_name>/json


def main() -> None:
    """Main entry point for running the dashboard"""
    config = get_config()
    dashboard_config = config.dashboard_config

    # Create app using factory
    app = create_app(config)

    # Run the app
    app.run(debug=dashboard_config.get("debug", True), port=dashboard_config.get("port", 5001), host="0.0.0.0")


if __name__ == "__main__":
    main()
