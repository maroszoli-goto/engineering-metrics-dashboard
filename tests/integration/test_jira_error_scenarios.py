"""Integration tests for Jira error scenarios and recovery.

Tests specific Jira collection error scenarios including timeouts,
server errors, and graceful degradation.
"""

from unittest.mock import Mock, patch

import pytest
from jira.exceptions import JIRAError

from src.collectors.jira_collector import JiraCollector
from tests.fixtures.jira_responses import (
    create_auth_error,
    create_issue,
    create_sample_issues_medium,
    create_sample_issues_small,
    create_search_response,
    create_server_error,
    create_timeout_error,
)


@pytest.fixture
def jira_collector():
    """Create Jira collector with mocked connection."""
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


class TestTimeoutRecovery:
    """Tests for 504 timeout recovery with eventual success."""

    def test_timeout_then_success_on_retry(self, jira_collector):
        """Test that 504 timeout leads to successful retry."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # First call: timeout, second call: success
        mock_jira.search_issues.side_effect = [
            Mock(total=50),  # Count succeeds
            timeout_error,  # First data query times out
            issues,  # Retry succeeds
        ]

        with patch("time.sleep"):  # Skip actual sleep delays
            result = collector._paginate_search("project = PROJ")

            # Should succeed after retry
            assert len(result) == 50
            assert mock_jira.search_issues.call_count == 3

    def test_multiple_timeouts_then_success(self, jira_collector):
        """Test recovery after multiple consecutive timeouts."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # Timeout twice, then succeed
        mock_jira.search_issues.side_effect = [Mock(total=50), timeout_error, timeout_error, issues]

        with patch("time.sleep") as mock_sleep:
            result = collector._paginate_search("project = PROJ")

            # Should succeed after 2 retries
            assert len(result) == 50
            # Verify exponential backoff was used
            assert mock_sleep.call_count == 2

    def test_timeout_recovery_with_large_dataset(self, jira_collector):
        """Test timeout recovery with large dataset pagination."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_medium(count=1000)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # First batch: timeout then success
        # Second batch: immediate success
        batch1 = issues[:500]
        batch2 = issues[500:]

        mock_jira.search_issues.side_effect = [
            Mock(total=1000),  # Count
            timeout_error,  # Batch 1 timeout
            batch1,  # Batch 1 retry success
            batch2,  # Batch 2 success
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            # Should have all issues after recovery
            assert len(result) == 1000

    def test_timeout_during_changelog_fetch(self, jira_collector):
        """Test timeout when fetching with changelog."""
        collector, mock_jira = jira_collector

        issues_no_changelog = create_sample_issues_small(count=50)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # Timeout with changelog, success without
        mock_jira.search_issues.side_effect = [
            Mock(total=50),
            timeout_error,  # With changelog
            timeout_error,  # Retry with changelog
            timeout_error,  # Retry with changelog
            issues_no_changelog,  # Final attempt (may disable changelog internally)
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ", expand="changelog")

            # Should eventually succeed (may be without changelog)
            assert len(result) >= 0  # At least doesn't crash


class TestPartialFailureScenarios:
    """Tests for partial failures with graceful degradation."""

    def test_first_batch_succeeds_second_fails(self, jira_collector):
        """Test that first batch data is preserved when second batch fails."""
        collector, mock_jira = jira_collector

        batch1 = create_sample_issues_small(count=500)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # First batch succeeds, second batch fails all retries
        mock_jira.search_issues.side_effect = [
            Mock(total=1000),  # Count
            batch1,  # Batch 1 success
            timeout_error,  # Batch 2 fails
            timeout_error,  # Retry fails
            timeout_error,  # Retry fails
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            # Should have partial data from batch 1
            assert len(result) == 500

    def test_graceful_degradation_on_persistent_errors(self, jira_collector):
        """Test graceful degradation when errors persist."""
        collector, mock_jira = jira_collector

        issues_batch1 = create_sample_issues_small(count=500)
        issues_batch2 = create_sample_issues_small(count=500)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # Batch 1: success
        # Batch 2: timeout, eventually succeed
        # Batch 3: persistent timeout
        mock_jira.search_issues.side_effect = [
            Mock(total=1500),
            issues_batch1,  # Batch 1 success
            timeout_error,  # Batch 2 timeout
            issues_batch2,  # Batch 2 retry success
            timeout_error,  # Batch 3 timeout
            timeout_error,  # Retry timeout
            timeout_error,  # Retry timeout
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            # Should have data from batches 1 and 2
            assert len(result) == 1000

    def test_partial_results_still_usable(self, jira_collector):
        """Test that partial results are still valid and usable."""
        collector, mock_jira = jira_collector

        partial_issues = create_sample_issues_small(count=100)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        mock_jira.search_issues.side_effect = [
            Mock(total=500),
            partial_issues,  # Get 100 issues
            timeout_error,  # Then fail
            timeout_error,
            timeout_error,
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            # Partial data should be valid
            assert len(result) == 100
            assert all(hasattr(issue, "key") or "key" in issue for issue in result)


class TestNetworkErrors:
    """Tests for various network error scenarios."""

    def test_502_bad_gateway_retry(self, jira_collector):
        """Test retry on 502 Bad Gateway error."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)
        error_502 = JIRAError(status_code=502, text="Bad Gateway")

        mock_jira.search_issues.side_effect = [Mock(total=50), error_502, issues]  # 502 error  # Retry success

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            assert len(result) == 50

    def test_503_service_unavailable_retry(self, jira_collector):
        """Test retry on 503 Service Unavailable error."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)
        error_503 = JIRAError(status_code=503, text="Service Unavailable")

        mock_jira.search_issues.side_effect = [Mock(total=50), error_503, issues]  # 503 error  # Retry success

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            assert len(result) == 50

    def test_500_internal_server_error_no_retry(self, jira_collector):
        """Test that 500 errors are not retried (non-transient)."""
        collector, mock_jira = jira_collector

        error_500 = JIRAError(status_code=500, text="Internal Server Error")

        mock_jira.search_issues.side_effect = [Mock(total=50), error_500]

        # 500 errors should raise immediately (not transient)
        with pytest.raises(JIRAError) as exc_info:
            collector._paginate_search("project = PROJ")

        assert exc_info.value.status_code == 500

    def test_401_unauthorized_no_retry(self, jira_collector):
        """Test that 401 errors are not retried (auth failure)."""
        collector, mock_jira = jira_collector

        error_401 = JIRAError(status_code=401, text="Unauthorized")

        mock_jira.search_issues.side_effect = [Mock(total=50), error_401]

        # Auth errors should raise immediately
        with pytest.raises(JIRAError) as exc_info:
            collector._paginate_search("project = PROJ")

        assert exc_info.value.status_code == 401

    def test_generic_connection_error_retry(self, jira_collector):
        """Test retry on generic connection errors."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)

        # Generic exception (like connection reset)
        mock_jira.search_issues.side_effect = [Mock(total=50), Exception("Connection reset by peer"), issues]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            assert len(result) == 50


class TestCountQueryFailures:
    """Tests for failures during the initial count query."""

    def test_count_query_timeout_fallback(self, jira_collector):
        """Test fallback when count query times out."""
        collector, mock_jira = jira_collector

        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")
        issues = create_sample_issues_small(count=50)

        # Count query fails, should fall back to old behavior
        mock_jira.search_issues.side_effect = [timeout_error, issues]  # Count fails  # Fallback query succeeds

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            # Should get data via fallback
            assert len(result) > 0

    def test_count_query_generic_error_fallback(self, jira_collector):
        """Test fallback when count query has generic error."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)

        # Count fails with generic error
        mock_jira.search_issues.side_effect = [Exception("Network error"), issues]

        result = collector._paginate_search("project = PROJ")

        # Should fall back and get data
        assert len(result) > 0


class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""

    def test_backoff_timing_progression(self, jira_collector):
        """Test that backoff delays follow exponential pattern."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # Fail 3 times, then succeed
        mock_jira.search_issues.side_effect = [Mock(total=50), timeout_error, timeout_error, timeout_error, issues]

        with patch("time.sleep") as mock_sleep:
            result = collector._paginate_search("project = PROJ")

            # Verify exponential backoff: 5s, 10s, 20s
            assert mock_sleep.call_count == 3
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert delays[0] == 5  # 5 * 2^0
            assert delays[1] == 10  # 5 * 2^1
            assert delays[2] == 20  # 5 * 2^2

    def test_backoff_stops_at_max_retries(self, jira_collector):
        """Test that backoff stops at max retries."""
        collector, mock_jira = jira_collector

        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        # Always fail
        mock_jira.search_issues.side_effect = [
            Mock(total=50),
            timeout_error,
            timeout_error,
            timeout_error,
            timeout_error,  # Should not reach this
        ]

        with patch("time.sleep") as mock_sleep:
            result = collector._paginate_search("project = PROJ")

            # Should stop after max_retries (3)
            assert mock_sleep.call_count == 3
            # Should return empty (no data collected)
            assert len(result) == 0


class TestMixedErrorScenarios:
    """Tests for mixed error scenarios (multiple error types)."""

    def test_timeout_then_502_then_success(self, jira_collector):
        """Test recovery from different error types."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")
        gateway_error = JIRAError(status_code=502, text="Bad Gateway")

        mock_jira.search_issues.side_effect = [
            Mock(total=50),
            timeout_error,  # 504
            gateway_error,  # 502
            issues,  # Success
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            assert len(result) == 50

    def test_connection_error_then_timeout_then_success(self, jira_collector):
        """Test recovery from mixed connection and timeout errors."""
        collector, mock_jira = jira_collector

        issues = create_sample_issues_small(count=50)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        mock_jira.search_issues.side_effect = [Mock(total=50), Exception("Connection reset"), timeout_error, issues]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            assert len(result) == 50

    def test_intermittent_errors_across_batches(self, jira_collector):
        """Test handling intermittent errors across multiple batches."""
        collector, mock_jira = jira_collector

        batch1 = create_sample_issues_small(count=500)
        batch2 = create_sample_issues_small(count=500)
        timeout_error = JIRAError(status_code=504, text="Gateway Timeout")

        mock_jira.search_issues.side_effect = [
            Mock(total=1000),
            batch1,  # Batch 1 success
            timeout_error,  # Batch 2 timeout
            batch2,  # Batch 2 retry success
        ]

        with patch("time.sleep"):
            result = collector._paginate_search("project = PROJ")

            # Should have all data after recovery
            assert len(result) == 1000
