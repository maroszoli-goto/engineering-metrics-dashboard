"""Tests for API blueprint

Verifies API endpoints for metrics, refresh, cache operations, and collection.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestAPIMetricsEndpoint:
    """Test /api/metrics endpoint"""

    def test_returns_cached_metrics_when_fresh(self, app_with_cache, client_with_cache):
        """Should return cached metrics without refresh when cache is fresh"""
        # Ensure cache service returns false for should_refresh
        cache_service = app_with_cache.extensions["cache_service"]
        cache_service.should_refresh.return_value = False

        response = client_with_cache.get("/api/metrics")

        assert response.status_code == 200
        data = response.json
        assert "teams" in data
        assert "persons" in data
        assert "comparison" in data

    def test_refreshes_expired_cache(self, app_with_cache, client_with_cache):
        """Should refresh metrics when cache is expired"""
        # Mock cache as expired
        cache_service = app_with_cache.extensions["cache_service"]
        cache_service.should_refresh.return_value = True

        # Mock refresh service
        refresh_service = app_with_cache.extensions["refresh_service"]
        new_cache = {
            "teams": {"New Team": {}},
            "persons": {},
            "comparison": {},
            "timestamp": datetime.now(),
        }
        refresh_service.refresh_metrics.return_value = new_cache

        response = client_with_cache.get("/api/metrics")

        assert response.status_code == 200
        assert refresh_service.refresh_metrics.called
        assert app_with_cache.extensions["metrics_cache"]["data"]["teams"] == {"New Team": {}}

    def test_handles_refresh_failure(self, app_with_cache, client_with_cache):
        """Should return 500 when refresh fails"""
        # Mock cache as expired
        cache_service = app_with_cache.extensions["cache_service"]
        cache_service.should_refresh.return_value = True

        # Mock refresh failure
        refresh_service = app_with_cache.extensions["refresh_service"]
        refresh_service.refresh_metrics.side_effect = Exception("GitHub API error")

        response = client_with_cache.get("/api/metrics")

        assert response.status_code == 500
        assert "error" in response.json
        assert "Failed to refresh metrics" in response.json["error"]


class TestAPIRefreshEndpoint:
    """Test /api/refresh endpoint"""

    def test_successful_refresh(self, app_with_cache, client_with_cache):
        """Should refresh metrics and return success"""
        refresh_service = app_with_cache.extensions["refresh_service"]
        new_cache = {
            "teams": {"Refreshed Team": {}},
            "persons": {},
            "comparison": {},
            "timestamp": datetime.now(),
        }
        refresh_service.refresh_metrics.return_value = new_cache

        response = client_with_cache.get("/api/refresh")

        assert response.status_code == 200
        data = response.json
        assert data["status"] == "success"
        assert "metrics" in data
        assert data["metrics"]["teams"] == {"Refreshed Team": {}}
        assert refresh_service.refresh_metrics.called

    def test_refresh_failure(self, app_with_cache, client_with_cache):
        """Should return error when refresh fails"""
        refresh_service = app_with_cache.extensions["refresh_service"]
        refresh_service.refresh_metrics.side_effect = Exception("Jira connection timeout")

        response = client_with_cache.get("/api/refresh")

        assert response.status_code == 500
        data = response.json
        assert "error" in data
        assert "An error occurred" in data["error"]

    def test_updates_global_cache(self, app_with_cache, client_with_cache):
        """Should update global metrics cache"""
        refresh_service = app_with_cache.extensions["refresh_service"]
        new_timestamp = datetime.now()
        new_cache = {
            "teams": {"Updated Team": {}},
            "persons": {},
            "comparison": {},
            "timestamp": new_timestamp,
        }
        refresh_service.refresh_metrics.return_value = new_cache

        response = client_with_cache.get("/api/refresh")

        assert response.status_code == 200
        cache = app_with_cache.extensions["metrics_cache"]
        assert cache["data"]["teams"] == {"Updated Team": {}}
        assert cache["timestamp"] == new_timestamp


class TestAPIReloadCacheEndpoint:
    """Test /api/reload-cache endpoint"""

    def test_successful_cache_reload_default_params(self, app, client):
        """Should reload cache with default parameters (90d, prod)"""
        cache_service = app.extensions["cache_service"]
        loaded_cache = {
            "data": {"teams": {"Loaded Team": {}}, "persons": {}, "comparison": {}},
            "timestamp": datetime.now(),
        }
        cache_service.load_cache.return_value = loaded_cache

        response = client.post("/api/reload-cache")

        assert response.status_code == 200
        data = response.json
        assert data["status"] == "success"
        assert "Cache reloaded successfully" in data["message"]
        assert "timestamp" in data
        cache_service.load_cache.assert_called_with("90d", "prod")

    def test_cache_reload_custom_params(self, app, client):
        """Should reload cache with custom range and env"""
        cache_service = app.extensions["cache_service"]
        loaded_cache = {
            "data": {"teams": {}, "persons": {}, "comparison": {}},
            "timestamp": datetime.now(),
        }
        cache_service.load_cache.return_value = loaded_cache

        response = client.post("/api/reload-cache?range=30d&env=uat")

        assert response.status_code == 200
        cache_service.load_cache.assert_called_with("30d", "uat")

    def test_cache_reload_failure(self, app, client):
        """Should return error when cache file not found"""
        cache_service = app.extensions["cache_service"]
        cache_service.load_cache.return_value = None

        response = client.post("/api/reload-cache")

        assert response.status_code == 500
        data = response.json
        assert data["status"] == "error"
        assert "Failed to reload cache" in data["message"]

    def test_cache_reload_exception(self, app, client):
        """Should handle exceptions during cache reload"""
        cache_service = app.extensions["cache_service"]
        cache_service.load_cache.side_effect = Exception("Corrupted cache file")

        response = client.post("/api/reload-cache")

        assert response.status_code == 500
        data = response.json
        assert "error" in data
        assert "An error occurred" in data["error"]

    def test_updates_global_cache_on_reload(self, app, client):
        """Should update global metrics cache on successful reload"""
        cache_service = app.extensions["cache_service"]
        new_timestamp = datetime.now()
        loaded_cache = {
            "data": {"teams": {"Reloaded Team": {}}, "persons": {}, "comparison": {}},
            "timestamp": new_timestamp,
        }
        cache_service.load_cache.return_value = loaded_cache

        response = client.post("/api/reload-cache")

        assert response.status_code == 200
        cache = app.extensions["metrics_cache"]
        assert cache["data"]["teams"] == {"Reloaded Team": {}}
        assert cache["timestamp"] == new_timestamp


class TestCollectEndpoint:
    """Test /collect endpoint"""

    def test_successful_collection_redirects(self, app_with_cache, client_with_cache):
        """Should trigger collection and redirect to dashboard"""
        refresh_service = app_with_cache.extensions["refresh_service"]
        refresh_service.refresh_metrics.return_value = {
            "teams": {},
            "persons": {},
            "comparison": {},
            "timestamp": datetime.now(),
        }

        response = client_with_cache.get("/api/collect", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/"
        assert refresh_service.refresh_metrics.called

    def test_collection_failure_renders_error(self, app_with_cache, client_with_cache):
        """Should render error page when collection fails"""
        refresh_service = app_with_cache.extensions["refresh_service"]
        refresh_service.refresh_metrics.side_effect = Exception("Collection failed")

        # Mock render_template to avoid template not found error
        with patch("src.dashboard.blueprints.api.render_template") as mock_render:
            mock_render.return_value = "Error page"
            response = client_with_cache.get("/api/collect")

            assert response.status_code == 200
            mock_render.assert_called_with("error.html", error="An error occurred during collection")


class TestAPIHelperFunctions:
    """Test API blueprint helper functions"""

    def test_get_metrics_cache(self, app_with_cache):
        """Should retrieve metrics cache from extensions"""
        with app_with_cache.test_request_context():
            from src.dashboard.blueprints.api import get_metrics_cache

            cache = get_metrics_cache()
            assert cache is not None
            assert "data" in cache
            assert "timestamp" in cache

    def test_get_cache_service(self, app):
        """Should retrieve cache service from extensions"""
        with app.test_request_context():
            from src.dashboard.blueprints.api import get_cache_service

            service = get_cache_service()
            assert service is not None

    def test_get_refresh_service(self, app):
        """Should retrieve refresh service from extensions"""
        with app.test_request_context():
            from src.dashboard.blueprints.api import get_refresh_service

            service = get_refresh_service()
            assert service is not None

    def test_get_config(self, app):
        """Should retrieve config from extensions"""
        with app.test_request_context():
            from src.dashboard.blueprints.api import get_config

            config = get_config()
            assert config is not None
            assert "dashboard_config" in dir(config)

    def test_refresh_metrics_wrapper(self, app_with_cache):
        """Should call refresh service and update cache"""
        with app_with_cache.test_request_context():
            from src.dashboard.blueprints.api import refresh_metrics

            refresh_service = app_with_cache.extensions["refresh_service"]
            new_timestamp = datetime.now()
            new_cache = {
                "teams": {"Test": {}},
                "persons": {},
                "comparison": {},
                "timestamp": new_timestamp,
            }
            refresh_service.refresh_metrics.return_value = new_cache

            result = refresh_metrics()

            assert result == new_cache
            cache = app_with_cache.extensions["metrics_cache"]
            assert cache["data"] == new_cache
            assert cache["timestamp"] == new_timestamp

    def test_refresh_metrics_returns_none_on_failure(self, app_with_cache):
        """Should return None when refresh returns no data"""
        with app_with_cache.test_request_context():
            from src.dashboard.blueprints.api import refresh_metrics

            refresh_service = app_with_cache.extensions["refresh_service"]
            refresh_service.refresh_metrics.return_value = None

            result = refresh_metrics()

            assert result is None
