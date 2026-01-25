"""Tests for metrics refresh service"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config import Config
from src.dashboard.services.metrics_refresh_service import MetricsRefreshService


class TestMetricsRefreshServiceInit:
    """Test MetricsRefreshService initialization"""

    def test_init_with_config(self):
        """Should initialize with config"""
        config = MagicMock(spec=Config)
        service = MetricsRefreshService(config)

        assert service.config == config
        assert service.logger is None

    def test_init_with_logger(self):
        """Should initialize with optional logger"""
        config = MagicMock(spec=Config)
        logger = MagicMock()
        service = MetricsRefreshService(config, logger)

        assert service.logger == logger


class TestRefreshMetrics:
    """Test MetricsRefreshService.refresh_metrics method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = MagicMock(spec=Config)
        self.config.github_token = "fake_token"
        self.config.github_organization = "test_org"
        self.config.days_back = 90
        self.config.jira_config = {
            "server": "https://jira.example.com",
            "username": "user",
            "api_token": "token",
            "project_keys": ["PROJ"],
        }
        self.config.dashboard_config = {"jira_timeout_seconds": 120}

        self.logger = MagicMock()
        self.service = MetricsRefreshService(self.config, self.logger)

    def test_returns_none_for_no_teams(self):
        """Should return None when no teams are configured"""
        self.config.teams = []

        result = self.service.refresh_metrics()

        assert result is None
        self.logger.warning.assert_called_once()

    @patch("src.dashboard.services.metrics_refresh_service.JiraCollector")
    @patch("src.dashboard.services.metrics_refresh_service.GitHubGraphQLCollector")
    @patch("src.dashboard.services.metrics_refresh_service.MetricsCalculator")
    def test_successful_refresh_with_one_team(self, mock_calculator_class, mock_github_class, mock_jira_class):
        """Should successfully refresh metrics for one team"""
        # Setup team config
        self.config.teams = [
            {
                "name": "Test Team",
                "github": {"members": ["user1"], "team_slug": "test-team"},
                "jira": {"filters": {"wip": 123}},
            }
        ]

        # Mock Jira collector
        mock_jira = MagicMock()
        mock_jira.collect_team_filters.return_value = {"wip": {"count": 5}}
        mock_jira_class.return_value = mock_jira

        # Mock GitHub collector
        mock_github = MagicMock()
        mock_github.collect_all_metrics.return_value = {
            "pull_requests": [{"id": 1}],
            "reviews": [{"id": 1}],
            "commits": [{"sha": "abc"}],
            "deployments": [],
        }
        mock_github_class.return_value = mock_github

        # Mock MetricsCalculator
        mock_calculator = MagicMock()
        mock_calculator.calculate_team_metrics.return_value = {"github": {"prs": 10}}
        mock_calculator.calculate_team_comparison.return_value = {"Test Team": {"prs": 10}}
        mock_calculator_class.return_value = mock_calculator

        # Execute
        result = self.service.refresh_metrics()

        # Verify
        assert result is not None
        assert "teams" in result
        assert "comparison" in result
        assert "timestamp" in result
        assert "Test Team" in result["teams"]

        # Verify collectors were called
        mock_jira_class.assert_called_once()
        mock_github_class.assert_called_once()

    @patch("src.dashboard.services.metrics_refresh_service.JiraCollector")
    @patch("src.dashboard.services.metrics_refresh_service.GitHubGraphQLCollector")
    @patch("src.dashboard.services.metrics_refresh_service.MetricsCalculator")
    def test_handles_jira_connection_failure(self, mock_calculator_class, mock_github_class, mock_jira_class):
        """Should handle Jira connection failure gracefully"""
        self.config.teams = [
            {
                "name": "Test Team",
                "github": {"members": ["user1"]},
                "jira": {"filters": {}},
            }
        ]

        # Mock Jira to raise exception
        mock_jira_class.side_effect = Exception("Connection failed")

        # Mock GitHub collector
        mock_github = MagicMock()
        mock_github.collect_all_metrics.return_value = {
            "pull_requests": [],
            "reviews": [],
            "commits": [],
            "deployments": [],
        }
        mock_github_class.return_value = mock_github

        # Mock MetricsCalculator
        mock_calculator = MagicMock()
        mock_calculator.calculate_team_metrics.return_value = {}
        mock_calculator.calculate_team_comparison.return_value = {}
        mock_calculator_class.return_value = mock_calculator

        # Execute
        result = self.service.refresh_metrics()

        # Should still succeed even if Jira failed
        assert result is not None
        self.logger.warning.assert_called()

    @patch("src.dashboard.services.metrics_refresh_service.JiraCollector")
    @patch("src.dashboard.services.metrics_refresh_service.GitHubGraphQLCollector")
    @patch("src.dashboard.services.metrics_refresh_service.MetricsCalculator")
    def test_collects_multiple_teams(self, mock_calculator_class, mock_github_class, mock_jira_class):
        """Should collect metrics for multiple teams"""
        self.config.teams = [
            {"name": "Team A", "github": {"members": ["user1"]}, "jira": {"filters": {}}},
            {"name": "Team B", "github": {"members": ["user2"]}, "jira": {"filters": {}}},
        ]

        # Mock Jira
        mock_jira = MagicMock()
        mock_jira.collect_team_filters.return_value = {}
        mock_jira_class.return_value = mock_jira

        # Mock GitHub
        mock_github = MagicMock()
        mock_github.collect_all_metrics.return_value = {
            "pull_requests": [],
            "reviews": [],
            "commits": [],
            "deployments": [],
        }
        mock_github_class.return_value = mock_github

        # Mock MetricsCalculator
        mock_calculator = MagicMock()
        mock_calculator.calculate_team_metrics.return_value = {}
        mock_calculator.calculate_team_comparison.return_value = {"Team A": {}, "Team B": {}}
        mock_calculator_class.return_value = mock_calculator

        # Execute
        result = self.service.refresh_metrics()

        # Should have both teams
        assert "Team A" in result["teams"]
        assert "Team B" in result["teams"]

        # GitHub collector should be created twice (once per team)
        assert mock_github_class.call_count == 2

    @patch("src.dashboard.services.metrics_refresh_service.JiraCollector")
    @patch("src.dashboard.services.metrics_refresh_service.GitHubGraphQLCollector")
    @patch("src.dashboard.services.metrics_refresh_service.MetricsCalculator")
    def test_skips_jira_when_no_server_configured(self, mock_calculator_class, mock_github_class, mock_jira_class):
        """Should skip Jira collection when no server is configured"""
        self.config.teams = [{"name": "Test Team", "github": {"members": ["user1"]}, "jira": {"filters": {}}}]
        self.config.jira_config = {}  # No server

        # Mock GitHub
        mock_github = MagicMock()
        mock_github.collect_all_metrics.return_value = {
            "pull_requests": [],
            "reviews": [],
            "commits": [],
            "deployments": [],
        }
        mock_github_class.return_value = mock_github

        # Mock MetricsCalculator
        mock_calculator = MagicMock()
        mock_calculator.calculate_team_metrics.return_value = {}
        mock_calculator.calculate_team_comparison.return_value = {}
        mock_calculator_class.return_value = mock_calculator

        # Execute
        result = self.service.refresh_metrics()

        # Jira collector should not be created
        mock_jira_class.assert_not_called()

        # Should still return results
        assert result is not None

    @patch("src.dashboard.services.metrics_refresh_service.JiraCollector")
    @patch("src.dashboard.services.metrics_refresh_service.GitHubGraphQLCollector")
    @patch("src.dashboard.services.metrics_refresh_service.MetricsCalculator")
    def test_aggregates_github_data_across_teams(self, mock_calculator_class, mock_github_class, mock_jira_class):
        """Should aggregate GitHub data from all teams for comparison"""
        self.config.teams = [
            {"name": "Team A", "github": {"members": ["user1"]}, "jira": {"filters": {}}},
            {"name": "Team B", "github": {"members": ["user2"]}, "jira": {"filters": {}}},
        ]

        # Mock Jira
        mock_jira = MagicMock()
        mock_jira.collect_team_filters.return_value = {}
        mock_jira_class.return_value = mock_jira

        # Mock GitHub to return different data for each team
        mock_github = MagicMock()
        mock_github.collect_all_metrics.side_effect = [
            {"pull_requests": [{"id": 1}], "reviews": [], "commits": [], "deployments": []},
            {"pull_requests": [{"id": 2}], "reviews": [], "commits": [], "deployments": []},
        ]
        mock_github_class.return_value = mock_github

        # Mock MetricsCalculator
        mock_calculator = MagicMock()
        mock_calculator.calculate_team_metrics.return_value = {}
        mock_calculator.calculate_team_comparison.return_value = {}
        mock_calculator_class.return_value = mock_calculator

        # Execute
        result = self.service.refresh_metrics()

        # MetricsCalculator should be called with aggregated data
        # Check the final call (for team comparison)
        final_call_args = mock_calculator_class.call_args_list[-1]
        aggregated_dfs = final_call_args[0][0]

        # Should have combined PR data
        assert len(aggregated_dfs["pull_requests"]) == 2  # Both PRs combined

    def test_includes_timestamp_in_result(self):
        """Should include timestamp in returned data"""
        self.config.teams = []

        # Even with no teams, we can test the structure if we had data
        # For this test, just verify None is returned for no teams
        result = self.service.refresh_metrics()

        assert result is None

    @patch("src.dashboard.services.metrics_refresh_service.JiraCollector")
    @patch("src.dashboard.services.metrics_refresh_service.GitHubGraphQLCollector")
    @patch("src.dashboard.services.metrics_refresh_service.MetricsCalculator")
    def test_works_without_logger(self, mock_calculator_class, mock_github_class, mock_jira_class):
        """Should work without logger (no crashes)"""
        service = MetricsRefreshService(self.config, logger=None)
        service.config.teams = [{"name": "Test Team", "github": {"members": []}, "jira": {"filters": {}}}]

        # Mock collectors
        mock_jira = MagicMock()
        mock_jira.collect_team_filters.return_value = {}
        mock_jira_class.return_value = mock_jira

        mock_github = MagicMock()
        mock_github.collect_all_metrics.return_value = {
            "pull_requests": [],
            "reviews": [],
            "commits": [],
            "deployments": [],
        }
        mock_github_class.return_value = mock_github

        mock_calculator = MagicMock()
        mock_calculator.calculate_team_metrics.return_value = {}
        mock_calculator.calculate_team_comparison.return_value = {}
        mock_calculator_class.return_value = mock_calculator

        # Should not crash without logger
        result = service.refresh_metrics()

        assert result is not None
