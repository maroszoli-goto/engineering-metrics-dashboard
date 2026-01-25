"""Tests for data filtering utilities"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from src.dashboard.utils.data_filtering import filter_github_data_by_date, filter_jira_data_by_date


class TestFilterGithubDataByDate:
    """Test filter_github_data_by_date function"""

    def test_filters_prs_by_created_at(self):
        """Should filter PRs by created_at date"""
        raw_data = {
            "pull_requests": [
                {"id": 1, "created_at": "2025-01-15T10:00:00Z"},
                {"id": 2, "created_at": "2024-12-15T10:00:00Z"},  # Outside range
                {"id": 3, "created_at": "2025-01-20T10:00:00Z"},
            ],
            "reviews": [],
            "commits": [],
        }

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        assert len(filtered["pull_requests"]) == 2
        assert filtered["pull_requests"][0]["id"] == 1
        assert filtered["pull_requests"][1]["id"] == 3

    def test_filters_reviews_by_submitted_at(self):
        """Should filter reviews by submitted_at date"""
        raw_data = {
            "pull_requests": [],
            "reviews": [
                {"id": 1, "submitted_at": "2025-01-15T10:00:00Z"},
                {"id": 2, "submitted_at": "2024-12-15T10:00:00Z"},  # Outside range
                {"id": 3, "submitted_at": "2025-01-20T10:00:00Z"},
            ],
            "commits": [],
        }

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        assert len(filtered["reviews"]) == 2

    def test_filters_commits_by_date_field(self):
        """Should filter commits by 'date' field"""
        raw_data = {
            "pull_requests": [],
            "reviews": [],
            "commits": [
                {"sha": "abc", "date": "2025-01-15T10:00:00Z"},
                {"sha": "def", "date": "2024-12-15T10:00:00Z"},  # Outside range
                {"sha": "ghi", "date": "2025-01-20T10:00:00Z"},
            ],
        }

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        assert len(filtered["commits"]) == 2

    def test_filters_commits_by_committed_date_field(self):
        """Should filter commits by 'committed_date' field as fallback"""
        raw_data = {
            "pull_requests": [],
            "reviews": [],
            "commits": [
                {"sha": "abc", "committed_date": "2025-01-15T10:00:00Z"},
                {"sha": "def", "committed_date": "2024-12-15T10:00:00Z"},  # Outside range
            ],
        }

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        assert len(filtered["commits"]) == 1

    def test_handles_empty_lists(self):
        """Should handle empty data lists"""
        raw_data = {"pull_requests": [], "reviews": [], "commits": []}

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        assert filtered["pull_requests"] == []
        assert filtered["reviews"] == []
        assert filtered["commits"] == []

    def test_handles_missing_keys(self):
        """Should handle missing keys in raw_data"""
        raw_data = {}

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        assert filtered["pull_requests"] == []
        assert filtered["reviews"] == []
        assert filtered["commits"] == []

    def test_handles_missing_date_columns(self):
        """Should return original data if date columns missing"""
        raw_data = {
            "pull_requests": [{"id": 1, "title": "PR without date"}],
            "reviews": [{"id": 1, "state": "approved"}],
            "commits": [{"sha": "abc", "message": "commit"}],
        }

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        # Should return original data when date columns missing
        assert len(filtered["pull_requests"]) == 1
        assert len(filtered["reviews"]) == 1
        assert len(filtered["commits"]) == 1

    def test_inclusive_date_range(self):
        """Should include items on boundary dates"""
        raw_data = {
            "pull_requests": [
                {"id": 1, "created_at": "2025-01-01T00:00:00Z"},  # Start boundary
                {"id": 2, "created_at": "2025-01-31T23:59:59Z"},  # End boundary
            ],
            "reviews": [],
            "commits": [],
        }

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

        filtered = filter_github_data_by_date(raw_data, start, end)

        assert len(filtered["pull_requests"]) == 2


class TestFilterJiraDataByDate:
    """Test filter_jira_data_by_date function"""

    def test_includes_issues_created_in_period(self):
        """Should include issues created within date range"""
        issues = [
            {"key": "ISSUE-1", "created": "2025-01-15T10:00:00Z", "resolved": None, "updated": "2025-01-15T10:00:00Z"},
            {"key": "ISSUE-2", "created": "2024-12-15T10:00:00Z", "resolved": None, "updated": "2024-12-15T10:00:00Z"},
        ]

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        assert len(filtered) == 1
        assert filtered[0]["key"] == "ISSUE-1"

    def test_includes_issues_resolved_in_period(self):
        """Should include issues resolved within date range"""
        issues = [
            {
                "key": "ISSUE-1",
                "created": "2024-12-01T10:00:00Z",  # Created before
                "resolved": "2025-01-15T10:00:00Z",  # Resolved in period
                "updated": "2025-01-15T10:00:00Z",
            },
            {
                "key": "ISSUE-2",
                "created": "2024-12-01T10:00:00Z",
                "resolved": "2024-12-15T10:00:00Z",  # Resolved before
                "updated": "2024-12-15T10:00:00Z",
            },
        ]

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        assert len(filtered) == 1
        assert filtered[0]["key"] == "ISSUE-1"

    def test_includes_issues_updated_in_period(self):
        """Should include WIP issues updated within date range"""
        issues = [
            {
                "key": "ISSUE-1",
                "created": "2024-12-01T10:00:00Z",  # Created before
                "resolved": None,  # Still in progress
                "updated": "2025-01-15T10:00:00Z",  # Updated in period
            },
            {
                "key": "ISSUE-2",
                "created": "2024-12-01T10:00:00Z",
                "resolved": None,
                "updated": "2024-12-15T10:00:00Z",  # Updated before
            },
        ]

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        assert len(filtered) == 1
        assert filtered[0]["key"] == "ISSUE-1"

    def test_includes_issue_if_any_condition_true(self):
        """Should include issue if ANY date field is in range"""
        issues = [
            {
                "key": "ISSUE-1",
                "created": "2024-12-01T10:00:00Z",  # Outside
                "resolved": "2025-01-15T10:00:00Z",  # Inside - should be included
                "updated": "2024-12-01T10:00:00Z",  # Outside
            }
        ]

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        assert len(filtered) == 1

    def test_handles_empty_list(self):
        """Should handle empty issues list"""
        issues = []

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        assert filtered == []

    def test_handles_missing_date_fields(self):
        """Should handle issues with missing date fields"""
        issues = [{"key": "ISSUE-1"}]  # No date fields

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        # Should return empty list when no date fields to filter on
        assert len(filtered) == 0

    def test_handles_none_resolved_date(self):
        """Should handle None/null resolved dates (WIP issues)"""
        issues = [
            {"key": "ISSUE-1", "created": "2025-01-15T10:00:00Z", "resolved": None, "updated": "2025-01-15T10:00:00Z"}
        ]

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        assert len(filtered) == 1

    def test_inclusive_date_range(self):
        """Should include issues on boundary dates"""
        issues = [
            {
                "key": "ISSUE-1",
                "created": "2025-01-01T00:00:00Z",  # Start boundary
                "resolved": None,
                "updated": "2025-01-01T00:00:00Z",
            },
            {
                "key": "ISSUE-2",
                "created": "2025-01-31T23:59:59Z",  # End boundary
                "resolved": None,
                "updated": "2025-01-31T23:59:59Z",
            },
        ]

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

        filtered = filter_jira_data_by_date(issues, start, end)

        assert len(filtered) == 2
