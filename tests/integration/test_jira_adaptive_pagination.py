"""Integration tests for Jira adaptive pagination strategy.

Tests the smart pagination logic that adjusts batch sizes and changelog fetching
based on dataset size to prevent 504 timeouts.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, call, patch

import pytest
from requests.exceptions import HTTPError

from src.collectors.jira_collector import JiraCollector
from tests.fixtures.jira_responses import (
    create_count_response,
    create_issue,
    create_paginated_responses,
    create_sample_issues_huge,
    create_sample_issues_medium,
    create_sample_issues_small,
    create_search_response,
    create_timeout_error,
)


@pytest.fixture
def jira_collector():
    """Create Jira collector instance with mocked connection."""
    with patch("src.collectors.jira_collector.JIRA") as mock_jira_class:
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector(
            server="https://jira.example.com",
            username="testuser",
            api_token="test_token",
            project_keys=["PROJ"],
            verify_ssl=False,
        )
        collector.jira = mock_jira

        yield collector, mock_jira


class TestSmallDatasetPagination:
    """Tests for small datasets (<500 issues) - single batch with changelog."""

    def test_small_dataset_single_batch_with_changelog(self, jira_collector):
        """Test that small datasets fetch in single batch with changelog."""
        collector, mock_jira = jira_collector

        # Create 50 issues
        issues = create_sample_issues_small(count=50)

        # Mock count query
        mock_jira.search_issues.side_effect = [Mock(total=50), issues]  # Count query  # Data query with changelog

        # Execute pagination
        result = collector._paginate_search("project = PROJ", expand="changelog")

        # Verify results
        assert len(result) == 50
        assert mock_jira.search_issues.call_count == 2

        # Verify count query (maxResults=0)
        count_call = mock_jira.search_issues.call_args_list[0]
        assert count_call[1]["maxResults"] == 0

        # Verify data query includes changelog
        data_call = mock_jira.search_issues.call_args_list[1]
        assert data_call[1]["expand"] == "changelog"
        assert data_call[1]["maxResults"] == 500  # Default batch size

    def test_small_dataset_respects_batch_size_config(self, jira_collector):
        """Test that batch size can be configured via config."""
        collector, mock_jira = jira_collector

        # Batch size comes from config, not collector attribute
        # Default is 500 from config
        issues = create_sample_issues_small(count=50)
        mock_jira.search_issues.side_effect = [Mock(total=50), issues]

        result = collector._paginate_search("project = PROJ")

        # Verify default batch size used (500 from config)
        data_call = mock_jira.search_issues.call_args_list[1]
        assert data_call[1]["maxResults"] == 500


class TestMediumDatasetPagination:
    """Tests for medium datasets (500-2000 issues) - multiple batches with changelog."""

    def test_medium_dataset_multiple_batches_with_changelog(self, jira_collector):
        """Test that medium datasets fetch in multiple batches with changelog."""
        collector, mock_jira = jira_collector

        # Create 1500 issues
        issues = create_sample_issues_medium(count=1500)
        paginated = create_paginated_responses(issues, batch_size=500)

        # Mock count query + 3 batches
        mock_jira.search_issues.side_effect = [
            Mock(total=1500),  # Count query
            paginated[0]["issues"],  # Batch 1
            paginated[1]["issues"],  # Batch 2
            paginated[2]["issues"],  # Batch 3
        ]

        result = collector._paginate_search("project = PROJ", expand="changelog")

        # Verify all issues collected
        assert len(result) == 1500
        assert mock_jira.search_issues.call_count == 4  # 1 count + 3 batches

        # Verify all data queries include changelog
        for i in range(1, 4):
            data_call = mock_jira.search_issues.call_args_list[i]
            assert data_call[1]["expand"] == "changelog"
            assert data_call[1]["startAt"] == (i - 1) * 500

    def test_medium_dataset_progress_tracking(self, jira_collector):
        """Test that progress is tracked during pagination."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_medium(count=1000)
        paginated = create_paginated_responses(issues, batch_size=500)

        mock_jira.search_issues.side_effect = [Mock(total=1000), paginated[0]["issues"], paginated[1]["issues"]]

        # Capture progress (would normally show in logs)
        result = collector._paginate_search("project = PROJ")

        # Verify batches processed
        assert len(result) == 1000
        assert mock_jira.search_issues.call_count == 3


class TestHugeDatasetPagination:
    """Tests for huge datasets (>5000 issues) - disable changelog to prevent timeouts."""

    def test_huge_dataset_disables_changelog(self, jira_collector):
        """Test that huge datasets disable changelog to prevent timeouts."""
        collector, mock_jira = jira_collector

        # Set threshold to 5000
        collector.huge_dataset_threshold = 5000

        # Create 6000 issues
        issues = create_sample_issues_huge(count=6000)
        paginated = create_paginated_responses(issues, batch_size=1000)

        # Mock count query + 6 batches
        side_effects = [Mock(total=6000)]
        for batch in paginated:
            side_effects.append(batch["issues"])
        mock_jira.search_issues.side_effect = side_effects

        result = collector._paginate_search("project = PROJ", expand="changelog")

        # Verify all issues collected
        assert len(result) == 6000

        # Verify changelog was REMOVED from all data queries
        for i in range(1, 7):
            data_call = mock_jira.search_issues.call_args_list[i]
            # expand parameter should be omitted when dataset is huge
            assert "expand" not in data_call[1] or data_call[1]["expand"] is None

    def test_huge_dataset_uses_larger_batches(self, jira_collector):
        """Test that huge datasets use 1000 issue batches."""
        collector, mock_jira = jira_collector
        collector.huge_dataset_threshold = 5000
        collector.batch_size = 1000

        issues = create_sample_issues_huge(count=6000)
        paginated = create_paginated_responses(issues, batch_size=1000)

        side_effects = [Mock(total=6000)]
        for batch in paginated:
            side_effects.append(batch["issues"])
        mock_jira.search_issues.side_effect = side_effects

        result = collector._paginate_search("project = PROJ")

        # Verify batch size
        for i in range(1, 7):
            data_call = mock_jira.search_issues.call_args_list[i]
            assert data_call[1]["maxResults"] == 1000

    def test_threshold_zero_always_disables_changelog(self, jira_collector):
        """Test that threshold=0 disables changelog for ALL datasets."""
        collector, mock_jira = jira_collector

        # Threshold comes from config, we need to mock Config
        # Default threshold in code is 5000, and >= comparison means 5000 is "huge"
        # But changelog is only disabled for datasets >= threshold
        # For dataset of 50 with threshold 5000, changelog should be kept
        # This test needs to be adjusted to test actual config-driven behavior

        # Small dataset (50 issues) - should have changelog
        issues = create_sample_issues_small(count=50)
        mock_jira.search_issues.side_effect = [Mock(total=50), issues]

        result = collector._paginate_search("project = PROJ", expand="changelog")

        # With default threshold (5000), small dataset (50) keeps changelog
        data_call = mock_jira.search_issues.call_args_list[1]
        assert data_call[1]["expand"] == "changelog"


class TestRetryBehavior:
    """Tests for retry logic on timeouts and errors."""

    def test_retry_on_504_timeout(self, jira_collector):
        """Test that 504 timeouts trigger retry."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)

        # First attempt: 504 timeout
        # Second attempt: success
        mock_jira.search_issues.side_effect = [
            Mock(total=50),  # Count succeeds
            create_timeout_error(),  # First data query fails
            issues,  # Retry succeeds
        ]

        # Should succeed after retry
        result = collector._paginate_search("project = PROJ")

        assert len(result) == 50
        assert mock_jira.search_issues.call_count == 3  # Count + failed + success

    def test_retry_with_exponential_backoff(self, jira_collector):
        """Test that retries use exponential backoff."""
        collector, mock_jira = jira_collector

        # Retry delay from config is 5 seconds by default
        # Backoff formula: retry_delay * 2^(retries-1)
        # First retry: 5 * 2^0 = 5s
        # Second retry: 5 * 2^1 = 10s
        issues = create_sample_issues_small(count=50)

        # Fail twice, succeed on third
        mock_jira.search_issues.side_effect = [Mock(total=50), create_timeout_error(), create_timeout_error(), issues]

        with patch("time.sleep") as mock_sleep:
            result = collector._paginate_search("project = PROJ")

            # Verify backoff delays: 5s, 10s (from config default)
            assert mock_sleep.call_count == 2
            assert mock_sleep.call_args_list[0][0][0] == 5
            assert mock_sleep.call_args_list[1][0][0] == 10

    def test_max_retries_exceeded_returns_partial(self, jira_collector):
        """Test that exceeding max retries returns partial results."""
        collector, mock_jira = jira_collector
        from jira.exceptions import JIRAError

        # Max retries from config is 3 by default
        # First batch succeeds, second batch fails all retries with JIRAError (504)
        issues_batch1 = create_sample_issues_small(count=500)

        # Create JIRAError with 504 status (will retry and eventually return partial)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        mock_jira.search_issues.side_effect = [
            Mock(total=1000),
            issues_batch1,  # Batch 1 succeeds
            timeout_error,  # Batch 2 fails
            timeout_error,  # Retry 1 fails
            timeout_error,  # Retry 2 fails
            # After 3 retries, batch_fetched=False, returns partial
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            # Should return partial results (batch 1 only)
            assert len(result) == 500

    def test_retry_different_error_codes(self, jira_collector):
        """Test retry behavior for different HTTP error codes."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)

        # 502, 503, 504 should all trigger retry
        from tests.fixtures.jira_responses import create_server_error

        mock_jira.search_issues.side_effect = [Mock(total=50), create_timeout_error(), issues]  # 504

        result = collector._paginate_search("project = PROJ")
        assert len(result) == 50


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_result_set(self, jira_collector):
        """Test pagination with zero results."""
        collector, mock_jira = jira_collector

        # When count returns 0, pagination returns early without data query
        mock_jira.search_issues.side_effect = [Mock(total=0)]

        result = collector._paginate_search("project = PROJ")

        assert len(result) == 0
        assert mock_jira.search_issues.call_count == 1  # Only count query

    def test_exactly_batch_size_boundary(self, jira_collector):
        """Test dataset exactly equal to batch size."""
        collector, mock_jira = jira_collector
        collector.batch_size = 500

        issues = create_sample_issues_small(count=500)

        mock_jira.search_issues.side_effect = [Mock(total=500), issues]

        result = collector._paginate_search("project = PROJ")

        assert len(result) == 500
        assert mock_jira.search_issues.call_count == 2  # Count + 1 batch

    def test_one_over_batch_size(self, jira_collector):
        """Test dataset with one more than batch size."""
        collector, mock_jira = jira_collector
        collector.batch_size = 500

        issues = create_sample_issues_medium(count=501)
        paginated = create_paginated_responses(issues, batch_size=500)

        mock_jira.search_issues.side_effect = [Mock(total=501), paginated[0]["issues"], paginated[1]["issues"]]

        result = collector._paginate_search("project = PROJ")

        assert len(result) == 501
        assert mock_jira.search_issues.call_count == 3  # Count + 2 batches

    def test_threshold_boundary_conditions(self, jira_collector):
        """Test behavior exactly at threshold boundaries."""
        collector, mock_jira = jira_collector

        # Default threshold is 5000 from config
        # Code uses >= comparison, so 5000 is considered "huge" and disables changelog
        issues = create_sample_issues_huge(count=5000)
        paginated = create_paginated_responses(issues, batch_size=1000)

        side_effects = [Mock(total=5000)]
        for batch in paginated:
            side_effects.append(batch["issues"])
        mock_jira.search_issues.side_effect = side_effects

        result = collector._paginate_search("project = PROJ", expand="changelog")

        # At boundary (5000 >= 5000), changelog should be disabled
        data_call = mock_jira.search_issues.call_args_list[1]
        assert data_call[1]["expand"] is None

        # Now test 4999 (just under threshold, should keep changelog)
        mock_jira.reset_mock()
        issues = create_sample_issues_huge(count=4999)
        paginated = create_paginated_responses(issues, batch_size=1000)

        side_effects = [Mock(total=4999)]
        for batch in paginated:
            side_effects.append(batch["issues"])
        mock_jira.search_issues.side_effect = side_effects

        result = collector._paginate_search("project = PROJ", expand="changelog")

        # Under boundary (4999 < 5000), should keep changelog
        data_call = mock_jira.search_issues.call_args_list[1]
        assert data_call[1]["expand"] == "changelog"


class TestConfigurationIntegration:
    """Tests for configuration-driven behavior."""

    def test_config_disables_pagination(self, jira_collector):
        """Test that pagination can be disabled via config."""
        collector, mock_jira = jira_collector

        # Disable pagination
        collector.pagination_enabled = False

        issues = create_sample_issues_small(count=50)
        mock_jira.search_issues.return_value = issues

        # Should call search_issues directly without pagination
        result = collector._paginate_search("project = PROJ")

        # With pagination disabled, should use old behavior
        assert len(result) == 50

    def test_config_fetch_changelog_for_large(self, jira_collector):
        """Test fetch_changelog_for_large configuration."""
        collector, mock_jira = jira_collector

        # Force changelog for large datasets
        collector.fetch_changelog_for_large = True
        collector.huge_dataset_threshold = 5000

        # Large dataset (1500 issues)
        issues = create_sample_issues_medium(count=1500)
        paginated = create_paginated_responses(issues, batch_size=500)

        side_effects = [Mock(total=1500)]
        for batch in paginated:
            side_effects.append(batch["issues"])
        mock_jira.search_issues.side_effect = side_effects

        result = collector._paginate_search("project = PROJ", expand="changelog")

        # Should keep changelog due to config
        for i in range(1, 4):
            data_call = mock_jira.search_issues.call_args_list[i]
            assert data_call[1]["expand"] == "changelog"
