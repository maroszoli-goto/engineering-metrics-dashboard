"""
Unit tests for Jira pagination logic (_paginate_search method)

Tests cover:
- Adaptive batch sizing based on dataset size
- Changelog expansion/disabling logic
- Retry logic for 504/503/502 errors
- Exponential backoff
- Progress tracking
- Partial results on failure
- Edge cases (empty results, count failures, etc.)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from jira.exceptions import JIRAError

from src.collectors.jira_collector import JiraCollector


class TestPaginationSmallDataset:
    """Tests for small datasets (<500 issues) - single batch with changelog"""

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_small_dataset_single_batch(self, mock_jira_class, mock_config_class):
        # Arrange - 50 issues (small dataset)
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
            "fetch_changelog_for_large": False,
            "max_retries": 3,
            "retry_delay_seconds": 5,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 50

        mock_issues = [Mock(key=f"PROJ-{i}") for i in range(50)]
        mock_jira.search_issues.side_effect = [
            mock_count_result,  # Count query
            mock_issues,  # Single batch
        ]
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", expand="changelog", context_name="test")

        # Assert
        assert len(result) == 50
        assert mock_jira.search_issues.call_count == 2
        # First call: count query
        mock_jira.search_issues.assert_any_call("project = PROJ", maxResults=0)
        # Second call: fetch with changelog
        mock_jira.search_issues.assert_any_call(
            "project = PROJ", startAt=0, maxResults=500, fields=None, expand="changelog"
        )

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_empty_dataset_returns_immediately(self, mock_jira_class, mock_config_class):
        # Arrange - 0 issues
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 0
        mock_jira.search_issues.return_value = mock_count_result

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert
        assert result == []
        assert mock_jira.search_issues.call_count == 1  # Only count query


class TestPaginationMediumDataset:
    """Tests for medium datasets (500-2000 issues) - multiple batches"""

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_medium_dataset_multiple_batches(self, mock_jira_class, mock_config_class):
        # Arrange - 1500 issues (3 batches of 500)
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
            "max_retries": 3,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 1500

        # Create 3 batches of 500 issues each
        batch1 = [Mock(key=f"PROJ-{i}") for i in range(0, 500)]
        batch2 = [Mock(key=f"PROJ-{i}") for i in range(500, 1000)]
        batch3 = [Mock(key=f"PROJ-{i}") for i in range(1000, 1500)]

        mock_jira.search_issues.side_effect = [
            mock_count_result,  # Count query
            batch1,  # First batch
            batch2,  # Second batch
            batch3,  # Third batch
        ]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", expand="changelog", context_name="test")

        # Assert
        assert len(result) == 1500
        assert mock_jira.search_issues.call_count == 4

        # Verify correct startAt offsets
        calls = mock_jira.search_issues.call_args_list
        assert calls[1][1]["startAt"] == 0
        assert calls[2][1]["startAt"] == 500
        assert calls[3][1]["startAt"] == 1000


class TestPaginationHugeDataset:
    """Tests for huge datasets (5000+ issues) - changelog disabled"""

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_huge_dataset_disables_changelog(self, mock_jira_class, mock_config_class):
        # Arrange - 6000 issues (exceeds threshold)
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
            "fetch_changelog_for_large": False,  # Disable changelog for huge datasets
            "max_retries": 3,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 6000

        # Create batches (6 batches of 1000 each since huge datasets use batch_size=1000)
        batches = [[Mock(key=f"PROJ-{i}") for i in range(start, start + 1000)] for start in range(0, 6000, 1000)]

        mock_jira.search_issues.side_effect = [mock_count_result] + batches

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", expand="changelog", context_name="test")

        # Assert
        assert len(result) == 6000
        # Verify changelog was disabled (expand=None instead of "changelog")
        for call_args in mock_jira.search_issues.call_args_list[1:]:  # Skip count query
            assert call_args[1]["expand"] is None

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_huge_dataset_uses_larger_batch_size(self, mock_jira_class, mock_config_class):
        # Arrange - 6000 issues
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,  # Default
            "huge_dataset_threshold": 5000,
            "fetch_changelog_for_large": False,
            "max_retries": 3,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 6000

        batches = [[Mock(key=f"PROJ-{i}") for i in range(start, start + 1000)] for start in range(0, 6000, 1000)]
        mock_jira.search_issues.side_effect = [mock_count_result] + batches

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert
        # Verify batch_size was increased to 1000 for huge datasets
        for call_args in mock_jira.search_issues.call_args_list[1:]:
            assert call_args[1]["maxResults"] == 1000


class TestPaginationRetryLogic:
    """Tests for retry logic on 504/503/502 errors"""

    @patch("src.collectors.jira_collector.time.sleep")
    @patch("src.collectors.jira_collector.JIRA")
    @patch("src.config.Config")
    def test_retries_on_504_timeout(self, mock_config_class, mock_jira_class, mock_sleep):
        # Arrange
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
            "max_retries": 3,
            "retry_delay_seconds": 5,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 100

        # First attempt fails with 504, second succeeds
        mock_error = JIRAError(status_code=504, text="Gateway Timeout")
        mock_issues = [Mock(key=f"PROJ-{i}") for i in range(100)]

        mock_jira.search_issues.side_effect = [
            mock_count_result,  # Count
            mock_error,  # First attempt - 504
            mock_issues,  # Second attempt - success
        ]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert
        assert len(result) == 100
        assert mock_jira.search_issues.call_count == 3
        mock_sleep.assert_called_once_with(5)  # First retry delay

    @patch("src.collectors.jira_collector.time.sleep")
    @patch("src.collectors.jira_collector.JIRA")
    @patch("src.config.Config")
    def test_exponential_backoff(self, mock_config_class, mock_jira_class, mock_sleep):
        # Arrange
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
            "max_retries": 4,
            "retry_delay_seconds": 5,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 100

        # Fail 3 times, then succeed
        mock_error = JIRAError(status_code=503, text="Service Unavailable")
        mock_issues = [Mock(key=f"PROJ-{i}") for i in range(100)]

        mock_jira.search_issues.side_effect = [
            mock_count_result,  # Count
            mock_error,  # Attempt 1 - fail
            mock_error,  # Attempt 2 - fail
            mock_error,  # Attempt 3 - fail
            mock_issues,  # Attempt 4 - success
        ]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert
        assert len(result) == 100
        # Verify exponential backoff: 5s, 10s, 20s
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == 5  # 5 * 2^0
        assert mock_sleep.call_args_list[1][0][0] == 10  # 5 * 2^1
        assert mock_sleep.call_args_list[2][0][0] == 20  # 5 * 2^2

    @patch("src.collectors.jira_collector.time.sleep")
    @patch("src.collectors.jira_collector.JIRA")
    @patch("src.config.Config")
    def test_returns_partial_results_after_max_retries(self, mock_config_class, mock_jira_class, mock_sleep):
        # Arrange - 200 issues, but second batch fails
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 100,
            "huge_dataset_threshold": 5000,
            "max_retries": 2,
            "retry_delay_seconds": 5,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 200

        batch1 = [Mock(key=f"PROJ-{i}") for i in range(100)]
        mock_error = JIRAError(status_code=504, text="Gateway Timeout")

        # First batch succeeds, second batch fails all retries
        mock_jira.search_issues.side_effect = [
            mock_count_result,  # Count
            batch1,  # First batch - success
            mock_error,  # Second batch attempt 1 - fail
            mock_error,  # Second batch attempt 2 - fail
        ]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert - Returns partial results (first 100 issues)
        assert len(result) == 100
        assert mock_sleep.call_count == 2  # Retried twice


class TestPaginationEdgeCases:
    """Tests for edge cases and error conditions"""

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_pagination_disabled_fallback(self, mock_jira_class, mock_config_class):
        # Arrange
        mock_config = Mock()
        mock_config.jira_pagination = {"enabled": False}
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_issues = [Mock(key=f"PROJ-{i}") for i in range(500)]
        mock_jira.search_issues.return_value = mock_issues

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert - Falls back to old behavior (single 1000-issue query)
        assert len(result) == 500
        mock_jira.search_issues.assert_called_once_with("project = PROJ", maxResults=1000, fields=None, expand=None)

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_count_query_failure_fallback(self, mock_jira_class, mock_config_class):
        # Arrange
        mock_config = Mock()
        mock_config.jira_pagination = {"enabled": True, "batch_size": 500}
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        # Count query fails
        mock_jira.search_issues.side_effect = [
            Exception("Network error"),  # Count fails
            [Mock(key=f"PROJ-{i}") for i in range(100)],  # Fallback query
        ]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert - Falls back to old behavior
        assert len(result) == 100
        assert mock_jira.search_issues.call_count == 2

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_non_timeout_error_raises_immediately(self, mock_jira_class, mock_config_class):
        # Arrange - 400 error should not retry
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "max_retries": 3,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 100

        # 400 Bad Request should raise immediately (not retry)
        mock_error = JIRAError(status_code=400, text="Bad Request")
        mock_jira.search_issues.side_effect = [mock_count_result, mock_error]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act & Assert
        with pytest.raises(JIRAError) as exc_info:
            collector._paginate_search("project = PROJ", context_name="test")

        assert exc_info.value.status_code == 400
        assert mock_jira.search_issues.call_count == 2  # Count + 1 attempt (no retries)

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_last_batch_smaller_than_batch_size(self, mock_jira_class, mock_config_class):
        # Arrange - 250 issues with batch_size=100 (3 batches: 100, 100, 50)
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 100,
            "huge_dataset_threshold": 5000,
            "max_retries": 3,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 250

        batch1 = [Mock(key=f"PROJ-{i}") for i in range(0, 100)]
        batch2 = [Mock(key=f"PROJ-{i}") for i in range(100, 200)]
        batch3 = [Mock(key=f"PROJ-{i}") for i in range(200, 250)]  # Only 50 issues

        mock_jira.search_issues.side_effect = [mock_count_result, batch1, batch2, batch3]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", context_name="test")

        # Assert
        assert len(result) == 250
        assert mock_jira.search_issues.call_count == 4


class TestPaginationFieldsAndExpand:
    """Tests for fields and expand parameter handling"""

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_preserves_fields_parameter(self, mock_jira_class, mock_config_class):
        # Arrange
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 50
        mock_issues = [Mock(key=f"PROJ-{i}") for i in range(50)]
        mock_jira.search_issues.side_effect = [mock_count_result, mock_issues]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", fields="key,summary,status", context_name="test")

        # Assert
        mock_jira.search_issues.assert_any_call(
            "project = PROJ", startAt=0, maxResults=500, fields="key,summary,status", expand=None
        )

    @patch("src.config.Config")
    @patch("src.collectors.jira_collector.JIRA")
    def test_changelog_preserved_for_small_dataset(self, mock_jira_class, mock_config_class):
        # Arrange - 100 issues (below threshold)
        mock_config = Mock()
        mock_config.jira_pagination = {
            "enabled": True,
            "batch_size": 500,
            "huge_dataset_threshold": 5000,
            "fetch_changelog_for_large": False,
        }
        mock_config_class.return_value = mock_config

        mock_jira = Mock()
        mock_count_result = Mock()
        mock_count_result.total = 100
        mock_issues = [Mock(key=f"PROJ-{i}") for i in range(100)]
        mock_jira.search_issues.side_effect = [mock_count_result, mock_issues]

        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"], days_back=90)

        # Act
        result = collector._paginate_search("project = PROJ", expand="changelog", context_name="test")

        # Assert - Changelog should be preserved
        mock_jira.search_issues.assert_any_call(
            "project = PROJ", startAt=0, maxResults=500, fields=None, expand="changelog"
        )
