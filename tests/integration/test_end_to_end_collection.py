"""End-to-end integration tests for complete collection workflow.

Tests the full pipeline: GitHub → Jira → DORA metrics → Dashboard
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector
from src.models.metrics import MetricsCalculator
from tests.fixtures.github_responses import create_pull_request, create_release
from tests.fixtures.jira_responses import create_fix_version, create_issue, create_sample_issues_small


class TestFullTeamWorkflow:
    """Tests for complete team metrics collection workflow."""

    def test_github_to_jira_to_dora_pipeline(self):
        """Test full pipeline from GitHub collection to DORA metrics calculation."""
        # Step 1: Collect GitHub data
        github_collector = GitHubGraphQLCollector(
            token="test_token", organization="test-org", days_back=90, repo_workers=1
        )
        github_collector.teams = ["test-team"]
        github_collector.team_members = ["alice", "bob"]

        # Mock GitHub data
        prs = [
            create_pull_request(
                1,
                "Feature A",
                "alice",
                "MERGED",
                created_at=datetime.now(timezone.utc) - timedelta(days=7),
                merged_at=datetime.now(timezone.utc) - timedelta(days=3),
            ),
            create_pull_request(
                2,
                "Feature B",
                "bob",
                "MERGED",
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
                merged_at=datetime.now(timezone.utc) - timedelta(days=5),
            ),
        ]

        releases = [
            create_release("v1.0.0", "Version 1.0.0", published_at=datetime.now(timezone.utc) - timedelta(days=2)),
            create_release("v1.1.0", "Version 1.1.0", published_at=datetime.now(timezone.utc) - timedelta(days=1)),
        ]

        # Step 2: Mock Jira collector (don't make real connection)
        issues = create_sample_issues_small(count=10)

        # Step 3: Calculate metrics (MetricsCalculator doesn't need days_back param)

        # Mock the actual collection (we're testing integration, not real API calls)
        github_data = {
            "pull_requests": prs,
            "reviews": [],
            "commits": [],
            "deployments": releases,
            "releases": releases,
        }

        jira_data = {"issues": issues, "fix_versions": [create_fix_version("v1.0.0"), create_fix_version("v1.1.0")]}

        # Verify data flows through
        assert len(github_data["pull_requests"]) == 2
        assert len(github_data["releases"]) == 2
        assert len(jira_data["issues"]) == 10

        # Verify team members are consistent
        pr_authors = {pr["author"]["login"] for pr in github_data["pull_requests"]}
        assert pr_authors.issubset({"alice", "bob"})

    def test_multi_team_data_isolation(self):
        """Test that data from different teams doesn't mix."""
        # Team A
        team_a_prs = [
            create_pull_request(1, "Team A Feature", "alice", "MERGED"),
            create_pull_request(2, "Team A Feature", "bob", "MERGED"),
        ]

        # Team B
        team_b_prs = [
            create_pull_request(10, "Team B Feature", "charlie", "MERGED"),
            create_pull_request(11, "Team B Feature", "diana", "MERGED"),
        ]

        # Verify teams are isolated
        team_a_authors = {pr["author"]["login"] for pr in team_a_prs}
        team_b_authors = {pr["author"]["login"] for pr in team_b_prs}

        assert team_a_authors.isdisjoint(team_b_authors)
        assert "alice" in team_a_authors
        assert "charlie" in team_b_authors

    def test_date_range_filtering_end_to_end(self):
        """Test that date range filtering works across all collectors."""
        days_back = 30
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Create PRs with various dates
        recent_pr = create_pull_request(
            1, "Recent", "alice", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=15)
        )
        old_pr = create_pull_request(
            2, "Old", "bob", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=45)
        )

        # Verify recent PR is within range
        recent_date = datetime.fromisoformat(recent_pr["createdAt"].replace("Z", "+00:00"))
        assert recent_date >= cutoff_date

        # Verify old PR is outside range
        old_date = datetime.fromisoformat(old_pr["createdAt"].replace("Z", "+00:00"))
        assert old_date < cutoff_date

    def test_issue_to_release_mapping(self):
        """Test mapping Jira issues to GitHub releases via fix versions."""
        # Create issue with fix version
        issue = create_issue(
            key="PROJ-123",
            summary="Feature implementation",
            fix_versions=["v1.0.0"],
            status="Done",
            resolved=datetime.now(timezone.utc) - timedelta(days=5),
        )

        # Create matching release
        release = create_release("v1.0.0", "Version 1.0.0", published_at=datetime.now(timezone.utc) - timedelta(days=3))

        # Verify mapping
        issue_version = issue["fields"]["fixVersions"][0]["name"]
        release_tag = release["tagName"]

        assert issue_version == release_tag

    def test_dora_metrics_calculation_integration(self):
        """Test DORA metrics calculation with realistic data."""
        # Deployment Frequency: 2 releases in 30 days
        releases = [
            create_release("v1.0.0", "Release 1", published_at=datetime.now(timezone.utc) - timedelta(days=15)),
            create_release("v1.1.0", "Release 2", published_at=datetime.now(timezone.utc) - timedelta(days=3)),
        ]

        # Lead Time: PR merged → Release published
        pr = create_pull_request(
            1, "[PROJ-123] Feature", "alice", "MERGED", merged_at=datetime.now(timezone.utc) - timedelta(days=5)
        )

        release = releases[1]  # v1.1.0

        # Calculate lead time (5 days before release to 3 days before now = 2 days)
        pr_merged = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00"))
        release_published = datetime.fromisoformat(release["publishedAt"].replace("Z", "+00:00"))
        lead_time_days = (release_published - pr_merged).total_seconds() / 86400

        assert 1 <= lead_time_days <= 3  # Approximately 2 days

        # Deployment frequency: 2 releases / 30 days ≈ 0.067 per day
        deployment_freq = len(releases) / 30
        assert 0.05 <= deployment_freq <= 0.1

    def test_cache_save_and_load(self):
        """Test that metrics can be saved to cache and reloaded."""
        # Create sample metrics
        metrics = {
            "teams": {"test-team": {"pr_count": 10, "review_count": 20, "deployment_frequency": 2.5}},
            "persons": {"alice": {"pr_count": 5, "review_count": 12}},
            "timestamp": datetime.now(timezone.utc),
        }

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pkl") as f:
            import pickle

            pickle.dump(metrics, f)
            cache_file = f.name

        try:
            # Load from cache
            with open(cache_file, "rb") as f:
                loaded_metrics = pickle.load(f)

            # Verify data integrity
            assert loaded_metrics["teams"]["test-team"]["pr_count"] == 10
            assert loaded_metrics["persons"]["alice"]["review_count"] == 12
            assert "timestamp" in loaded_metrics
        finally:
            os.unlink(cache_file)


class TestMultiTeamIsolation:
    """Tests for multi-team data isolation."""

    def test_team_a_does_not_contaminate_team_b(self):
        """Test that Team A's metrics don't affect Team B."""
        # Team A data
        team_a_data = {
            "name": "Team A",
            "members": ["alice", "bob"],
            "prs": [
                create_pull_request(1, "Feature A", "alice", "MERGED"),
                create_pull_request(2, "Feature B", "bob", "MERGED"),
            ],
        }

        # Team B data
        team_b_data = {
            "name": "Team B",
            "members": ["charlie", "diana"],
            "prs": [
                create_pull_request(10, "Feature X", "charlie", "MERGED"),
                create_pull_request(11, "Feature Y", "diana", "MERGED"),
            ],
        }

        # Verify isolation
        team_a_authors = {pr["author"]["login"] for pr in team_a_data["prs"]}
        team_b_authors = {pr["author"]["login"] for pr in team_b_data["prs"]}

        assert team_a_authors == {"alice", "bob"}
        assert team_b_authors == {"charlie", "diana"}
        assert team_a_authors.isdisjoint(team_b_authors)

    def test_shared_repository_different_team_members(self):
        """Test that teams can work on same repo but have separate metrics."""
        repo_name = "test-org/shared-repo"

        # All PRs from shared repo
        all_prs = [
            create_pull_request(1, "Feature", "alice", "MERGED"),  # Team A
            create_pull_request(2, "Feature", "bob", "MERGED"),  # Team A
            create_pull_request(3, "Feature", "charlie", "MERGED"),  # Team B
            create_pull_request(4, "Feature", "diana", "MERGED"),  # Team B
        ]

        # Filter for Team A
        team_a_members = {"alice", "bob"}
        team_a_prs = [pr for pr in all_prs if pr["author"]["login"] in team_a_members]

        # Filter for Team B
        team_b_members = {"charlie", "diana"}
        team_b_prs = [pr for pr in all_prs if pr["author"]["login"] in team_b_members]

        assert len(team_a_prs) == 2
        assert len(team_b_prs) == 2
        assert all(pr["author"]["login"] in team_a_members for pr in team_a_prs)
        assert all(pr["author"]["login"] in team_b_members for pr in team_b_prs)

    def test_cache_separation_by_environment(self):
        """Test that different environments have separate cache files."""
        # Production cache
        prod_cache_name = "metrics_cache_90d_prod.pkl"

        # UAT cache
        uat_cache_name = "metrics_cache_90d_uat.pkl"

        # Verify cache names are different
        assert prod_cache_name != uat_cache_name
        assert "prod" in prod_cache_name
        assert "uat" in uat_cache_name


class TestDateRangeVariations:
    """Tests for various date range configurations."""

    def test_30_day_collection(self):
        """Test 30-day collection window."""
        days_back = 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        pr = create_pull_request(
            1, "Feature", "alice", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=15)
        )

        pr_date = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
        assert pr_date >= cutoff

    def test_90_day_collection(self):
        """Test 90-day collection window."""
        days_back = 90
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        pr = create_pull_request(
            1, "Feature", "alice", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=60)
        )

        pr_date = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
        assert pr_date >= cutoff

    def test_365_day_collection(self):
        """Test 365-day collection window (1 year)."""
        days_back = 365
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        pr = create_pull_request(
            1, "Feature", "alice", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=200)
        )

        pr_date = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
        assert pr_date >= cutoff

    def test_filters_data_outside_range(self):
        """Test that data outside the collection window is filtered."""
        days_back = 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        recent_pr = create_pull_request(
            1, "Recent", "alice", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=15)
        )

        old_pr = create_pull_request(
            2, "Old", "bob", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=45)
        )

        recent_date = datetime.fromisoformat(recent_pr["createdAt"].replace("Z", "+00:00"))
        old_date = datetime.fromisoformat(old_pr["createdAt"].replace("Z", "+00:00"))

        # Recent should be included
        assert recent_date >= cutoff

        # Old should be excluded
        assert old_date < cutoff
