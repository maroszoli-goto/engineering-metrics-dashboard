"""Trends and performance calculation service

Application layer service for calculating person trends and performance scores.
This wraps Domain layer MetricsCalculator and PerformanceScorer to maintain proper layering.
"""

from typing import Dict, List, Optional

import pandas as pd

from src.models.metrics import MetricsCalculator
from src.models.performance_scoring import PerformanceScorer


class TrendsService:
    """Service for calculating person activity trends and performance scores"""

    @staticmethod
    def calculate_person_trends(raw_github_data: Dict, period: str = "weekly") -> Dict[str, List]:
        """Calculate person trends from raw GitHub data.

        Args:
            raw_github_data: Dict with pull_requests, reviews, commits lists
            period: Aggregation period ("weekly" or "daily")

        Returns:
            Dictionary with trend data for PRs, reviews, commits, and lines changed

        Note:
            This is an Application layer service that wraps Domain layer logic.
            Blueprints (Presentation) should call this instead of MetricsCalculator directly.
        """
        if not raw_github_data:
            return {
                "pr_trend": [],
                "review_trend": [],
                "commit_trend": [],
                "lines_changed_trend": [],
            }

        # Convert raw data to DataFrames (Application layer responsibility)
        person_dfs = {
            "pull_requests": pd.DataFrame(raw_github_data.get("pull_requests", [])),
            "reviews": pd.DataFrame(raw_github_data.get("reviews", [])),
            "commits": pd.DataFrame(raw_github_data.get("commits", [])),
        }

        # Use Domain layer to calculate (with no logger - trends don't need logging)
        calculator = MetricsCalculator(person_dfs, logger=None)
        return calculator.calculate_person_trends(raw_github_data, period=period)

    @staticmethod
    def calculate_performance_score(
        metrics: Dict, all_metrics_list: List[Dict], team_size: Optional[int] = None, weights: Optional[Dict] = None
    ) -> float:
        """Calculate overall performance score (0-100) for a team or person.

        Application layer wrapper for PerformanceScorer.calculate_performance_score().
        Blueprints should call this instead of accessing Domain layer directly.

        Args:
            metrics: Dict with individual metrics (prs, reviews, commits, etc.)
            all_metrics_list: List of all metrics dicts for normalization
            team_size: Optional team size for normalizing volume metrics (per-capita)
            weights: Optional dict of metric weights (defaults to balanced defaults)

        Returns:
            Performance score between 0-100

        Note:
            This delegates to Domain layer PerformanceScorer but provides proper
            layering so Presentation doesn't access Domain directly.
        """
        return PerformanceScorer.calculate_performance_score(metrics, all_metrics_list, team_size, weights)
