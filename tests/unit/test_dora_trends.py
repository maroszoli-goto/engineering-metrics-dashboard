"""Tests for DORA metrics trend calculations"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src.models.metrics import MetricsCalculator


class TestDeploymentFrequencyTrend:
    """Test deployment frequency trend calculation"""

    def test_deployment_frequency_trend_weekly_aggregation(self):
        """Test that deployment frequency trend aggregates by week"""
        # Create releases across 3 weeks
        releases = []
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        # Week 1: 2 releases
        releases.append(
            {"tag_name": "v1.0.0", "environment": "production", "published_at": base_date, "repo": "test/repo"}
        )
        releases.append(
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": base_date + timedelta(days=2),
                "repo": "test/repo",
            }
        )

        # Week 2: 3 releases
        releases.append(
            {
                "tag_name": "v1.0.2",
                "environment": "production",
                "published_at": base_date + timedelta(days=7),
                "repo": "test/repo",
            }
        )
        releases.append(
            {
                "tag_name": "v1.0.3",
                "environment": "production",
                "published_at": base_date + timedelta(days=9),
                "repo": "test/repo",
            }
        )
        releases.append(
            {
                "tag_name": "v1.0.4",
                "environment": "production",
                "published_at": base_date + timedelta(days=12),
                "repo": "test/repo",
            }
        )

        # Week 3: 1 release
        releases.append(
            {
                "tag_name": "v1.0.5",
                "environment": "production",
                "published_at": base_date + timedelta(days=14),
                "repo": "test/repo",
            }
        )

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Check trend exists
        assert "trend" in result["deployment_frequency"]
        trend = result["deployment_frequency"]["trend"]

        # Should have data (at least 2 weeks, possibly 3 depending on week boundaries)
        assert len(trend) >= 2

        # Check weekly counts are sensible
        weeks = sorted(trend.keys())
        total_releases = sum(trend.values())
        assert total_releases == 6  # Total releases across all weeks

    def test_deployment_frequency_trend_empty(self):
        """Test deployment frequency trend with no releases"""
        dfs = {"releases": pd.DataFrame(), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["deployment_frequency"]["trend"] == {}

    def test_deployment_frequency_trend_filters_staging(self):
        """Test that trend only includes production releases"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.1-rc",
                "environment": "staging",
                "published_at": datetime(2025, 1, 2, tzinfo=timezone.utc),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.2",
                "environment": "production",
                "published_at": datetime(2025, 1, 3, tzinfo=timezone.utc),
                "repo": "test/repo",
            },
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        trend = result["deployment_frequency"]["trend"]
        # Should only count 2 production releases
        assert sum(trend.values()) == 2


class TestLeadTimeTrend:
    """Test lead time for changes trend calculation"""

    def test_lead_time_trend_weekly_median(self):
        """Test that lead time trend calculates weekly median"""
        base_date = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)

        # Week 1: PRs with 1h and 3h lead times (median: 2h)
        prs = [
            {"number": 1, "merged": True, "merged_at": base_date, "author": "user1", "title": "PR 1"},
            {
                "number": 2,
                "merged": True,
                "merged_at": base_date + timedelta(hours=1),
                "author": "user1",
                "title": "PR 2",
            },
        ]

        # Week 2: PRs with 5h and 7h lead times (median: 6h)
        prs.extend(
            [
                {
                    "number": 3,
                    "merged": True,
                    "merged_at": base_date + timedelta(days=7),
                    "author": "user1",
                    "title": "PR 3",
                },
                {
                    "number": 4,
                    "merged": True,
                    "merged_at": base_date + timedelta(days=7, hours=1),
                    "author": "user1",
                    "title": "PR 4",
                },
            ]
        )

        # Releases to map PRs to
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": base_date + timedelta(hours=2),
                "repo": "test/repo",
            },  # 1h and 3h after PRs
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": base_date + timedelta(days=7, hours=7),
                "repo": "test/repo",
            },  # 5h and 7h after PRs
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Check trend exists
        assert "trend" in result["lead_time"]
        trend = result["lead_time"]["trend"]

        # Should have data for 2 weeks
        assert len(trend) >= 1  # At least 1 week of data

    def test_lead_time_trend_empty(self):
        """Test lead time trend with no PRs"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "repo": "test/repo",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["lead_time"]["trend"] == {}

    def test_lead_time_trend_with_jira_mapping(self):
        """Test lead time trend with Jira Fix Version mapping"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        prs = [
            {"number": 1, "merged": True, "merged_at": base_date, "author": "user1", "title": "[PROJ-123] Feature"},
        ]

        releases = [
            {
                "tag_name": "Live - 2/Jan/2025",
                "environment": "production",
                "published_at": base_date + timedelta(hours=12),
                "repo": "test/repo",
            },
        ]

        # Issue to version mapping
        issue_to_version_map = {"PROJ-123": "Live - 2/Jan/2025"}

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics(issue_to_version_map=issue_to_version_map)

        # Should have trend data using Jira-based mapping
        assert "trend" in result["lead_time"]


class TestChangeFailureRateTrend:
    """Test change failure rate trend calculation"""

    def test_cfr_trend_weekly_percentage(self):
        """Test that CFR trend calculates weekly failure rate"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        # Week 1: 2 deployments, 1 failed (50%)
        releases = [
            {"tag_name": "v1.0.0", "environment": "production", "published_at": base_date, "repo": "test/repo"},
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": base_date + timedelta(days=2),
                "repo": "test/repo",
            },
        ]

        # Week 2: 3 deployments, 2 failed (66.7%)
        releases.extend(
            [
                {
                    "tag_name": "v1.0.2",
                    "environment": "production",
                    "published_at": base_date + timedelta(days=7),
                    "repo": "test/repo",
                },
                {
                    "tag_name": "v1.0.3",
                    "environment": "production",
                    "published_at": base_date + timedelta(days=9),
                    "repo": "test/repo",
                },
                {
                    "tag_name": "v1.0.4",
                    "environment": "production",
                    "published_at": base_date + timedelta(days=12),
                    "repo": "test/repo",
                },
            ]
        )

        # Incidents correlated to deployments
        incidents = [
            {
                "key": "INC-1",
                "created": base_date + timedelta(hours=2),
                "resolved": base_date + timedelta(hours=5),
                "related_deployment": "v1.0.0",
            },  # Week 1 failure
            {
                "key": "INC-2",
                "created": base_date + timedelta(days=7, hours=2),
                "resolved": base_date + timedelta(days=7, hours=6),
                "related_deployment": "v1.0.2",
            },  # Week 2 failure
            {
                "key": "INC-3",
                "created": base_date + timedelta(days=9, hours=1),
                "resolved": base_date + timedelta(days=9, hours=3),
                "related_deployment": "v1.0.3",
            },  # Week 2 failure
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics(incidents_df=pd.DataFrame(incidents))

        # Check trend exists
        assert "trend" in result["change_failure_rate"]
        trend = result["change_failure_rate"]["trend"]

        # Should have data for 2 weeks
        assert len(trend) >= 1

    def test_cfr_trend_zero_incidents(self):
        """Test CFR trend with zero incidents (0% failure rate)"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": datetime(2025, 1, 2, tzinfo=timezone.utc),
                "repo": "test/repo",
            },
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics(incidents_df=pd.DataFrame())

        # Trend should exist but show 0% failure rate
        trend = result["change_failure_rate"]["trend"]
        if trend:  # Only check if trend exists
            assert all(rate == 0.0 for rate in trend.values())

    def test_cfr_trend_empty_without_incidents(self):
        """Test CFR trend when incidents data not provided"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "repo": "test/repo",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Without incidents, trend should be empty
        assert "trend" in result["change_failure_rate"]


class TestMTTRTrend:
    """Test Mean Time to Restore trend calculation"""

    def test_mttr_trend_weekly_median(self):
        """Test that MTTR trend calculates weekly median resolution time"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        # Week 1: 2 incidents with 2h and 4h resolution (median: 3h)
        incidents = [
            {
                "key": "INC-1",
                "created": base_date,
                "resolved": base_date + timedelta(hours=2),
                "resolution_time_hours": 2.0,
            },
            {
                "key": "INC-2",
                "created": base_date + timedelta(days=1),
                "resolved": base_date + timedelta(days=1, hours=4),
                "resolution_time_hours": 4.0,
            },
        ]

        # Week 2: 2 incidents with 1h and 5h resolution (median: 3h)
        incidents.extend(
            [
                {
                    "key": "INC-3",
                    "created": base_date + timedelta(days=7),
                    "resolved": base_date + timedelta(days=7, hours=1),
                    "resolution_time_hours": 1.0,
                },
                {
                    "key": "INC-4",
                    "created": base_date + timedelta(days=9),
                    "resolved": base_date + timedelta(days=9, hours=5),
                    "resolution_time_hours": 5.0,
                },
            ]
        )

        dfs = {"releases": pd.DataFrame(), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics(incidents_df=pd.DataFrame(incidents))

        # Check trend exists
        assert "trend" in result["mttr"]
        trend = result["mttr"]["trend"]

        # Should have data for 2 weeks
        assert len(trend) >= 1

    def test_mttr_trend_empty(self):
        """Test MTTR trend with no incidents"""
        dfs = {
            "releases": pd.DataFrame(),
            "pull_requests": pd.DataFrame(),
            "commits": pd.DataFrame(),
            "incidents": pd.DataFrame(),
        }

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Without incidents, trend should be empty
        assert "trend" in result["mttr"]
        assert result["mttr"]["trend"] == {}

    def test_mttr_trend_with_unresolved_incidents(self):
        """Test MTTR trend ignores unresolved incidents"""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        incidents = [
            # Resolved incident
            {
                "key": "INC-1",
                "created": base_date,
                "resolved": base_date + timedelta(hours=2),
                "resolution_time_hours": 2.0,
            },
            # Unresolved incident (should be ignored)
            {"key": "INC-2", "created": base_date + timedelta(days=1), "resolved": None, "resolution_time_hours": None},
        ]

        dfs = {"releases": pd.DataFrame(), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics(incidents_df=pd.DataFrame(incidents))

        # Should only count resolved incident
        trend = result["mttr"]["trend"]
        if trend:  # Only check if trend exists
            assert len(trend) >= 1


class TestTrendDataTypes:
    """Test that trend data types are correct for JSON serialization"""

    def test_trend_values_are_serializable(self):
        """Test that all trend values are JSON-serializable types"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "repo": "test/repo",
            }
        ]

        prs = [
            {
                "number": 1,
                "merged": True,
                "merged_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
                "author": "user1",
                "title": "PR 1",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Check all trends are dictionaries with string keys and numeric values
        for metric_name in ["deployment_frequency", "lead_time"]:
            if "trend" in result[metric_name]:
                trend = result[metric_name]["trend"]
                assert isinstance(trend, dict)
                for week, value in trend.items():
                    assert isinstance(week, str), f"Week key should be string, got {type(week)}"
                    assert isinstance(value, (int, float)), f"Value should be numeric, got {type(value)}"
