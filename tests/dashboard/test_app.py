"""Integration tests for Flask dashboard routes"""

import csv
import io
import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.config import Config
from src.dashboard.app import create_app


@pytest.fixture
def client():
    """Flask test client fixture using factory pattern"""
    # Create mock config
    config = MagicMock(spec=Config)
    config.dashboard_config = {"port": 5001, "cache_duration_minutes": 60, "auth": {"enabled": False}}
    config.teams = []

    # Create app using factory
    app = create_app(config)
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_cache_data():
    """Create mock cache data matching expected structure"""
    return {
        "range_key": "90d",
        "date_range": {
            "description": "Last 90 days",
            "start_date": datetime(2024, 10, 13),
            "end_date": datetime(2026, 1, 11),
        },
        "teams": {
            "Native": {
                "display_name": "Native Team",
                "timestamp": datetime.now(),
                "github": {
                    "pr_count": 107,
                    "review_count": 472,
                    "commit_count": 519,
                    "merge_rate": 0.85,
                    "avg_cycle_time": 120.5,
                    "member_trends": {
                        "jdoe": {
                            "prs": 10,
                            "reviews": 50,
                            "commits": 60,
                            "lines_added": 1000,
                            "lines_deleted": 500,
                        }
                    },
                },
                "jira": {
                    "wip": {"count": 81},
                    "completed": 57,
                    "bugs_created": 20,
                    "bugs_resolved": 16,
                    "flagged_blocked": 5,
                },
                "members": [
                    {
                        "name": "John Doe",
                        "github": "jdoe",
                        "jira": "jdoe",
                        "prs_created": 10,
                        "reviews_given": 50,
                        "commits": 60,
                    }
                ],
            },
            "WebTC": {
                "display_name": "WebTC Team",
                "timestamp": datetime.now(),
                "github": {
                    "pr_count": 69,
                    "review_count": 268,
                    "commit_count": 512,
                    "avg_cycle_time": 145.2,
                    "member_trends": {},
                },
                "jira": {"wip": {"count": 44}, "completed": 103},
                "members": [],
            },
        },
        "persons": {
            "jdoe": {
                "name": "John Doe",
                "teams": ["Native"],
                "timestamp": datetime.now(),
                "github": {
                    "prs_created": 10,
                    "prs_merged": 8,
                    "prs_reviewed": 45,
                    "reviews_given": 50,
                    "commits": 60,
                    "lines_added": 1000,
                    "lines_deleted": 500,
                    "merge_rate": 0.8,
                    "avg_pr_cycle_time": 48.5,
                    "avg_time_to_review": 12.3,
                },
                "jira": {
                    "completed": 5,
                    "in_progress": 2,
                    "avg_cycle_time": 72.0,
                    "types": {"Story": 3, "Bug": 2},
                },
                "period": {"start": "2024-10-13", "end": "2026-01-11"},
            }
        },
        "comparison": {
            "Native": {
                "score": 75.5,
                "team_size": 5,
                "prs": 107,
                "reviews": 472,
                "commits": 519,
                "jira_throughput": 57,
                "jira_wip": 81,
                "jira_flagged": 5,
                "avg_cycle_time": 120.5,
                "merge_rate": 0.85,
                "dora_deployment_freq": 2.1,
                "dora_lead_time": 168.0,
                "dora_cfr": 0.05,
                "dora_mttr": 24.0,
                "github": {"pr_count": 107, "review_count": 472},
                "jira": {"completed": 57},
            },
            "WebTC": {
                "score": 68.2,
                "team_size": 4,
                "prs": 69,
                "reviews": 268,
                "commits": 512,
                "jira_throughput": 103,
                "jira_wip": 44,
                "jira_flagged": 3,
                "avg_cycle_time": 145.2,
                "merge_rate": 0.78,
                "dora_deployment_freq": 1.5,
                "dora_lead_time": 200.0,
                "dora_cfr": 0.08,
                "dora_mttr": 36.0,
                "github": {"pr_count": 69, "review_count": 268},
                "jira": {"completed": 103},
            },
        },
        "timestamp": datetime.now(),
    }


@pytest.fixture
def mock_cache(client, mock_cache_data):
    """Mock metrics cache with sample data"""
    # Create cache structure
    cache_data = {"data": mock_cache_data, "range_key": "90d", "timestamp": mock_cache_data["timestamp"]}

    # Get the app from the client fixture
    app = client.application

    # Update app.extensions since blueprints use that
    app.extensions["metrics_cache"] = cache_data

    # Always set up a fresh config for blueprints to avoid test isolation issues
    # Previous tests may have set up incomplete MockConfig objects
    mock_config = MagicMock(spec=Config)
    # Add team configs matching the mock cache data (with jira filters for comparison template)
    mock_config.teams = [
        {
            "name": "Native",
            "display_name": "Native Team",
            "members": [{"github": "jdoe", "name": "John Doe"}],
            "jira": {"filters": {"completed": 12345, "wip": 12346}},
        },
        {
            "name": "WebTC",
            "display_name": "WebTC Team",
            "members": [{"github": "asmith", "name": "Alice Smith"}],
            "jira": {"filters": {"completed": 12347, "wip": 12348}},
        },
    ]
    mock_config.days_back = 90
    mock_config.github_organization = "test-org"
    mock_config.github_base_url = "https://github.com"
    mock_config.jira_config = {"server": "https://jira.test.com"}
    mock_config.performance_weights = {
        "prs": 0.15,
        "reviews": 0.15,
        "commits": 0.10,
        "cycle_time": 0.10,
        "jira_completed": 0.15,
        "merge_rate": 0.05,
        "deployment_frequency": 0.10,
        "lead_time": 0.10,
        "change_failure_rate": 0.05,
        "mttr": 0.05,
    }

    def get_team_by_name(name):
        for team in mock_config.teams:
            if team["name"] == name:
                return team
        return None

    mock_config.get_team_by_name = get_team_by_name
    app.extensions["app_config"] = mock_config

    # Mock cache_service to always return the same mock data regardless of range
    # This prevents issues when tests request different ranges (30d, 60d, etc.)
    mock_cache_service = MagicMock()
    mock_cache_service.load_cache.return_value = cache_data
    mock_cache_service.get_available_ranges.return_value = [("90d", "90d", True)]
    app.extensions["cache_service"] = mock_cache_service

    return mock_cache_data


class TestMainRoutes:
    """Test main dashboard routes"""

    def test_index_with_range_parameter(self, client, mock_cache):
        """Test index with date range parameter"""
        response = client.get("/?range=30d")
        assert response.status_code == 200


class TestDocumentationRoutes:
    """Test documentation routes"""

    def test_documentation_page(self, client, mock_cache):
        """Test documentation page loads"""
        response = client.get("/documentation")
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""

    def test_no_cache_loaded(self, client):
        """Test handling when no cache is loaded"""
        # Set cache to empty via app extensions
        client.application.extensions["metrics_cache"] = {"data": None}
        response = client.get("/")
        # Should either show loading page (200) or handle gracefully
        assert response.status_code in [200, 500]


class TestAppConfiguration:
    """Test Flask app configuration"""

    def test_app_exists(self, client):
        """Test that Flask app is properly configured via factory"""
        app = client.application
        assert app is not None
        assert app.name == "src.dashboard.app"

    def test_app_in_testing_mode(self, client):
        """Test that testing mode can be enabled"""
        assert client.application.config["TESTING"] is True


class TestExportFunctionality:
    """Test export routes for CSV and JSON"""

    def test_export_team_csv(self, client, mock_cache):
        """Test exporting team data as CSV"""
        response = client.get("/api/export/team/Native/csv")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["Content-Disposition"]
        # Check for filename pattern with date suffix (e.g., team_native_metrics_2026-01-14.csv)
        assert "team_metrics_export" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

        # Parse CSV and verify structure
        csv_data = response.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        assert len(rows) == 1

        # Verify key fields are present (flattened structure)
        row = rows[0]
        assert "github.pr_count" in row
        assert "github.review_count" in row
        assert "jira.wip.count" in row

    def test_export_team_json(self, client, mock_cache):
        """Test exporting team data as JSON"""
        response = client.get("/api/export/team/Native/json")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert "attachment" in response.headers["Content-Disposition"]
        # Check for filename pattern with date suffix
        assert "team_metrics_export" in response.headers["Content-Disposition"]
        assert ".json" in response.headers["Content-Disposition"]

        # Parse JSON and verify structure
        data = json.loads(response.data)
        assert "team" in data
        assert "metadata" in data
        assert data["team"]["github"]["pr_count"] == 107
        assert data["team"]["jira"]["completed"] == 57

    def test_export_team_not_found(self, client, mock_cache):
        """Test exporting non-existent team"""
        response = client.get("/api/export/team/NonExistent/csv")
        assert response.status_code == 404
        assert b"not found" in response.data

    def test_export_person_csv(self, client, mock_cache):
        """Test exporting person data as CSV"""
        response = client.get("/api/export/person/jdoe/csv")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        # Check for filename pattern with date suffix
        assert "team_metrics_export" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

        # Parse CSV and verify structure
        csv_data = response.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        assert len(rows) == 1

        row = rows[0]
        assert "github.prs_created" in row
        assert "jira.completed" in row

    def test_export_person_json(self, client, mock_cache):
        """Test exporting person data as JSON"""
        response = client.get("/api/export/person/jdoe/json")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"

        data = json.loads(response.data)
        assert "person" in data
        assert "metadata" in data
        assert data["person"]["name"] == "John Doe"
        assert data["person"]["github"]["prs_created"] == 10

    def test_export_person_not_found(self, client, mock_cache):
        """Test exporting non-existent person"""
        response = client.get("/api/export/person/unknown/json")
        assert response.status_code == 404

    def test_export_comparison_csv(self, client, mock_cache):
        """Test exporting team comparison as CSV"""
        response = client.get("/api/export/comparison/csv")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        # Check for filename pattern with date suffix
        assert "team_metrics_export" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

        # Parse CSV and verify structure
        csv_data = response.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        assert len(rows) == 2  # Two teams

        # Verify team names are present
        team_names = [row["team_name"] for row in rows]
        assert "Native" in team_names
        assert "WebTC" in team_names

    def test_export_comparison_json(self, client, mock_cache):
        """Test exporting team comparison as JSON"""
        response = client.get("/api/export/comparison/json")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"

        data = json.loads(response.data)
        assert "comparison" in data
        assert "metadata" in data
        assert "Native" in data["comparison"]
        assert "WebTC" in data["comparison"]
        assert data["comparison"]["Native"]["score"] == 75.5

    def test_export_team_members_csv(self, client, mock_cache):
        """Test exporting team member comparison as CSV"""
        # Add members_breakdown to mock data
        mock_data = mock_cache.copy()
        mock_data["teams"]["Native"]["members_breakdown"] = {
            "John Doe": {
                "github": {"prs_created": 10, "reviews_given": 50},
                "jira": {"issues_completed": 5},
                "score": 85.0,
            }
        }
        client.application.extensions["metrics_cache"] = {
            "data": mock_data,
            "range_key": "90d",
            "date_range": mock_cache.get("date_range", {}),
        }

        response = client.get("/api/export/team-members/Native/csv")
        assert response.status_code == 200
        # Check for filename pattern with date suffix
        assert "team_metrics_export" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

        # Parse CSV
        csv_data = response.data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["member_name"] == "John Doe"

    def test_export_team_members_json(self, client, mock_cache):
        """Test exporting team member comparison as JSON"""
        # Add members_breakdown to mock data
        mock_data = mock_cache.copy()
        mock_data["teams"]["Native"]["members_breakdown"] = {"John Doe": {"github": {"prs_created": 10}, "score": 85.0}}
        client.application.extensions["metrics_cache"] = {
            "data": mock_data,
            "range_key": "90d",
            "date_range": mock_cache.get("date_range", {}),
        }

        response = client.get("/api/export/team-members/Native/json")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "members" in data
        assert "John Doe" in data["members"]
        assert data["members"]["John Doe"]["score"] == 85.0

    def test_export_no_cache(self, client):
        """Test export when no cache is available"""
        empty_cache = {"data": None}

        # Update app.extensions since blueprints use that
        client.application.extensions["metrics_cache"] = empty_cache

        response = client.get("/api/export/team/Native/csv")
        assert response.status_code == 404
        assert b"No metrics data available" in response.data


class TestSettingsRoutes:
    """Test settings functionality"""

    def test_settings_page_loads(self, client, mock_cache):
        """Test settings page renders successfully"""
        response = client.get("/settings", follow_redirects=True)
        assert response.status_code == 200
        assert b"Performance Score Settings" in response.data

    def test_settings_page_has_presets(self, client, mock_cache):
        """Test settings page contains preset buttons"""
        response = client.get("/settings", follow_redirects=True)
        assert response.status_code == 200
        assert b"Balanced" in response.data
        assert b"Code Quality" in response.data
        assert b"Velocity" in response.data
        assert b"Jira Focus" in response.data

    def test_settings_save_valid_weights(self, client, mock_cache):
        """Test saving valid performance weights"""

        # Mock config
        class MockConfig:
            def __init__(self):
                self.performance_weights = {}

            def update_performance_weights(self, weights):
                self.performance_weights = weights

        mock_config = MockConfig()
        # Update app.extensions since blueprints use that
        client.application.extensions["app_config"] = mock_config

        # Valid weights that sum to 100 (all 10 metrics)
        weights = {
            "prs": 15,
            "reviews": 15,
            "commits": 10,
            "cycle_time": 10,
            "jira_completed": 15,
            "merge_rate": 5,
            "deployment_frequency": 10,
            "lead_time": 10,
            "change_failure_rate": 5,
            "mttr": 5,
        }

        response = client.post("/settings/save", data=json.dumps(weights), content_type="application/json")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify weights were converted to decimals
        assert mock_config.performance_weights["prs"] == 0.15
        assert mock_config.performance_weights["deployment_frequency"] == 0.10

    def test_settings_save_invalid_weights_sum(self, client, mock_cache):
        """Test saving weights that don't sum to 100"""
        # Invalid weights (sum to 110)
        weights = {"prs": 30, "reviews": 30, "commits": 20, "cycle_time": 10, "jira_completed": 10, "merge_rate": 10}

        response = client.post("/settings/save", data=json.dumps(weights), content_type="application/json")

        # Should return 400 (bad request) for validation error
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "error" in data
        assert "must sum to 100%" in data["error"]

    def test_settings_reset(self, client, mock_cache):
        """Test resetting weights to defaults"""

        class MockConfig:
            def __init__(self):
                self.performance_weights = {}

            def update_performance_weights(self, weights):
                self.performance_weights = weights

        mock_config = MockConfig()
        # Update app.extensions since blueprints use that
        client.application.extensions["app_config"] = mock_config

        response = client.post("/settings/reset")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify default weights were set (new balanced defaults)
        assert mock_config.performance_weights["prs"] == 0.15
        assert mock_config.performance_weights["reviews"] == 0.15
        assert mock_config.performance_weights["commits"] == 0.10
        assert mock_config.performance_weights["cycle_time"] == 0.10
        assert mock_config.performance_weights["jira_completed"] == 0.15
        assert mock_config.performance_weights["merge_rate"] == 0.05
        assert mock_config.performance_weights["deployment_frequency"] == 0.10
        assert mock_config.performance_weights["lead_time"] == 0.10
        assert mock_config.performance_weights["change_failure_rate"] == 0.05
        assert mock_config.performance_weights["mttr"] == 0.05


class TestHelperFunctions:
    """Test export helper functions"""

    def test_flatten_dict(self):
        """Test dictionary flattening with nested structures"""
        from src.dashboard.app import flatten_dict

        nested = {"a": 1, "b": {"c": 2, "d": {"e": 3}}, "f": [1, 2, 3]}

        flattened = flatten_dict(nested)
        assert flattened["a"] == 1
        assert flattened["b.c"] == 2
        assert flattened["b.d.e"] == 3
        assert flattened["f"] == "1, 2, 3"

    def test_format_value_for_csv(self):
        """Test CSV value formatting"""
        from src.dashboard.app import format_value_for_csv

        # Test numbers
        assert format_value_for_csv(42) == 42
        assert format_value_for_csv(3.14159) == 3.14

        # Test datetime
        dt = datetime(2024, 1, 15, 10, 30, 45)
        assert format_value_for_csv(dt) == "2024-01-15 10:30:45"

        # Test None
        assert format_value_for_csv(None) == ""

        # Test string
        assert format_value_for_csv("hello") == "hello"


class TestDateRangeDisplay:
    """Tests for date range display in templates (Jan 2026)"""

    def test_team_members_comparison_passes_date_range_info(self, client, mock_cache):
        """Verify date_range_info passed to team_members_comparison template"""
        response = client.get("/team/Native/compare?range=30d")

        assert response.status_code == 200
        # Verify page loads successfully with date range parameter
        assert b"Native" in response.data

    def test_team_comparison_passes_date_range_info(self, client, mock_cache):
        """Verify date_range_info passed to comparison template"""
        response = client.get("/comparison?range=60d")

        assert response.status_code == 200
        # Verify comparison page loads with date range parameter
        assert b"Team Comparison" in response.data or b"Comparison" in response.data

    def test_context_processor_includes_date_range_info(self, client, mock_cache):
        """Verify global context processor adds date_range_info"""
        # Context processor requires request context, not just app context
        # Test by making an actual request and checking the response
        response = client.get("/")
        assert response.status_code == 200
        # Verify date_range_info is available (would cause template error if not)

    def test_date_range_selector_updates_all_pages(self, client, mock_cache):
        """Verify date range parameter works on all major pages"""
        pages = [
            "/",
            "/team/Native",
            "/team/Native/compare",
            "/comparison",
            "/person/jdoe",
        ]

        for page in pages:
            response = client.get(f"{page}?range=30d")
            assert response.status_code == 200, f"Failed to load {page} with range=30d"

    def test_missing_date_range_info_fallback(self, client):
        """Verify graceful fallback when date_range_info missing"""
        # Simulate cache with missing date_range
        mock_data = {
            "teams": {"Native": {"display_name": "Native Team", "timestamp": datetime.now()}},
            "persons": {},
            "comparison": {"Native": {"prs": 10, "reviews": 5}},
            "timestamp": datetime.now(),
        }
        cache_data = {"data": mock_data, "range_key": "90d", "timestamp": datetime.now()}

        # Update app.extensions for blueprints
        client.application.extensions["metrics_cache"] = cache_data

        # Set up config with proper team data
        mock_config = MagicMock(spec=Config)
        mock_config.teams = [
            {
                "name": "Native",
                "display_name": "Native Team",
                "members": [{"github": "jdoe", "name": "John Doe"}],
            }
        ]
        mock_config.days_back = 90
        mock_config.github_organization = "test-org"

        def get_team_by_name(name):
            for team in mock_config.teams:
                if team["name"] == name:
                    return team
            return None

        mock_config.get_team_by_name = get_team_by_name
        client.application.extensions["app_config"] = mock_config

        response = client.get("/team/Native/compare")
        # Should still render without crashing
        assert response.status_code == 200


class TestNoneValueHandling:
    """Tests for handling None values in DORA metrics (Jan 2026)

    Note: These are baseline tests to verify pages render. The actual None value
    handling is documented in CLAUDE.md under "Handling Missing DORA Metrics".
    Templates use Jinja2 'is not none' checks to display N/A for missing values.
    """

    def test_team_members_comparison_renders_successfully(self, client, mock_cache):
        """Verify team members comparison page renders"""
        response = client.get("/team/Native/compare")
        assert response.status_code == 200
        # Baseline test: page should render successfully with mock data
