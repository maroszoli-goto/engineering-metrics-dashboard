"""Tests for blueprint registration

Verifies that all blueprints are registered correctly and accessible.
"""

import pytest


class TestBlueprintRegistration:
    """Test blueprint registration functionality"""

    def test_all_blueprints_registered(self, app):
        """Should register all 4 blueprints"""
        blueprint_names = [bp.name for bp in app.blueprints.values()]

        assert "api" in blueprint_names
        assert "dashboard" in blueprint_names
        assert "export" in blueprint_names
        assert "settings" in blueprint_names

    def test_api_blueprint_prefix(self, app):
        """API blueprint should have /api prefix"""
        api_bp = app.blueprints.get("api")
        assert api_bp is not None

        # Check that routes have /api prefix
        rules = [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("api.")]
        assert any("/api/" in rule for rule in rules)

    def test_export_blueprint_prefix(self, app):
        """Export blueprint should have /api/export prefix"""
        export_bp = app.blueprints.get("export")
        assert export_bp is not None

        # Check that routes have /api/export prefix
        rules = [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("export.")]
        assert any("/api/export/" in rule for rule in rules)

    def test_dashboard_blueprint_no_prefix(self, app):
        """Dashboard blueprint should have no prefix (root level)"""
        dashboard_bp = app.blueprints.get("dashboard")
        assert dashboard_bp is not None

    def test_settings_blueprint_prefix(self, app):
        """Settings blueprint should have /settings prefix"""
        settings_bp = app.blueprints.get("settings")
        assert settings_bp is not None

        # Check that routes have /settings prefix
        rules = [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("settings.")]
        assert any("/settings/" in rule for rule in rules)

    def test_health_endpoints_accessible(self, client):
        """All blueprint health endpoints should be accessible"""
        # Test API health
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json["blueprint"] == "api"

        # Test dashboard health
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json["blueprint"] == "dashboard"

        # Test export health
        response = client.get("/api/export/health")
        assert response.status_code == 200
        assert response.json["blueprint"] == "export"

        # Test settings health
        response = client.get("/settings/health")
        assert response.status_code == 200
        assert response.json["blueprint"] == "settings"

    def test_dependencies_available(self, app):
        """Blueprint dependencies should be available in app.extensions"""
        assert "metrics_cache" in app.extensions
        assert "cache_service" in app.extensions
        assert "refresh_service" in app.extensions
        assert "app_config" in app.extensions

    def test_metrics_cache_structure(self, app):
        """Metrics cache should have expected structure"""
        cache = app.extensions["metrics_cache"]
        assert "data" in cache
        assert "timestamp" in cache


class TestDependencyInjection:
    """Test dependency injection for blueprints"""

    def test_cache_accessible_from_extension(self, app_with_cache):
        """Cache should be accessible from app.extensions"""
        cache = app_with_cache.extensions["metrics_cache"]

        assert cache["data"] is not None
        assert "teams" in cache["data"]
        assert "persons" in cache["data"]
        assert "comparison" in cache["data"]

    def test_mock_services_available(self, app):
        """Mock services should be available for testing"""
        cache_service = app.extensions["cache_service"]
        refresh_service = app.extensions["refresh_service"]

        assert cache_service is not None
        assert refresh_service is not None
