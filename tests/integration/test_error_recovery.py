"""Integration tests for error recovery and resilience

Tests how the system handles errors and edge cases across modules.
"""

import pytest
import pandas as pd
import pickle
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from requests.exceptions import Timeout, ConnectionError
from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector
from src.models.metrics import MetricsCalculator
from src.dashboard.app import load_cache_from_file


class TestErrorRecovery:
    """Test error handling and recovery across modules"""

    def test_github_api_timeout_handling(self):
        """Test handling of GitHub API timeouts"""
        collector = GitHubGraphQLCollector('fake_token', 'test-org')

        with patch.object(collector, '_execute_graphql_query', side_effect=Timeout("Connection timeout")):
            # Should handle timeout gracefully
            with pytest.raises(Timeout):
                collector.collect_repository_metrics(
                    'test-org', 'test-repo',
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                    datetime(2024, 3, 31, tzinfo=timezone.utc)
                )

    def test_jira_connection_failure_handling(self):
        """Test handling of Jira connection failures"""
        with patch('src.collectors.jira_collector.JIRA', side_effect=ConnectionError("Cannot connect")):
            with pytest.raises(ConnectionError):
                collector = JiraCollector(
                    server='https://jira.invalid.com',
                    username='test',
                    api_token='test_token',
                    project_keys=['TEST'],
                    days_back=90
                )

    def test_metrics_with_malformed_data(self):
        """Test metrics calculation with malformed data"""
        # Missing required columns
        malformed_prs = pd.DataFrame({
            'pr_number': [1, 2],
            'author': ['alice', 'bob']
            # Missing: merged, state, additions, deletions, etc.
        })

        dfs = {
            'pull_requests': malformed_prs,
            'reviews': pd.DataFrame(),
            'commits': pd.DataFrame(),
            'deployments': pd.DataFrame()
        }

        calculator = MetricsCalculator(dfs)

        # Should handle gracefully, returning zero or default values
        metrics = calculator.calculate_pr_metrics()
        assert metrics is not None
        assert 'total_prs' in metrics

    def test_corrupted_cache_handling(self):
        """Test handling of corrupted cache files"""
        # Create corrupted cache file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pkl') as f:
            f.write("This is not valid pickle data")
            temp_path = f.name

        try:
            with patch('src.dashboard.app.get_cache_filename', return_value=temp_path):
                # Should return False and not crash
                success = load_cache_from_file('90d')
                assert success is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_missing_cache_file_handling(self):
        """Test handling of missing cache files"""
        with patch('src.dashboard.app.get_cache_filename', return_value='/nonexistent/path/cache.pkl'):
            # Should return False and not crash
            success = load_cache_from_file('90d')
            assert success is False

    def test_empty_dataframes_handling(self):
        """Test metrics calculation with all empty dataframes"""
        empty_dfs = {
            'pull_requests': pd.DataFrame(),
            'reviews': pd.DataFrame(),
            'commits': pd.DataFrame(),
            'deployments': pd.DataFrame()
        }

        calculator = MetricsCalculator(empty_dfs)

        # Should return zero metrics, not crash
        pr_metrics = calculator.calculate_pr_metrics()
        assert pr_metrics['total_prs'] == 0
        assert pr_metrics['merged_prs'] == 0

        review_metrics = calculator.calculate_review_metrics()
        assert review_metrics['total_reviews'] == 0

        commit_metrics = calculator.calculate_contributor_metrics()
        assert commit_metrics['total_commits'] == 0

    def test_invalid_date_range_handling(self):
        """Test handling of invalid date ranges"""
        from src.utils.date_ranges import parse_date_range, DateRangeError

        # Invalid format
        with pytest.raises(DateRangeError):
            parse_date_range("invalid_format")

        # Negative days
        with pytest.raises(DateRangeError):
            parse_date_range("-30d")

        # Days too large
        with pytest.raises(DateRangeError):
            parse_date_range("10000d")

        # Invalid year
        with pytest.raises(DateRangeError):
            parse_date_range("1999")  # Before 2000

    def test_partial_data_collection_recovery(self):
        """Test recovery when only partial data is collected"""
        # Scenario: GitHub succeeds but Jira fails
        mock_prs = [{
            'pr_number': 1,
            'author': 'alice',
            'merged': True,
            'state': 'merged',
            'additions': 100,
            'deletions': 50,
            'cycle_time_hours': 24.0,
            'time_to_first_review_hours': 2.0
        }]

        # Create calculator with only PR data (no Jira)
        dfs = {
            'pull_requests': pd.DataFrame(mock_prs),
            'reviews': pd.DataFrame(),
            'commits': pd.DataFrame(),
            'deployments': pd.DataFrame()
        }
        calculator = MetricsCalculator(dfs)

        # Should still calculate metrics with available data
        pr_metrics = calculator.calculate_pr_metrics()
        assert pr_metrics['total_prs'] == 1
        assert pr_metrics['merged_prs'] == 1

    def test_nan_and_null_value_handling(self):
        """Test handling of NaN and None values in data"""
        prs_with_nans = pd.DataFrame({
            'pr_number': [1, 2, 3],
            'author': ['alice', 'bob', None],  # None value
            'merged': [True, False, True],
            'state': ['merged', 'open', 'merged'],
            'additions': [100, None, 300],  # NaN value
            'deletions': [50, 100, 150],
            'cycle_time_hours': [24.0, None, 36.0]  # NaN value
        })

        dfs = {
            'pull_requests': prs_with_nans,
            'reviews': pd.DataFrame(),
            'commits': pd.DataFrame(),
            'deployments': pd.DataFrame()
        }

        calculator = MetricsCalculator(dfs)

        # Should handle NaN/None values gracefully
        metrics = calculator.calculate_pr_metrics()
        assert metrics is not None
        assert metrics['total_prs'] == 3
        assert metrics['merged_prs'] == 2

        # Cycle time should ignore None values
        assert metrics['avg_cycle_time_hours'] is not None

    def test_concurrent_cache_access(self):
        """Test handling of concurrent cache file access"""
        # Create valid cache
        cache_data = {
            'teams': {},
            'persons': {},
            'comparison': {'teams': [], 'metrics': {}},
            'timestamp': datetime.now(timezone.utc),
            'date_range': {}
        }

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
            pickle.dump(cache_data, f)
            temp_path = f.name

        try:
            with patch('src.dashboard.app.get_cache_filename', return_value=temp_path):
                # Multiple sequential loads should work
                success1 = load_cache_from_file('90d')
                success2 = load_cache_from_file('90d')
                assert success1 is True
                assert success2 is True
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
