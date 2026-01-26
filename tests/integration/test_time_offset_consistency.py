"""Integration tests for time_offset_days consistency across collectors"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector


class TestTimeOffsetConsistency:
    """Test that time_offset_days is applied consistently across collectors"""

    def test_github_jira_time_offset_alignment(self):
        """Test that GitHub and Jira collectors use same time offset"""
        days_back = 90
        time_offset_days = 180

        # Create GitHub collector
        github_collector = GitHubGraphQLCollector(
            token="test_token",
            organization="test-org",
            teams=["test-team"],
            days_back=days_back,
            time_offset_days=time_offset_days,
        )

        # Create Jira collector (mock JIRA connection)
        with patch("src.collectors.jira_collector.JIRA") as mock_jira:
            mock_jira.return_value = MagicMock()
            jira_collector = JiraCollector(
                server="https://jira.example.com",
                username="test",
                api_token="test",
                project_keys=["TEST"],
                days_back=days_back,
                time_offset_days=time_offset_days,
            )

            # Both should have the same since_date
            github_since = github_collector.since_date
            jira_since = jira_collector.since_date

            # Allow 1 second tolerance
            assert abs((github_since - jira_since).total_seconds()) < 1

    def test_zero_offset_backward_compatibility(self):
        """Test that time_offset_days=0 maintains existing behavior"""
        days_back = 90
        time_offset_days = 0

        github_collector = GitHubGraphQLCollector(
            token="test_token",
            organization="test-org",
            teams=["test-team"],
            days_back=days_back,
            time_offset_days=time_offset_days,
        )

        # Create Jira collector (mock JIRA connection)
        with patch("src.collectors.jira_collector.JIRA") as mock_jira:
            mock_jira.return_value = MagicMock()
            jira_collector = JiraCollector(
                server="https://jira.example.com",
                username="test",
                api_token="test",
                project_keys=["TEST"],
                days_back=days_back,
                time_offset_days=time_offset_days,
            )

            # Both should use days_back only
            expected_date = datetime.now(timezone.utc) - timedelta(days=90)

            assert abs((github_collector.since_date - expected_date).total_seconds()) < 1
            assert abs((jira_collector.since_date - expected_date).total_seconds()) < 1
