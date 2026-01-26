"""Pytest fixtures for blueprint testing

Provides shared fixtures for testing Flask blueprints with authentication,
dependencies, and test data.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from flask import Flask

from src.config import Config
from src.dashboard.app import create_app


@pytest.fixture
def app():
    """Create Flask app with blueprints registered using factory pattern"""
    # Create mock config
    config = MagicMock(spec=Config)
    config.dashboard_config = {"port": 5001, "cache_duration_minutes": 60, "auth": {"enabled": False}}
    config.teams = []

    # Create app using factory
    app = create_app(config)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    # Replace real service instances with mocks for testing
    # This allows tests to mock service behavior without side effects
    mock_cache_service = MagicMock()
    mock_refresh_service = MagicMock()

    # Override services in the container (new pattern)
    app.container.override("cache_service", mock_cache_service)  # type: ignore[attr-defined]
    app.container.override("refresh_service", mock_refresh_service)  # type: ignore[attr-defined]

    # Also set in extensions for backward compatibility with helper functions
    app.extensions["cache_service"] = mock_cache_service
    app.extensions["refresh_service"] = mock_refresh_service

    return app


@pytest.fixture
def client(app):
    """Create Flask test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create Flask CLI test runner"""
    return app.test_cli_runner()


@pytest.fixture
def mock_cache_data():
    """Create mock metrics cache data"""
    return {
        "teams": {
            "Test Team": {
                "github": {"pr_count": 10, "review_count": 15},
                "jira": {"throughput": {"weekly_avg": 5}, "wip": {"count": 3}},
                "dora": {"deployment_frequency": 2.5},
            }
        },
        "persons": {
            "testuser": {
                "github": {"pr_count": 5, "review_count": 8},
                "jira": {"completed": 10},
            }
        },
        "comparison": {"Test Team": {"prs": 10}},
        "timestamp": datetime.now(),
    }


@pytest.fixture
def app_with_cache(app, mock_cache_data):
    """Create Flask app with populated cache"""
    app.extensions["metrics_cache"]["data"] = mock_cache_data
    app.extensions["metrics_cache"]["timestamp"] = mock_cache_data["timestamp"]
    return app


@pytest.fixture
def client_with_cache(app_with_cache):
    """Create Flask test client with populated cache"""
    return app_with_cache.test_client()
