"""
Unit tests for metrics.py - MetricsCalculator class

Tests cover:
- PR metrics calculation (total, merged, merge rate, cycle time, size distribution)
- Review metrics calculation (total, unique reviewers, top reviewers)
- Contributor metrics calculation (commits, lines changed)
- Team metrics aggregation
- Person metrics with time windows
- Edge cases (empty dataframes, missing columns, None values)
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src.models.metrics import MetricsCalculator


class TestCalculatePRMetrics:
    """Tests for calculate_pr_metrics method"""

    def test_empty_dataframe_returns_zero_metrics(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        assert metrics["total_prs"] == 0
        assert metrics["merged_prs"] == 0
        assert metrics["open_prs"] == 0
        assert metrics["merge_rate"] == 0
        assert metrics["avg_pr_size"] == 0

    def test_calculates_total_and_merged_prs(self, sample_pr_dataframe):
        # Arrange
        dfs = {
            "pull_requests": sample_pr_dataframe,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        assert metrics["total_prs"] == 4
        assert metrics["merged_prs"] == 3  # 3 merged PRs
        assert metrics["open_prs"] == 1  # 1 open PR

    def test_calculates_merge_rate_correctly(self, sample_pr_dataframe):
        # Arrange
        dfs = {
            "pull_requests": sample_pr_dataframe,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        expected_merge_rate = 3 / 4  # 3 merged out of 4 total
        assert metrics["merge_rate"] == pytest.approx(expected_merge_rate, rel=0.01)

    def test_calculates_cycle_time_average_and_median(self, sample_pr_dataframe):
        # Arrange
        dfs = {
            "pull_requests": sample_pr_dataframe,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        # Cycle times: 24, 48, None, 36
        assert metrics["avg_cycle_time_hours"] == pytest.approx(36.0, rel=0.01)  # (24+48+36)/3
        assert metrics["median_cycle_time_hours"] == 36.0

    def test_calculates_pr_size_distribution(self, sample_pr_dataframe):
        # Arrange
        dfs = {
            "pull_requests": sample_pr_dataframe,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        distribution = metrics["pr_size_distribution"]
        assert "small (<100 lines)" in distribution
        assert "medium (100-500 lines)" in distribution
        assert "large (500-1000 lines)" in distribution
        assert "xlarge (>1000 lines)" in distribution

        # PR sizes: 150, 300, 75, 450
        assert distribution["small (<100 lines)"] == 1  # 75 lines
        assert distribution["medium (100-500 lines)"] == 3  # 150, 300, 450

    def test_calculates_average_pr_size(self, sample_pr_dataframe):
        # Arrange
        dfs = {
            "pull_requests": sample_pr_dataframe,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        # Sizes: 150, 300, 75, 450
        expected_avg = (150 + 300 + 75 + 450) / 4
        assert metrics["avg_pr_size"] == pytest.approx(expected_avg, rel=0.01)

    def test_calculates_time_to_first_review(self, sample_pr_dataframe):
        # Arrange
        dfs = {
            "pull_requests": sample_pr_dataframe,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        # Times: 2, 4, None, 3
        assert metrics["avg_time_to_first_review_hours"] == pytest.approx(3.0, rel=0.01)  # (2+4+3)/3

    def test_handles_all_open_prs(self):
        # Arrange - All PRs are open
        df = pd.DataFrame(
            {
                "pr_number": [1, 2, 3],
                "merged": [False, False, False],
                "state": ["open", "open", "open"],
                "additions": [100, 200, 300],
                "deletions": [50, 100, 150],
                "cycle_time_hours": [None, None, None],
                "time_to_first_review_hours": [None, None, None],
            }
        )
        dfs = {"pull_requests": df, "reviews": pd.DataFrame(), "commits": pd.DataFrame(), "deployments": pd.DataFrame()}
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        assert metrics["total_prs"] == 3
        assert metrics["merged_prs"] == 0
        assert metrics["open_prs"] == 3
        assert metrics["merge_rate"] == 0


class TestCalculateReviewMetrics:
    """Tests for calculate_review_metrics method"""

    def test_empty_reviews_returns_zero_metrics(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)

        # Act
        metrics = calculator.calculate_review_metrics()

        # Assert
        assert metrics["total_reviews"] == 0
        assert metrics["unique_reviewers"] == 0
        assert metrics["avg_reviews_per_pr"] == 0
        assert metrics["top_reviewers"] == {}

    def test_calculates_total_reviews(self, sample_reviews_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame({"pr_number": [1, 2, 3]}),
            "reviews": sample_reviews_dataframe,
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_review_metrics()

        # Assert
        assert metrics["total_reviews"] == 4

    def test_calculates_unique_reviewers(self, sample_reviews_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame({"pr_number": [1, 2, 3]}),
            "reviews": sample_reviews_dataframe,
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_review_metrics()

        # Assert
        # Reviewers: alice, bob, alice, charlie = 3 unique
        assert metrics["unique_reviewers"] == 3

    def test_calculates_top_reviewers(self, sample_reviews_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame({"pr_number": [1, 2, 3]}),
            "reviews": sample_reviews_dataframe,
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_review_metrics()

        # Assert
        top_reviewers = metrics["top_reviewers"]
        assert "alice" in top_reviewers
        assert "bob" in top_reviewers
        assert "charlie" in top_reviewers
        assert top_reviewers["alice"] == 2  # Alice reviewed twice

    def test_calculates_avg_reviews_per_pr(self, sample_reviews_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame({"pr_number": [1, 2, 3]}),
            "reviews": sample_reviews_dataframe,
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_review_metrics()

        # Assert
        # 4 reviews across 3 unique PRs
        expected_avg = 4 / 3
        assert metrics["avg_reviews_per_pr"] == pytest.approx(expected_avg, rel=0.01)


class TestCalculateContributorMetrics:
    """Tests for calculate_contributor_metrics method"""

    def test_empty_commits_returns_zero_metrics(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)

        # Act
        metrics = calculator.calculate_contributor_metrics()

        # Assert
        assert metrics["total_commits"] == 0
        assert metrics["unique_contributors"] == 0
        assert metrics["total_lines_added"] == 0
        assert metrics["total_lines_deleted"] == 0

    def test_calculates_total_commits(self, sample_commits_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": sample_commits_dataframe,
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_contributor_metrics()

        # Assert
        assert metrics["total_commits"] == 4

    def test_calculates_unique_contributors(self, sample_commits_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": sample_commits_dataframe,
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_contributor_metrics()

        # Assert
        # Authors: alice, bob, alice, charlie = 3 unique
        assert metrics["unique_contributors"] == 3

    def test_calculates_lines_added_and_deleted(self, sample_commits_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": sample_commits_dataframe,
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_contributor_metrics()

        # Assert
        # Additions: 100, 200, 50, 300 = 650
        # Deletions: 50, 100, 25, 150 = 325
        assert metrics["total_lines_added"] == 650
        assert metrics["total_lines_deleted"] == 325

    def test_calculates_top_contributors(self, sample_commits_dataframe):
        # Arrange
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": sample_commits_dataframe,
            "deployments": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_contributor_metrics()

        # Assert
        top_contributors = metrics["top_contributors"]
        assert "alice" in top_contributors
        assert "bob" in top_contributors
        assert "charlie" in top_contributors
        assert top_contributors["alice"]["sha"] == 2  # Alice has 2 commits
        assert top_contributors["alice"]["additions"] == 150  # 100 + 50
        assert top_contributors["alice"]["deletions"] == 75  # 50 + 25


class TestTeamMetrics:
    """Tests for team-level metrics aggregation"""

    def test_calculate_team_metrics_aggregates_individual_stats(self):
        # Arrange
        prs_df = pd.DataFrame(
            {
                "pr_number": [1, 2, 3, 4],
                "author": ["alice", "bob", "alice", "charlie"],
                "merged": [True, True, False, True],
                "state": ["merged", "merged", "open", "merged"],
                "additions": [100, 200, 50, 300],
                "deletions": [50, 100, 25, 150],
                "cycle_time_hours": [24.0, 48.0, None, 36.0],
                "time_to_first_review_hours": [2.0, 4.0, None, 3.0],
            }
        )

        reviews_df = pd.DataFrame(
            {
                "reviewer": ["alice", "bob", "alice", "charlie"],
                "pr_number": [1, 1, 2, 3],
                "state": ["APPROVED", "APPROVED", "CHANGES_REQUESTED", "APPROVED"],
            }
        )

        commits_df = pd.DataFrame(
            {
                "sha": ["abc", "def", "ghi", "jkl"],
                "author": ["alice", "bob", "alice", "charlie"],
                "additions": [100, 200, 50, 300],
                "deletions": [50, 100, 25, 150],
                "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            }
        )

        dfs = {"pull_requests": prs_df, "reviews": reviews_df, "commits": commits_df, "deployments": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)

        # Act
        pr_metrics = calculator.calculate_pr_metrics()
        review_metrics = calculator.calculate_review_metrics()
        contributor_metrics = calculator.calculate_contributor_metrics()

        # Assert
        # Verify team-level aggregations
        assert pr_metrics["total_prs"] == 4
        assert pr_metrics["merged_prs"] == 3
        assert review_metrics["total_reviews"] == 4
        assert contributor_metrics["total_commits"] == 4


class TestPersonMetrics:
    """Tests for person-level metrics"""

    def test_filters_metrics_by_person(self):
        # Arrange - Data for multiple people
        prs_df = pd.DataFrame(
            {
                "pr_number": [1, 2, 3, 4],
                "author": ["alice", "bob", "alice", "charlie"],
                "merged": [True, True, False, True],
                "state": ["merged", "merged", "open", "merged"],
                "additions": [100, 200, 50, 300],
                "deletions": [50, 100, 25, 150],
                "cycle_time_hours": [24.0, 48.0, None, 36.0],
                "time_to_first_review_hours": [2.0, 4.0, None, 3.0],
            }
        )

        dfs = {
            "pull_requests": prs_df,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)

        # Act - Filter for Alice
        alice_prs = prs_df[prs_df["author"] == "alice"]
        alice_dfs = {
            "pull_requests": alice_prs,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }
        alice_calculator = MetricsCalculator(alice_dfs)
        alice_metrics = alice_calculator.calculate_pr_metrics()

        # Assert
        assert alice_metrics["total_prs"] == 2  # Alice has 2 PRs
        assert alice_metrics["merged_prs"] == 1  # 1 merged


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_handles_missing_columns_gracefully(self):
        # Arrange - DataFrame missing some expected columns
        incomplete_df = pd.DataFrame(
            {
                "pr_number": [1, 2],
                "author": ["alice", "bob"],
                "merged": [True, False],
                # Missing state, additions, deletions, etc.
            }
        )

        dfs = {
            "pull_requests": incomplete_df,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "deployments": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)

        # Act & Assert - Should handle gracefully (may raise KeyError or return partial metrics)
        try:
            metrics = calculator.calculate_pr_metrics()
            # If it doesn't raise, verify it returns something
            assert metrics is not None
        except KeyError:
            # Expected if columns are required
            pass

    def test_handles_all_none_cycle_times(self):
        # Arrange - All cycle times are None
        df = pd.DataFrame(
            {
                "pr_number": [1, 2, 3],
                "author": ["alice", "bob", "charlie"],
                "merged": [False, False, False],
                "state": ["open", "open", "open"],
                "additions": [100, 200, 300],
                "deletions": [50, 100, 150],
                "cycle_time_hours": [None, None, None],
                "time_to_first_review_hours": [None, None, None],
            }
        )

        dfs = {"pull_requests": df, "reviews": pd.DataFrame(), "commits": pd.DataFrame(), "deployments": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert - Mean/median of all None should be NaN
        import math

        assert math.isnan(metrics["avg_cycle_time_hours"]) or metrics["avg_cycle_time_hours"] is None

    def test_handles_single_pr(self):
        # Arrange - Only one PR
        df = pd.DataFrame(
            {
                "pr_number": [1],
                "author": ["alice"],
                "merged": [True],
                "state": ["merged"],
                "additions": [100],
                "deletions": [50],
                "cycle_time_hours": [24.0],
                "time_to_first_review_hours": [2.0],
            }
        )

        dfs = {"pull_requests": df, "reviews": pd.DataFrame(), "commits": pd.DataFrame(), "deployments": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_pr_metrics()

        # Assert
        assert metrics["total_prs"] == 1
        assert metrics["merged_prs"] == 1
        assert metrics["merge_rate"] == 1.0
        assert metrics["avg_cycle_time_hours"] == 24.0


class TestCalculatePerformanceScore:
    """Tests for calculate_performance_score static method"""

    def test_calculate_performance_score_with_default_weights(self):
        """Test performance score calculation with default weights (includes DORA metrics)"""
        # Arrange - sample metrics for a person and comparison list
        person_metrics = {
            "prs": 10,
            "reviews": 20,
            "commits": 50,
            "cycle_time": 48.0,
            "jira_completed": 5,
            "merge_rate": 0.8,
            # DORA metrics (default weights include these)
            "deployment_frequency": 1.5,  # Middle value
            "lead_time": 48.0,  # Middle value
            "change_failure_rate": 0.15,  # Middle value
            "mttr": 24.0,  # Middle value
        }

        # List of all metrics for normalization (3 people)
        all_metrics = [
            {
                "prs": 5,
                "reviews": 10,
                "commits": 30,
                "cycle_time": 72.0,
                "jira_completed": 2,
                "merge_rate": 0.5,
                "deployment_frequency": 0.5,
                "lead_time": 72.0,
                "change_failure_rate": 0.30,
                "mttr": 48.0,
            },
            person_metrics,
            {
                "prs": 15,
                "reviews": 30,
                "commits": 70,
                "cycle_time": 24.0,
                "jira_completed": 8,
                "merge_rate": 1.0,
                "deployment_frequency": 2.5,
                "lead_time": 24.0,
                "change_failure_rate": 0.05,
                "mttr": 12.0,
            },
        ]

        # Act
        score = MetricsCalculator.calculate_performance_score(person_metrics, all_metrics)

        # Assert - score should be calculated and between 0-100
        assert score is not None
        assert 0 <= score <= 100
        # Person with middle values should have a score around 50
        assert 40 <= score <= 60

    def test_calculate_performance_score_with_custom_weights(self):
        """Test performance score calculation with custom weights"""
        # Arrange
        person_metrics = {
            "prs": 10,
            "reviews": 30,  # High reviews
            "commits": 50,
            "cycle_time": 48.0,
            "jira_completed": 5,
            "merge_rate": 0.8,
        }

        all_metrics = [
            {"prs": 5, "reviews": 10, "commits": 30, "cycle_time": 72.0, "jira_completed": 2, "merge_rate": 0.5},
            person_metrics,
            {"prs": 15, "reviews": 30, "commits": 70, "cycle_time": 24.0, "jira_completed": 8, "merge_rate": 1.0},
        ]

        # Custom weights heavily favor reviews
        custom_weights = {
            "prs": 0.10,
            "reviews": 0.50,  # 50% weight on reviews
            "commits": 0.10,
            "cycle_time": 0.10,
            "jira_completed": 0.10,
            "merge_rate": 0.10,
        }

        # Act
        score_default = MetricsCalculator.calculate_performance_score(person_metrics, all_metrics)
        score_custom = MetricsCalculator.calculate_performance_score(
            person_metrics, all_metrics, weights=custom_weights
        )

        # Assert
        assert score_default is not None
        assert score_custom is not None
        assert 0 <= score_default <= 100
        assert 0 <= score_custom <= 100
        # Since person has high reviews, custom weight score should be higher
        assert score_custom >= score_default

    def test_calculate_performance_score_with_zero_weights(self):
        """Test performance score with some metrics having zero weight"""
        person_metrics = {
            "prs": 15,  # High PRs
            "reviews": 30,  # High reviews
            "commits": 30,  # Low commits
            "cycle_time": 72.0,  # High cycle time
            "jira_completed": 2,  # Low jira
            "merge_rate": 0.5,  # Low merge rate
        }

        all_metrics = [
            person_metrics,
            {"prs": 5, "reviews": 10, "commits": 70, "cycle_time": 24.0, "jira_completed": 8, "merge_rate": 1.0},
            {"prs": 10, "reviews": 20, "commits": 50, "cycle_time": 48.0, "jira_completed": 5, "merge_rate": 0.75},
        ]

        # Weights with some zeros (only PRs and reviews count)
        weights_with_zeros = {
            "prs": 0.50,
            "reviews": 0.50,
            "commits": 0.0,
            "cycle_time": 0.0,
            "jira_completed": 0.0,
            "merge_rate": 0.0,
        }

        # Act
        score = MetricsCalculator.calculate_performance_score(person_metrics, all_metrics, weights=weights_with_zeros)

        # Assert - person has high PRs and reviews, so score should be high
        assert score is not None
        assert 80 <= score <= 100

    def test_calculate_performance_score_extreme_values(self):
        """Test performance score with person at extremes (min/max)"""
        # Person at maximum values
        person_max = {
            "prs": 15,
            "reviews": 30,
            "commits": 70,
            "cycle_time": 24.0,  # Lowest (best)
            "jira_completed": 8,
            "merge_rate": 1.0,
            # DORA metrics at best values
            "deployment_frequency": 3.0,  # High (best)
            "lead_time": 12.0,  # Low (best)
            "change_failure_rate": 0.05,  # Low (best)
            "mttr": 6.0,  # Low (best)
        }

        # Person at minimum values
        person_min = {
            "prs": 5,
            "reviews": 10,
            "commits": 30,
            "cycle_time": 72.0,  # Highest (worst)
            "jira_completed": 2,
            "merge_rate": 0.5,
            # DORA metrics at worst values
            "deployment_frequency": 0.3,  # Low (worst)
            "lead_time": 96.0,  # High (worst)
            "change_failure_rate": 0.40,  # High (worst)
            "mttr": 72.0,  # High (worst)
        }

        all_metrics = [person_min, person_max]

        # Act
        score_max = MetricsCalculator.calculate_performance_score(person_max, all_metrics)
        score_min = MetricsCalculator.calculate_performance_score(person_min, all_metrics)

        # Assert
        assert score_max is not None
        assert score_min is not None
        # Max performer should have higher score than min performer
        assert score_max > score_min
        # Max performer should be at or near 100
        assert score_max >= 95
        # Min performer should be at or near 0
        assert score_min <= 10


class TestCalculateDeploymentMetrics:
    """Tests for calculate_deployment_metrics method"""

    def test_empty_releases_returns_zero_deployments(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)

        # Act
        metrics = calculator.calculate_deployment_metrics()

        # Assert
        assert metrics["total_deployments"] == 0
        assert metrics["deployments_per_week"] == 0

    def test_missing_releases_key_returns_zero_deployments(self):
        # Arrange - releases key missing entirely
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_deployment_metrics()

        # Assert
        assert metrics["total_deployments"] == 0
        assert metrics["deployments_per_week"] == 0

    def test_calculates_total_deployments(self):
        # Arrange
        releases_df = pd.DataFrame(
            {
                "name": ["v1.0", "v1.1", "v1.2"],
                "published_at": ["2024-01-01", "2024-01-08", "2024-01-15"],
                "environment": ["production", "production", "production"],
            }
        )
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases_df,
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_deployment_metrics()

        # Assert
        assert metrics["total_deployments"] == 3

    def test_filters_production_releases_only(self):
        # Arrange
        releases_df = pd.DataFrame(
            {
                "name": ["v1.0", "v1.1", "v1.2", "v1.3-staging"],
                "published_at": ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-20"],
                "environment": ["production", "production", "production", "staging"],
            }
        )
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases_df,
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_deployment_metrics()

        # Assert
        assert metrics["total_deployments"] == 3  # Only production
        assert "deployments_by_environment" in metrics
        assert metrics["deployments_by_environment"]["production"] == 3
        assert metrics["deployments_by_environment"]["staging"] == 1

    def test_calculates_deployments_per_week(self):
        # Arrange - 4 deployments over 28 days (4 weeks)
        releases_df = pd.DataFrame(
            {
                "name": ["v1.0", "v1.1", "v1.2", "v1.3"],
                "published_at": ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-29"],
                "environment": ["production", "production", "production", "production"],
            }
        )
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases_df,
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_deployment_metrics()

        # Assert
        # 4 deployments over 28 days = 1 deployment/week
        assert metrics["deployments_per_week"] == pytest.approx(1.0, rel=0.1)

    def test_handles_no_environment_column(self):
        # Arrange - Releases without environment column
        releases_df = pd.DataFrame(
            {
                "name": ["v1.0", "v1.1", "v1.2"],
                "published_at": ["2024-01-01", "2024-01-08", "2024-01-15"],
            }
        )
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases_df,
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_deployment_metrics()

        # Assert - Should count all releases as production
        assert metrics["total_deployments"] == 3
        assert "deployments_by_environment" not in metrics

    def test_handles_no_published_at_column(self):
        # Arrange - Releases without published_at
        releases_df = pd.DataFrame(
            {
                "name": ["v1.0", "v1.1", "v1.2"],
                "environment": ["production", "production", "production"],
            }
        )
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases_df,
        }
        calculator = MetricsCalculator(dfs)

        # Act
        metrics = calculator.calculate_deployment_metrics()

        # Assert - Should use default 90-day window
        assert metrics["total_deployments"] == 3
        assert metrics["deployments_per_week"] == pytest.approx(3 / (90 / 7), rel=0.1)


class TestExtractGithubMembers:
    """Tests for _extract_github_members method"""

    def test_extracts_github_members_new_format(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)
        team_config = {
            "name": "Backend",
            "members": [
                {"name": "Alice", "github": "alice", "jira": "alice123"},
                {"name": "Bob", "github": "bob", "jira": "bob456"},
                {"name": "Charlie", "github": "charlie", "jira": "charlie789"},
            ],
        }

        # Act
        github_members = calculator._extract_github_members(team_config)

        # Assert
        assert len(github_members) == 3
        assert "alice" in github_members
        assert "bob" in github_members
        assert "charlie" in github_members

    def test_extracts_github_members_old_format(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)
        team_config = {"name": "Backend", "github": {"members": ["alice", "bob", "charlie"]}}

        # Act
        github_members = calculator._extract_github_members(team_config)

        # Assert
        assert len(github_members) == 3
        assert "alice" in github_members
        assert "bob" in github_members
        assert "charlie" in github_members

    def test_handles_missing_members_key(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)
        team_config = {"name": "Backend"}

        # Act
        github_members = calculator._extract_github_members(team_config)

        # Assert
        assert github_members == []

    def test_handles_empty_members_list(self, empty_dataframes):
        # Arrange
        calculator = MetricsCalculator(empty_dataframes)
        team_config = {"name": "Backend", "members": []}

        # Act
        github_members = calculator._extract_github_members(team_config)

        # Assert
        assert github_members == []

    def test_skips_members_without_github(self, empty_dataframes):
        # Arrange - Some members missing github field
        calculator = MetricsCalculator(empty_dataframes)
        team_config = {
            "name": "Backend",
            "members": [
                {"name": "Alice", "github": "alice", "jira": "alice123"},
                {"name": "Bob", "jira": "bob456"},  # Missing github
                {"name": "Charlie", "github": "charlie", "jira": "charlie789"},
            ],
        }

        # Act
        github_members = calculator._extract_github_members(team_config)

        # Assert
        assert len(github_members) == 2
        assert "alice" in github_members
        assert "charlie" in github_members
        assert "bob" not in github_members


class TestFilterTeamGithubData:
    """Tests for _filter_team_github_data method"""

    def test_filters_pull_requests_by_author(self):
        # Arrange
        prs_df = pd.DataFrame(
            {
                "pr_number": [1, 2, 3, 4],
                "author": ["alice", "bob", "charlie", "david"],
                "merged": [True, True, False, True],
                "state": ["merged", "merged", "open", "merged"],
            }
        )
        dfs = {
            "pull_requests": prs_df,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)
        github_members = ["alice", "bob"]

        # Act
        filtered_dfs = calculator._filter_team_github_data(github_members)

        # Assert
        assert len(filtered_dfs["pull_requests"]) == 2
        assert set(filtered_dfs["pull_requests"]["author"]) == {"alice", "bob"}

    def test_filters_reviews_by_reviewer(self):
        # Arrange
        reviews_df = pd.DataFrame(
            {
                "reviewer": ["alice", "bob", "charlie", "david"],
                "pr_number": [1, 1, 2, 3],
                "state": ["APPROVED", "APPROVED", "CHANGES_REQUESTED", "APPROVED"],
            }
        )
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": reviews_df,
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)
        github_members = ["alice", "charlie"]

        # Act
        filtered_dfs = calculator._filter_team_github_data(github_members)

        # Assert
        assert len(filtered_dfs["reviews"]) == 2
        assert set(filtered_dfs["reviews"]["reviewer"]) == {"alice", "charlie"}

    def test_filters_commits_by_author(self):
        # Arrange
        commits_df = pd.DataFrame(
            {
                "sha": ["abc", "def", "ghi", "jkl"],
                "author": ["alice", "bob", "charlie", "david"],
                "additions": [100, 200, 50, 300],
                "deletions": [50, 100, 25, 150],
            }
        )
        dfs = {
            "pull_requests": pd.DataFrame(),
            "reviews": pd.DataFrame(),
            "commits": commits_df,
            "releases": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)
        github_members = ["bob", "david"]

        # Act
        filtered_dfs = calculator._filter_team_github_data(github_members)

        # Assert
        assert len(filtered_dfs["commits"]) == 2
        assert set(filtered_dfs["commits"]["author"]) == {"bob", "david"}

    def test_returns_empty_dataframes_when_no_matches(self):
        # Arrange
        prs_df = pd.DataFrame(
            {
                "pr_number": [1, 2, 3],
                "author": ["alice", "bob", "charlie"],
                "merged": [True, True, False],
            }
        )
        dfs = {
            "pull_requests": prs_df,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": pd.DataFrame(),
        }
        calculator = MetricsCalculator(dfs)
        github_members = ["david", "eve"]  # Not in data

        # Act
        filtered_dfs = calculator._filter_team_github_data(github_members)

        # Assert
        assert filtered_dfs["pull_requests"].empty
        assert filtered_dfs["reviews"].empty
        assert filtered_dfs["commits"].empty

    def test_returns_only_github_dataframes(self):
        # Arrange - Method returns only PRs, reviews, commits (not releases)
        prs_df = pd.DataFrame(
            {
                "pr_number": [1, 2],
                "author": ["alice", "bob"],
                "merged": [True, False],
            }
        )
        releases_df = pd.DataFrame(
            {
                "name": ["v1.0", "v1.1"],
                "published_at": ["2024-01-01", "2024-01-08"],
                "environment": ["production", "production"],
            }
        )
        dfs = {
            "pull_requests": prs_df,
            "reviews": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "releases": releases_df,
        }
        calculator = MetricsCalculator(dfs)
        github_members = ["alice", "bob"]

        # Act
        filtered_dfs = calculator._filter_team_github_data(github_members)

        # Assert - Returns only GitHub data (PRs, reviews, commits), not releases
        assert "pull_requests" in filtered_dfs
        assert "reviews" in filtered_dfs
        assert "commits" in filtered_dfs
        assert "releases" not in filtered_dfs  # Releases not included
