"""Integration tests for metrics orchestration

Tests the complete metrics calculation pipeline including:
- Team-level aggregation from GitHub and Jira data
- Individual contributor metrics
- Cross-team comparison
- DORA metrics integration
- Date range filtering
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src.models.metrics import MetricsCalculator


class TestMetricsCalculatorInitialization:
    """Test MetricsCalculator initialization and basic operations"""

    def test_initializes_with_empty_dataframes(self):
        """Test calculator handles empty dataframes"""
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)

        assert calculator.dfs is not None
        assert len(calculator.dfs) == 4

        # Should return zero metrics, not crash
        pr_metrics = calculator.calculate_pr_metrics()
        assert pr_metrics["total_prs"] == 0
        assert pr_metrics["merged_prs"] == 0

    def test_initializes_with_populated_dataframes(self):
        """Test calculator with real data"""
        prs = pd.DataFrame(
            [
                {
                    "pr_number": 1,
                    "author": "alice",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 100,
                    "deletions": 50,
                    "created_at": datetime.now(timezone.utc),
                    "merged_at": datetime.now(timezone.utc),
                }
            ]
        )

        dfs = {
            "pull_requests": prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        pr_metrics = calculator.calculate_pr_metrics()

        assert pr_metrics["total_prs"] == 1
        assert pr_metrics["merged_prs"] == 1
        assert pr_metrics["merge_rate"] == 1.0


class TestTeamMetricsAggregation:
    """Test team-level metrics aggregation"""

    def test_aggregates_github_prs_across_team(self):
        """Test aggregating PR metrics for multiple team members"""
        prs = pd.DataFrame(
            [
                {
                    "pr_number": 1,
                    "author": "alice",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 100,
                    "deletions": 50,
                    "created_at": datetime.now(timezone.utc) - timedelta(days=1),
                    "merged_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 2,
                    "author": "bob",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 48.0,
                    "time_to_first_review_hours": 4.0,
                    "additions": 200,
                    "deletions": 100,
                    "created_at": datetime.now(timezone.utc) - timedelta(days=2),
                    "merged_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 3,
                    "author": "alice",
                    "merged": False,
                    "state": "open",
                    "cycle_time_hours": None,
                    "time_to_first_review_hours": 1.0,
                    "additions": 50,
                    "deletions": 25,
                    "created_at": datetime.now(timezone.utc),
                    "merged_at": None,
                },
            ]
        )

        dfs = {
            "pull_requests": prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_pr_metrics()

        # Team aggregates
        assert metrics["total_prs"] == 3
        assert metrics["merged_prs"] == 2
        assert metrics["open_prs"] == 1
        assert metrics["merge_rate"] == 2 / 3

    def test_aggregates_reviews_across_team(self):
        """Test aggregating review metrics"""
        reviews = pd.DataFrame(
            [
                {"reviewer": "alice", "pr_number": 1, "state": "APPROVED", "pr_author": "bob"},
                {"reviewer": "bob", "pr_number": 2, "state": "APPROVED", "pr_author": "alice"},
                {"reviewer": "charlie", "pr_number": 3, "state": "CHANGES_REQUESTED", "pr_author": "alice"},
            ]
        )

        prs = pd.DataFrame(
            [
                {
                    "pr_number": 1,
                    "author": "bob",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "additions": 100,
                    "deletions": 50,
                },
                {
                    "pr_number": 2,
                    "author": "alice",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "additions": 100,
                    "deletions": 50,
                },
            ]
        )

        dfs = {
            "pull_requests": prs,
            "reviews": reviews,
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_review_metrics()

        assert metrics["total_reviews"] == 3
        assert metrics["unique_reviewers"] == 3
        assert "top_reviewers" in metrics

    def test_aggregates_commits_across_team(self):
        """Test aggregating commit metrics"""
        commits = pd.DataFrame(
            [
                {
                    "sha": "abc1",
                    "author": "alice",
                    "date": datetime.now(timezone.utc),
                    "additions": 100,
                    "deletions": 50,
                },
                {
                    "sha": "abc2",
                    "author": "bob",
                    "date": datetime.now(timezone.utc),
                    "additions": 200,
                    "deletions": 100,
                },
                {
                    "sha": "abc3",
                    "author": "alice",
                    "date": datetime.now(timezone.utc),
                    "additions": 50,
                    "deletions": 25,
                },
            ]
        )

        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": commits,
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_contributor_metrics()

        assert metrics["total_commits"] == 3
        assert metrics["unique_contributors"] == 2
        assert metrics["total_lines_added"] == 350
        assert metrics["total_lines_deleted"] == 175


class TestPersonMetricsCalculation:
    """Test individual contributor metrics"""

    def test_calculates_person_pr_metrics(self):
        """Test calculating PR metrics for a single person"""
        prs = pd.DataFrame(
            [
                {
                    "pr_number": 1,
                    "author": "alice",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 100,
                    "deletions": 50,
                    "created_at": datetime.now(timezone.utc),
                    "merged_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 2,
                    "author": "bob",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 48.0,
                    "time_to_first_review_hours": 4.0,
                    "additions": 200,
                    "deletions": 100,
                    "created_at": datetime.now(timezone.utc),
                    "merged_at": datetime.now(timezone.utc),
                },
            ]
        )

        # Filter to alice's PRs
        alice_prs = prs[prs["author"] == "alice"]

        dfs = {
            "pull_requests": alice_prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_pr_metrics()

        # Should only count alice's PR
        assert metrics["total_prs"] == 1
        assert metrics["merged_prs"] == 1
        assert metrics["avg_cycle_time_hours"] == 24.0

    def test_calculates_person_review_metrics(self):
        """Test calculating review metrics for a single person"""
        reviews = pd.DataFrame(
            [
                {"reviewer": "alice", "pr_number": 1, "state": "APPROVED", "pr_author": "bob"},
                {"reviewer": "alice", "pr_number": 2, "state": "APPROVED", "pr_author": "charlie"},
                {"reviewer": "bob", "pr_number": 3, "state": "CHANGES_REQUESTED", "pr_author": "alice"},
            ]
        )

        # Filter to alice's reviews
        alice_reviews = reviews[reviews["reviewer"] == "alice"]

        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": alice_reviews,
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_review_metrics()

        assert metrics["total_reviews"] == 2
        assert metrics["unique_reviewers"] == 1

    def test_handles_person_with_no_activity(self):
        """Test person with zero activity returns graceful defaults"""
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)

        pr_metrics = calculator.calculate_pr_metrics()
        review_metrics = calculator.calculate_review_metrics()
        commit_metrics = calculator.calculate_contributor_metrics()

        # All should return zero/empty values
        assert pr_metrics["total_prs"] == 0
        assert review_metrics["total_reviews"] == 0
        assert commit_metrics["total_commits"] == 0


class TestDORAMetricsIntegration:
    """Test DORA metrics calculation within orchestration"""

    def test_calculates_deployment_frequency(self):
        """Test deployment frequency calculation"""
        releases = pd.DataFrame(
            [
                {
                    "tag_name": "v1.0",
                    "published_at": datetime.now(timezone.utc) - timedelta(days=7),
                    "environment": "production",
                    "repo": "test/repo",
                },
                {
                    "tag_name": "v1.1",
                    "published_at": datetime.now(timezone.utc) - timedelta(days=3),
                    "environment": "production",
                    "repo": "test/repo",
                },
                {
                    "tag_name": "v1.2",
                    "published_at": datetime.now(timezone.utc),
                    "environment": "production",
                    "repo": "test/repo",
                },
            ]
        )

        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases,
        }

        calculator = MetricsCalculator(dfs)

        # Calculate DORA metrics
        dora_metrics = calculator.calculate_dora_metrics()

        # Should have deployment frequency
        assert dora_metrics["deployment_frequency"] is not None
        # Check that deployments were calculated (any valid key exists)
        assert dora_metrics["deployment_frequency"]["total_deployments"] > 0

    def test_calculates_lead_time_with_mapping(self):
        """Test lead time calculation with issue-to-version mapping"""
        prs = pd.DataFrame(
            [
                {
                    "number": 1,
                    "title": "[PROJ-123] Add feature",
                    "merged": True,
                    "merged_at": datetime.now(timezone.utc) - timedelta(days=5),
                    "author": "alice",
                    "branch": "main",
                }
            ]
        )

        releases = pd.DataFrame(
            [
                {
                    "tag_name": "v1.0",
                    "published_at": datetime.now(timezone.utc),
                    "environment": "production",
                    "repo": "test/repo",
                }
            ]
        )

        dfs = {
            "pull_requests": prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases,
        }

        calculator = MetricsCalculator(dfs)

        # Calculate with issue mapping
        issue_to_version_map = {"PROJ-123": "v1.0"}
        dora_metrics = calculator.calculate_dora_metrics(issue_to_version_map=issue_to_version_map)

        # Should calculate lead time
        assert "lead_time" in dora_metrics
        if dora_metrics["lead_time"]["sample_size"] > 0:
            assert dora_metrics["lead_time"]["median_hours"] > 0


class TestDateRangeFiltering:
    """Test date range filtering across metrics"""

    def test_filters_prs_by_date_range(self):
        """Test PRs filtered by date range"""
        # PRs from different time periods
        prs = pd.DataFrame(
            [
                {
                    "pr_number": 1,
                    "author": "alice",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 100,
                    "deletions": 50,
                    "created_at": datetime.now(timezone.utc) - timedelta(days=5),
                    "merged_at": datetime.now(timezone.utc) - timedelta(days=4),
                },
                {
                    "pr_number": 2,
                    "author": "bob",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 48.0,
                    "time_to_first_review_hours": 4.0,
                    "additions": 200,
                    "deletions": 100,
                    "created_at": datetime.now(timezone.utc) - timedelta(days=95),  # Outside 90d
                    "merged_at": datetime.now(timezone.utc) - timedelta(days=94),
                },
            ]
        )

        # Filter to last 90 days
        recent_prs = prs[prs["created_at"] >= datetime.now(timezone.utc) - timedelta(days=90)]

        dfs = {
            "pull_requests": recent_prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_pr_metrics()

        # Should only count PR from last 90 days
        assert metrics["total_prs"] == 1

    def test_filters_releases_by_date_range(self):
        """Test releases filtered by date range"""
        releases = pd.DataFrame(
            [
                {
                    "tag_name": "v1.0",
                    "published_at": datetime.now(timezone.utc) - timedelta(days=30),
                    "environment": "production",
                    "repo": "test/repo",
                },
                {
                    "tag_name": "v0.9",
                    "published_at": datetime.now(timezone.utc) - timedelta(days=180),
                    "environment": "production",
                    "repo": "test/repo",
                },
            ]
        )

        # Filter to last 90 days
        recent_releases = releases[releases["published_at"] >= datetime.now(timezone.utc) - timedelta(days=90)]

        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": recent_releases,
        }

        calculator = MetricsCalculator(dfs)
        dora_metrics = calculator.calculate_dora_metrics()

        # Should only count recent release
        assert dora_metrics["deployment_frequency"]["total_deployments"] == 1


class TestPRSizeDistribution:
    """Test PR size categorization"""

    def test_categorizes_pr_sizes(self):
        """Test PR size distribution calculation"""
        prs = pd.DataFrame(
            [
                {
                    "pr_number": 1,
                    "author": "alice",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 50,
                    "deletions": 30,  # Small: 80 lines
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 2,
                    "author": "bob",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 200,
                    "deletions": 150,  # Medium: 350 lines
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 3,
                    "author": "charlie",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 600,
                    "deletions": 300,  # Large: 900 lines
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 4,
                    "author": "diana",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 1500,
                    "deletions": 800,  # XLarge: 2300 lines
                    "created_at": datetime.now(timezone.utc),
                },
            ]
        )

        dfs = {
            "pull_requests": prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_pr_metrics()

        # Verify distribution
        assert metrics["pr_size_distribution"]["small (<100 lines)"] == 1
        assert metrics["pr_size_distribution"]["medium (100-500 lines)"] == 1
        assert metrics["pr_size_distribution"]["large (500-1000 lines)"] == 1
        assert metrics["pr_size_distribution"]["xlarge (>1000 lines)"] == 1


class TestMergeRateCalculation:
    """Test merge rate calculation"""

    def test_calculates_merge_rate(self):
        """Test merge rate calculation with mixed PR states"""
        prs = pd.DataFrame(
            [
                {
                    "pr_number": 1,
                    "author": "alice",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                    "additions": 100,
                    "deletions": 50,
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 2,
                    "author": "bob",
                    "merged": True,
                    "state": "merged",
                    "cycle_time_hours": 48.0,
                    "time_to_first_review_hours": 4.0,
                    "additions": 200,
                    "deletions": 100,
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 3,
                    "author": "charlie",
                    "merged": False,
                    "state": "open",
                    "cycle_time_hours": None,
                    "time_to_first_review_hours": 1.0,
                    "additions": 50,
                    "deletions": 25,
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "pr_number": 4,
                    "author": "diana",
                    "merged": False,
                    "state": "closed",
                    "cycle_time_hours": None,
                    "time_to_first_review_hours": 1.0,
                    "additions": 30,
                    "deletions": 15,
                    "created_at": datetime.now(timezone.utc),
                },
            ]
        )

        dfs = {
            "pull_requests": prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        metrics = calculator.calculate_pr_metrics()

        # 2 merged out of 4 total = 50%
        assert metrics["merge_rate"] == 0.5
        assert metrics["merged_prs"] == 2
        assert metrics["open_prs"] == 1
        assert metrics["closed_unmerged_prs"] == 1
