"""
Simplified tests for GitHub GraphQL collector

Tests cover only the methods that are testable without complex HTTP mocking:
- Date range filtering
- Release classification
- Data extraction methods
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from src.collectors.github_graphql_collector import GitHubGraphQLCollector


class TestDateRangeFiltering:
    """Tests for date range filtering methods"""

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_pr_in_date_range(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token", days_back=30)

        # PR created 15 days ago
        recent_date = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        pr = {"createdAt": recent_date, "mergedAt": None, "closedAt": None}

        # Act
        result = collector._is_pr_in_date_range(pr)

        # Assert
        assert result is True

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_pr_outside_date_range(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token", days_back=30)

        # PR created 60 days ago (outside range)
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        pr = {"createdAt": old_date, "mergedAt": None, "closedAt": None}

        # Act
        result = collector._is_pr_in_date_range(pr)

        # Assert
        assert result is False

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_release_in_date_range(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token", days_back=30)

        # Release published 15 days ago
        recent_date = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        release = {"publishedAt": recent_date}

        # Act
        result = collector._is_release_in_date_range(release)

        # Assert
        assert result is True

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_release_outside_date_range(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token", days_back=30)

        # Release published 60 days ago
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        release = {"publishedAt": old_date}

        # Act
        result = collector._is_release_in_date_range(release)

        # Assert
        assert result is False


class TestReleaseClassification:
    """Tests for _classify_release_environment method"""

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_classifies_production_release(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        # Act & Assert - Only semantic versions without suffix are production
        assert collector._classify_release_environment("v1.0.0", is_prerelease=False) == "production"
        assert collector._classify_release_environment("1.2.3", is_prerelease=False) == "production"
        assert collector._classify_release_environment("v10.20.30", is_prerelease=False) == "production"
        # Non-semantic version tags default to staging
        assert collector._classify_release_environment("release-2024-01-15", is_prerelease=False) == "staging"

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_classifies_staging_release(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        # Act & Assert
        assert collector._classify_release_environment("v1.0.0-rc.1", is_prerelease=True) == "staging"
        assert collector._classify_release_environment("v1.0.0-beta", is_prerelease=True) == "staging"
        assert collector._classify_release_environment("v1.0.0-alpha.3", is_prerelease=True) == "staging"
        assert collector._classify_release_environment("staging-2024-01-15", is_prerelease=False) == "staging"
        assert collector._classify_release_environment("test-release", is_prerelease=False) == "staging"

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_prerelease_flag_overrides_tag_name(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        # Act & Assert - Even without staging keywords, prerelease=True means staging
        assert collector._classify_release_environment("v1.0.0", is_prerelease=True) == "staging"


class TestPRDataExtraction:
    """Tests for _extract_pr_data method"""

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_calculates_cycle_time_for_merged_pr(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        # PR created and merged 24 hours later
        pr = {
            "number": 123,
            "title": "Test PR",
            "author": {"login": "alice"},
            "createdAt": "2024-01-01T10:00:00Z",
            "mergedAt": "2024-01-02T10:00:00Z",  # 24 hours later
            "closedAt": "2024-01-02T10:00:00Z",
            "state": "MERGED",
            "merged": True,
            "additions": 100,
            "deletions": 50,
            "changedFiles": 3,
            "baseRefName": "main",
            "headRefName": "feature-branch",
        }

        # Act
        result = collector._extract_pr_data(pr)

        # Assert
        assert result["cycle_time_hours"] == 24.0

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_open_pr_has_none_cycle_time(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        pr = {
            "number": 123,
            "title": "Open PR",
            "author": {"login": "bob"},
            "createdAt": "2024-01-01T10:00:00Z",
            "mergedAt": None,
            "closedAt": None,
            "state": "OPEN",
            "merged": False,
            "additions": 100,
            "deletions": 50,
            "changedFiles": 3,
            "baseRefName": "main",
            "headRefName": "feature-branch",
        }

        # Act
        result = collector._extract_pr_data(pr)

        # Assert
        assert result["cycle_time_hours"] is None
        assert result["merged"] is False


class TestReviewDataExtraction:
    """Tests for _extract_review_data method"""

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_extracts_multiple_reviews(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        pr = {
            "number": 123,
            "author": {"login": "alice"},
            "reviews": {
                "nodes": [
                    {
                        "author": {"login": "bob"},
                        "state": "APPROVED",
                        "submittedAt": "2024-01-01T12:00:00Z",
                    },
                    {
                        "author": {"login": "charlie"},
                        "state": "CHANGES_REQUESTED",
                        "submittedAt": "2024-01-01T14:00:00Z",
                    },
                ]
            },
        }

        # Act
        result = collector._extract_review_data(pr)

        # Assert
        assert len(result) == 2
        assert result[0]["reviewer"] == "bob"
        assert result[0]["state"] == "APPROVED"
        assert result[1]["reviewer"] == "charlie"
        assert result[1]["state"] == "CHANGES_REQUESTED"

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_handles_empty_reviews(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        pr = {
            "number": 123,
            "author": {"login": "alice"},
            "reviews": {"nodes": []},
        }

        # Act
        result = collector._extract_review_data(pr)

        # Assert
        assert result == []


class TestCommitDataExtraction:
    """Tests for _extract_commit_data method"""

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_extracts_commit_data(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        pr = {
            "number": 123,
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "oid": "abc123",
                            "committedDate": "2024-01-01T10:00:00Z",
                            "additions": 100,
                            "deletions": 50,
                            "author": {
                                "user": {"login": "alice"},
                                "name": "Alice Developer",
                                "email": "alice@example.com",
                            },
                        }
                    },
                    {
                        "commit": {
                            "oid": "def456",
                            "committedDate": "2024-01-01T11:00:00Z",
                            "additions": 50,
                            "deletions": 25,
                            "author": {
                                "user": {"login": "bob"},
                                "name": "Bob Developer",
                                "email": "bob@example.com",
                            },
                        }
                    },
                ]
            },
        }

        # Act
        result = collector._extract_commit_data(pr)

        # Assert
        assert len(result) == 2
        assert result[0]["sha"] == "abc123"
        assert result[0]["author"] == "alice"
        assert result[0]["additions"] == 100
        assert result[0]["deletions"] == 50
        assert result[1]["sha"] == "def456"
        assert result[1]["author"] == "bob"

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_handles_commits_without_user(self, mock_session_class):
        # Arrange - Some commits don't have associated GitHub user
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token")

        pr = {
            "number": 123,
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "oid": "abc123",
                            "committedDate": "2024-01-01T10:00:00Z",
                            "additions": 100,
                            "deletions": 50,
                            "author": {
                                "user": None,  # No GitHub user
                                "name": "External Contributor",
                                "email": "external@example.com",
                            },
                        }
                    },
                ]
            },
        }

        # Act
        result = collector._extract_commit_data(pr)

        # Assert - Falls back to email when user is None
        assert len(result) == 1
        assert result[0]["author"] == "external@example.com"


class TestTeamMemberFiltering:
    """Tests for _filter_by_team_members method"""

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_filters_prs_by_author(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token", team_members=["alice", "bob"])

        data = {
            "pull_requests": [
                {"number": 1, "author": "alice"},
                {"number": 2, "author": "charlie"},  # Not in team
                {"number": 3, "author": "bob"},
            ],
            "reviews": [],
            "commits": [],
            "deployments": [],
            "releases": [],
        }

        # Act
        result = collector._filter_by_team_members(data)

        # Assert
        assert len(result["pull_requests"]) == 2
        assert result["pull_requests"][0]["author"] == "alice"
        assert result["pull_requests"][1]["author"] == "bob"

    @patch("src.collectors.github_graphql_collector.requests.Session")
    def test_filters_reviews_by_reviewer(self, mock_session_class):
        # Arrange
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        collector = GitHubGraphQLCollector(token="test-token", team_members=["alice", "bob"])

        data = {
            "pull_requests": [],
            "reviews": [
                {"reviewer": "alice", "state": "APPROVED"},
                {"reviewer": "charlie", "state": "APPROVED"},  # Not in team
                {"reviewer": "bob", "state": "CHANGES_REQUESTED"},
            ],
            "commits": [],
            "deployments": [],
            "releases": [],
        }

        # Act
        result = collector._filter_by_team_members(data)

        # Assert
        assert len(result["reviews"]) == 2
        assert result["reviews"][0]["reviewer"] == "alice"
        assert result["reviews"][1]["reviewer"] == "bob"
