"""Tests for DORA metrics calculation"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.models.metrics import MetricsCalculator


class TestDeploymentFrequency:
    """Test deployment frequency DORA metric"""

    def test_deployment_frequency_elite_level(self):
        """Test elite level classification (>= 1 per day)"""
        # Create 100 releases over 90 days (1.1 per day)
        releases = []
        base_date = datetime(2025, 1, 1)
        for i in range(100):
            releases.append(
                {
                    "tag_name": f"v1.0.{i}",
                    "environment": "production",
                    "published_at": base_date + timedelta(days=i % 90),
                    "repo": "test/repo",
                }
            )

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["deployment_frequency"]["level"] == "elite"
        assert result["deployment_frequency"]["total_deployments"] == 100
        assert result["deployment_frequency"]["per_day"] >= 1.0

    def test_deployment_frequency_high_level(self):
        """Test high level classification (>= 1 per week)"""
        # Create 20 releases over 90 days (~1.5 per week)
        releases = []
        base_date = datetime(2025, 1, 1)
        for i in range(20):
            releases.append(
                {
                    "tag_name": f"v1.0.{i}",
                    "environment": "production",
                    "published_at": base_date + timedelta(days=i * 4),
                    "repo": "test/repo",
                }
            )

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["deployment_frequency"]["level"] == "high"
        assert result["deployment_frequency"]["per_week"] >= 1.0

    def test_deployment_frequency_medium_level(self):
        """Test medium level classification (>= 1 per month)"""
        # Create 3 releases over 90 days
        releases = []
        base_date = datetime(2025, 1, 1)
        for i in range(3):
            releases.append(
                {
                    "tag_name": f"v1.0.{i}",
                    "environment": "production",
                    "published_at": base_date + timedelta(days=i * 30),
                    "repo": "test/repo",
                }
            )

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["deployment_frequency"]["level"] == "medium"
        assert result["deployment_frequency"]["per_month"] >= 1.0

    def test_deployment_frequency_low_level(self):
        """Test low level classification (< 1 per month)"""
        # Create 2 releases over 90 days (< 1 per month)
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": datetime(2025, 3, 31),
                "repo": "test/repo",
            },
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["deployment_frequency"]["level"] == "low"
        assert result["deployment_frequency"]["per_month"] < 1.0

    def test_deployment_frequency_filters_production_only(self):
        """Test that deployment frequency only counts production releases"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.1-rc1",
                "environment": "staging",
                "published_at": datetime(2025, 1, 2),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": datetime(2025, 1, 3),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.2-beta",
                "environment": "staging",
                "published_at": datetime(2025, 1, 4),
                "repo": "test/repo",
            },
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Should only count 2 production releases
        assert result["deployment_frequency"]["total_deployments"] == 2

    def test_deployment_frequency_no_releases(self):
        """Test deployment frequency with no releases"""
        dfs = {"releases": pd.DataFrame(), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["deployment_frequency"]["total_deployments"] == 0
        assert result["deployment_frequency"]["level"] == "low"


class TestLeadTimeForChanges:
    """Test lead time for changes DORA metric"""

    def test_lead_time_elite_level(self):
        """Test elite level classification (< 24 hours)"""
        # PR merged, release 12 hours later
        prs = [{"pr_number": 1, "merged": True, "merged_at": datetime(2025, 1, 1, 10, 0), "author": "user1"}]

        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1, 22, 0),  # 12 hours later
                "repo": "test/repo",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["lead_time"]["level"] == "elite"
        assert result["lead_time"]["median_hours"] == 12.0
        assert result["lead_time"]["median_days"] == 0.5

    def test_lead_time_high_level(self):
        """Test high level classification (< 1 week)"""
        # PR merged, release 3 days later
        prs = [{"pr_number": 1, "merged": True, "merged_at": datetime(2025, 1, 1, 10, 0), "author": "user1"}]

        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 4, 10, 0),  # 3 days later
                "repo": "test/repo",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["lead_time"]["level"] == "high"
        assert result["lead_time"]["median_hours"] == 72.0

    def test_lead_time_maps_pr_to_next_release(self):
        """Test that lead time maps PRs to the next deployment"""
        prs = [
            {"pr_number": 1, "merged": True, "merged_at": datetime(2025, 1, 1, 10, 0), "author": "user1"},
            {"pr_number": 2, "merged": True, "merged_at": datetime(2025, 1, 2, 10, 0), "author": "user1"},
            {"pr_number": 3, "merged": True, "merged_at": datetime(2025, 1, 5, 10, 0), "author": "user1"},
        ]

        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 3, 10, 0),
                "repo": "test/repo",
            },  # Gets PRs 1 & 2
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": datetime(2025, 1, 6, 10, 0),
                "repo": "test/repo",
            },  # Gets PR 3
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # PR1: 2 days to deployment, PR2: 1 day, PR3: 1 day
        # Median should be 24 hours
        assert result["lead_time"]["sample_size"] == 3
        assert result["lead_time"]["median_hours"] == 24.0

    def test_lead_time_ignores_unmerged_prs(self):
        """Test that lead time ignores PRs that weren't merged"""
        prs = [
            {"pr_number": 1, "merged": True, "merged_at": datetime(2025, 1, 1, 10, 0), "author": "user1"},
            {"pr_number": 2, "merged": False, "merged_at": None, "author": "user1"},
        ]

        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 2, 10, 0),
                "repo": "test/repo",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Only 1 merged PR should be counted
        assert result["lead_time"]["sample_size"] == 1

    def test_lead_time_no_releases(self):
        """Test lead time with no releases"""
        prs = [{"pr_number": 1, "merged": True, "merged_at": datetime(2025, 1, 1, 10, 0), "author": "user1"}]

        dfs = {"releases": pd.DataFrame(), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert result["lead_time"]["median_hours"] is None
        assert result["lead_time"]["sample_size"] == 0


class TestChangeFailureRate:
    """Test change failure rate DORA metric"""

    def test_cfr_without_incident_data(self):
        """Test CFR returns placeholder when incident data not provided"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1),
                "repo": "test/repo",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Should return placeholder since incidents not implemented yet
        assert result["change_failure_rate"]["rate_percent"] is None
        assert result["change_failure_rate"]["total_deployments"] == 1
        assert "note" in result["change_failure_rate"]


class TestMTTR:
    """Test Mean Time to Restore DORA metric"""

    def test_mttr_without_incident_data(self):
        """Test MTTR returns placeholder when incident data not provided"""
        dfs = {"releases": pd.DataFrame(), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # Should return placeholder since incidents not implemented yet
        assert result["mttr"]["median_hours"] is None
        assert "note" in result["mttr"]


class TestDORAPerformanceLevel:
    """Test overall DORA performance level classification"""

    def test_dora_level_elite(self):
        """Test elite classification with 3+ elite metrics"""
        # Elite deployment frequency (>1/day) and elite lead time (<24h)
        prs = [{"pr_number": 1, "merged": True, "merged_at": datetime(2025, 1, 1, 10, 0), "author": "user1"}]

        releases = []
        base_date = datetime(2025, 1, 1)
        # 100 releases over 90 days = elite deployment frequency
        for i in range(100):
            releases.append(
                {
                    "tag_name": f"v1.0.{i}",
                    "environment": "production",
                    "published_at": base_date + timedelta(days=i % 90, hours=i % 24),
                    "repo": "test/repo",
                }
            )

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(prs), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        # With elite deployment frequency and potentially elite lead time
        assert result["dora_level"]["level"] in ["Elite", "High"]

    def test_dora_level_includes_breakdown(self):
        """Test that DORA level includes breakdown by metric"""
        dfs = {"releases": pd.DataFrame(), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert "breakdown" in result["dora_level"]
        assert "elite" in result["dora_level"]["breakdown"]
        assert "high" in result["dora_level"]["breakdown"]
        assert "medium" in result["dora_level"]["breakdown"]
        assert "low" in result["dora_level"]["breakdown"]


class TestDORAMeasurementPeriod:
    """Test DORA measurement period tracking"""

    def test_measurement_period_from_releases(self):
        """Test measurement period calculated from release dates"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 1),
                "repo": "test/repo",
            },
            {
                "tag_name": "v1.0.1",
                "environment": "production",
                "published_at": datetime(2025, 3, 31),
                "repo": "test/repo",
            },
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics()

        assert "measurement_period" in result
        assert result["measurement_period"]["days"] == 89

    def test_measurement_period_explicit_dates(self):
        """Test measurement period with explicit start/end dates"""
        releases = [
            {
                "tag_name": "v1.0.0",
                "environment": "production",
                "published_at": datetime(2025, 1, 15),
                "repo": "test/repo",
            }
        ]

        dfs = {"releases": pd.DataFrame(releases), "pull_requests": pd.DataFrame(), "commits": pd.DataFrame()}

        calculator = MetricsCalculator(dfs)
        result = calculator.calculate_dora_metrics(start_date=datetime(2025, 1, 1), end_date=datetime(2025, 3, 31))

        assert result["measurement_period"]["days"] == 89
