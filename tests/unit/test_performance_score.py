"""
Tests for performance score calculation.

The performance score is a critical feature used for ranking teams and individuals
across the dashboard. It normalizes metrics to 0-100 scale and calculates a
weighted composite score.
"""

import pytest
from src.models.metrics import MetricsCalculator


class TestNormalize:
    """Tests for the normalize helper function"""

    def test_normalize_basic(self):
        """Test basic normalization to 0-100 scale"""
        result = MetricsCalculator.normalize(5, 0, 10)
        assert result == 50.0

    def test_normalize_min_value(self):
        """Test normalization returns 0 for minimum value"""
        result = MetricsCalculator.normalize(10, 10, 50)
        assert result == 0.0

    def test_normalize_max_value(self):
        """Test normalization returns 100 for maximum value"""
        result = MetricsCalculator.normalize(50, 10, 50)
        assert result == 100.0

    def test_normalize_equal_min_max(self):
        """Test normalization returns 50 when all values are equal"""
        result = MetricsCalculator.normalize(42, 42, 42)
        assert result == 50.0

    def test_normalize_fractional(self):
        """Test normalization handles fractional values"""
        result = MetricsCalculator.normalize(2.5, 0, 10)
        assert result == 25.0


class TestPerformanceScore:
    """Tests for calculate_performance_score function"""

    def test_single_metric_perfect_score(self):
        """Test perfect score when one metric is at maximum"""
        metrics = {'prs': 100, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0}
        all_metrics = [
            {'prs': 100, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0},
            {'prs': 0, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0},
        ]
        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)
        # PRs weight is 15% (new default), so perfect PR score = 15.0
        assert score == 15.0

    def test_all_metrics_equal(self):
        """Test score when all teams have identical metrics"""
        metrics = {'prs': 10, 'reviews': 20, 'commits': 30, 'jira_completed': 5, 'merge_rate': 80}
        all_metrics = [
            {'prs': 10, 'reviews': 20, 'commits': 30, 'jira_completed': 5, 'merge_rate': 80},
            {'prs': 10, 'reviews': 20, 'commits': 30, 'jira_completed': 5, 'merge_rate': 80},
        ]
        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)
        # All normalized to 50, so score = 50 * (0.15 + 0.15 + 0.10 + 0.15 + 0.05) = 50 * 0.60 = 30.0
        # Note: cycle_time is 0, so that 0.10 weight is not included, DORA metrics not present
        assert score == 30.0

    def test_cycle_time_inversion(self):
        """Test that cycle time is inverted (lower is better)"""
        # Team with lower cycle time should score higher
        low_cycle = {'prs': 10, 'reviews': 10, 'commits': 10, 'cycle_time': 5, 'jira_completed': 10, 'merge_rate': 80}
        high_cycle = {'prs': 10, 'reviews': 10, 'commits': 10, 'cycle_time': 50, 'jira_completed': 10, 'merge_rate': 80}

        all_metrics = [low_cycle, high_cycle]

        low_score = MetricsCalculator.calculate_performance_score(low_cycle, all_metrics)
        high_score = MetricsCalculator.calculate_performance_score(high_cycle, all_metrics)

        # Lower cycle time should have higher score
        assert low_score > high_score

    def test_custom_weights(self):
        """Test custom weight configuration"""
        metrics = {'prs': 100, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0}
        all_metrics = [
            {'prs': 100, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0},
            {'prs': 0, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0},
        ]

        custom_weights = {
            'prs': 0.50,  # Give PRs 50% weight
            'reviews': 0.10,
            'commits': 0.10,
            'cycle_time': 0.10,
            'jira_completed': 0.10,
            'merge_rate': 0.10
        }

        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics, weights=custom_weights)
        # Perfect PR score with 50% weight = 50.0
        assert score == 50.0

    def test_zero_metrics(self):
        """Test score with all zero metrics"""
        metrics = {'prs': 0, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0}
        all_metrics = [
            {'prs': 10, 'reviews': 10, 'commits': 10, 'jira_completed': 10, 'merge_rate': 80},
            {'prs': 0, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0},
        ]
        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)
        # All metrics at minimum = 0
        assert score == 0.0

    def test_team_size_normalization(self):
        """Test per-capita normalization with team_size parameter"""
        # Large team with high volume
        large_team = {
            'prs': 100,
            'reviews': 200,
            'commits': 300,
            'jira_completed': 50,
            'merge_rate': 80,
            'team_size': 10
        }

        # Small team with lower volume
        small_team = {
            'prs': 20,
            'reviews': 40,
            'commits': 60,
            'jira_completed': 10,
            'merge_rate': 80,
            'team_size': 2
        }

        all_metrics = [large_team, small_team]

        # Calculate with team size normalization
        large_score = MetricsCalculator.calculate_performance_score(
            large_team, all_metrics, team_size=10
        )
        small_score = MetricsCalculator.calculate_performance_score(
            small_team, all_metrics, team_size=2
        )

        # Per capita they're equal (100/10=10 vs 20/2=10), so scores should be equal
        assert large_score == small_score

    def test_mixed_metrics(self):
        """Test realistic scenario with mixed metric values"""
        team_a = {
            'prs': 50,
            'reviews': 80,
            'commits': 100,
            'cycle_time': 10,
            'jira_completed': 30,
            'merge_rate': 90
        }

        team_b = {
            'prs': 100,
            'reviews': 40,
            'commits': 50,
            'cycle_time': 20,
            'jira_completed': 60,
            'merge_rate': 70
        }

        all_metrics = [team_a, team_b]

        score_a = MetricsCalculator.calculate_performance_score(team_a, all_metrics)
        score_b = MetricsCalculator.calculate_performance_score(team_b, all_metrics)

        # Both should have valid scores between 0-100
        assert 0 <= score_a <= 100
        assert 0 <= score_b <= 100
        # Scores should be different
        assert score_a != score_b

    def test_missing_metrics_handled(self):
        """Test that missing metrics are handled gracefully"""
        metrics = {'prs': 50}  # Only PRs provided
        all_metrics = [
            {'prs': 100, 'reviews': 50},
            {'prs': 0, 'reviews': 0},
        ]

        # Should not crash, should calculate with available metrics
        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)
        assert isinstance(score, float)
        assert score >= 0

    def test_single_team_comparison(self):
        """Test score calculation with only one team (edge case)"""
        metrics = {'prs': 50, 'reviews': 30, 'commits': 100, 'jira_completed': 20, 'merge_rate': 85}
        all_metrics = [metrics]  # Only one team

        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)
        # With only one team, all metrics normalize to 50, so score should be 50 * sum of weights
        # cycle_time missing so: 50 * (0.15 + 0.15 + 0.10 + 0.15 + 0.05) = 50 * 0.60 = 30.0
        # DORA metrics not present so their weights not included
        assert score == 30.0

    def test_cycle_time_zero_handled(self):
        """Test that zero cycle time is handled correctly"""
        metrics = {
            'prs': 50,
            'reviews': 30,
            'commits': 100,
            'cycle_time': 0,  # Zero cycle time
            'jira_completed': 20,
            'merge_rate': 85
        }
        all_metrics = [
            {'prs': 50, 'reviews': 30, 'commits': 100, 'cycle_time': 0, 'jira_completed': 20, 'merge_rate': 85},
            {'prs': 40, 'reviews': 20, 'commits': 80, 'cycle_time': 10, 'jira_completed': 15, 'merge_rate': 75},
        ]

        # Should not crash with zero cycle time
        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)
        assert isinstance(score, float)
        # Cycle time of 0 should be excluded from scoring
        assert score >= 0

    def test_all_max_values(self):
        """Test team with maximum values in all metrics"""
        max_team = {
            'prs': 100,
            'reviews': 100,
            'commits': 100,
            'cycle_time': 5,  # Minimum (best)
            'jira_completed': 100,
            'merge_rate': 100
        }

        min_team = {
            'prs': 0,
            'reviews': 0,
            'commits': 0,
            'cycle_time': 50,  # Maximum (worst)
            'jira_completed': 0,
            'merge_rate': 0
        }

        all_metrics = [max_team, min_team]

        max_score = MetricsCalculator.calculate_performance_score(max_team, all_metrics)
        min_score = MetricsCalculator.calculate_performance_score(min_team, all_metrics)

        # Max team should have perfect score for 6 metrics only (DORA not present)
        # Sum of weights: 0.15 + 0.15 + 0.10 + 0.10 + 0.15 + 0.05 = 0.70
        # Score = 100 * 0.70 = 70.0
        assert max_score == 70.0
        # Min team should have zero score
        assert min_score == 0.0

    def test_team_size_zero_handled(self):
        """Test that team_size of 0 doesn't cause division by zero"""
        metrics = {'prs': 50, 'reviews': 30, 'commits': 100, 'jira_completed': 20, 'merge_rate': 85, 'team_size': 0}
        all_metrics = [metrics]

        # Should handle team_size=0 gracefully
        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics, team_size=0)
        assert isinstance(score, float)

    def test_default_weights_sum_to_one(self):
        """Test that default weights sum to 1.0 for proper scoring"""
        # This is a sanity check on the weight configuration
        default_weights = {
            'prs': 0.15,
            'reviews': 0.15,
            'commits': 0.10,
            'cycle_time': 0.10,
            'jira_completed': 0.15,
            'merge_rate': 0.05,
            # DORA metrics
            'deployment_frequency': 0.10,
            'lead_time': 0.10,
            'change_failure_rate': 0.05,
            'mttr': 0.05
        }

        total = sum(default_weights.values())
        assert total == 1.0, f"Weights should sum to 1.0, got {total}"

    def test_score_rounding(self):
        """Test that scores are rounded to 1 decimal place"""
        metrics = {'prs': 33, 'reviews': 33, 'commits': 33, 'jira_completed': 33, 'merge_rate': 33}
        all_metrics = [
            {'prs': 100, 'reviews': 100, 'commits': 100, 'jira_completed': 100, 'merge_rate': 100},
            {'prs': 0, 'reviews': 0, 'commits': 0, 'jira_completed': 0, 'merge_rate': 0},
        ]

        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)

        # Should be rounded to 1 decimal place
        assert isinstance(score, float)
        # Check that it has at most 1 decimal place
        assert len(str(score).split('.')[-1]) <= 1 or str(score).endswith('.0')

    def test_dora_metrics_included(self):
        """Test that DORA metrics are included in performance score calculation"""
        # Create teams where one has all max values including DORA, other has all min
        team_max = {
            'prs': 100,
            'reviews': 100,
            'commits': 100,
            'cycle_time': 1,  # Min cycle time (best)
            'jira_completed': 100,
            'merge_rate': 100,
            'deployment_frequency': 10.0,  # High deployment frequency (good)
            'lead_time': 1.0,  # Low lead time (good)
            'change_failure_rate': 1.0,  # Low CFR (good)
            'mttr': 0.5  # Low MTTR (good)
        }

        team_min = {
            'prs': 0,
            'reviews': 0,
            'commits': 0,
            'cycle_time': 50,  # High cycle time (worst)
            'jira_completed': 0,
            'merge_rate': 0,
            'deployment_frequency': 0.1,  # Low deployment frequency (bad)
            'lead_time': 20.0,  # High lead time (bad)
            'change_failure_rate': 50.0,  # High CFR (bad)
            'mttr': 10.0  # High MTTR (bad)
        }

        all_metrics = [team_max, team_min]

        score_max = MetricsCalculator.calculate_performance_score(team_max, all_metrics)
        score_min = MetricsCalculator.calculate_performance_score(team_min, all_metrics)

        # Team with max values should have perfect score (100), team with min should have 0
        # This tests that DORA metrics are included in the calculation
        assert score_max == 100.0
        assert score_min == 0.0

    def test_dora_metrics_none_handled(self):
        """Test that None DORA metrics are handled gracefully"""
        metrics = {
            'prs': 50,
            'reviews': 50,
            'commits': 50,
            'jira_completed': 50,
            'merge_rate': 80,
            'deployment_frequency': 2.0,
            'lead_time': 5.0,
            'change_failure_rate': None,  # No incident data
            'mttr': None  # No incident data
        }

        all_metrics = [
            metrics,
            {'prs': 40, 'reviews': 40, 'commits': 40, 'jira_completed': 40, 'merge_rate': 70,
             'deployment_frequency': 1.5, 'lead_time': 7.0, 'change_failure_rate': None, 'mttr': None}
        ]

        # Should not crash with None DORA metrics
        score = MetricsCalculator.calculate_performance_score(metrics, all_metrics)
        assert isinstance(score, float)
        assert score >= 0
        assert score <= 100

    def test_dora_lead_time_inversion(self):
        """Test that DORA lead time is inverted (lower is better)"""
        # Test that DORA metrics with explicit weights work correctly
        low_lead = {
            'prs': 50, 'reviews': 50, 'commits': 50, 'jira_completed': 50,
            'merge_rate': 50, 'cycle_time': 10,
            'lead_time': 1.0  # Min lead time (best)
        }
        high_lead = {
            'prs': 50, 'reviews': 50, 'commits': 50, 'jira_completed': 50,
            'merge_rate': 50, 'cycle_time': 10,
            'lead_time': 20.0  # Max lead time (worst)
        }

        all_metrics = [low_lead, high_lead]

        # Use explicit weights that include lead_time
        weights_with_dora = {
            'prs': 0.20,
            'reviews': 0.20,
            'commits': 0.10,
            'cycle_time': 0.10,
            'jira_completed': 0.20,
            'merge_rate': 0.10,
            'lead_time': 0.10  # Add lead time explicitly
        }

        low_score = MetricsCalculator.calculate_performance_score(low_lead, all_metrics, weights=weights_with_dora)
        high_score = MetricsCalculator.calculate_performance_score(high_lead, all_metrics, weights=weights_with_dora)

        # Lower lead time should have higher score (because lead time is inverted)
        assert low_score > high_score
