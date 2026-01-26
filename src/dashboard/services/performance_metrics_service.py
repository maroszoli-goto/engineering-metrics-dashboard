"""Performance metrics service for aggregating and analyzing route performance.

Provides business logic for:
- Route performance analysis
- Slow route identification
- Cache effectiveness tracking
- Performance trends over time
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.utils.performance_tracker import PerformanceTracker


class PerformanceMetricsService:
    """Service for analyzing performance metrics.

    Wraps PerformanceTracker with higher-level business logic
    for dashboard consumption.
    """

    def __init__(self, tracker: Optional[PerformanceTracker] = None):
        """Initialize service.

        Args:
            tracker: PerformanceTracker instance, or None to create default
        """
        self.tracker = tracker or PerformanceTracker()

    def get_performance_overview(self, days_back: int = 7) -> Dict:
        """Get high-level performance overview.

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with overview statistics
        """
        all_stats = self.tracker.get_all_routes_stats(days_back)

        if not all_stats:
            return {
                "total_routes": 0,
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "cache_hit_rate": 0,
                "slowest_route": None,
            }

        # Aggregate across all routes
        total_requests = sum(s["count"] for s in all_stats)

        # Weighted average response time
        weighted_avg = sum(s["avg_ms"] * s["count"] for s in all_stats) / total_requests if total_requests > 0 else 0

        # Weighted P95
        weighted_p95 = sum(s["p95_ms"] * s["count"] for s in all_stats) / total_requests if total_requests > 0 else 0

        # Weighted cache hit rate
        weighted_cache_rate = (
            sum(s["cache_hit_rate"] * s["count"] for s in all_stats) / total_requests if total_requests > 0 else 0
        )

        # Slowest route
        slowest = max(all_stats, key=lambda x: x["p95_ms"]) if all_stats else None

        return {
            "total_routes": len(all_stats),
            "total_requests": total_requests,
            "avg_response_time_ms": round(weighted_avg, 2),
            "p95_response_time_ms": round(weighted_p95, 2),
            "cache_hit_rate": round(weighted_cache_rate, 2),
            "slowest_route": slowest["route"] if slowest else None,
        }

    def get_slow_routes(self, limit: int = 10, days_back: int = 7) -> List[Dict]:
        """Get slowest routes with performance details.

        Args:
            limit: Number of routes to return
            days_back: Number of days to analyze

        Returns:
            List of route performance dictionaries with severity levels
        """
        slow_routes = self.tracker.get_slowest_routes(limit, days_back)

        # Add severity level based on P95
        for route_stats in slow_routes:
            p95 = route_stats["p95_ms"]

            if p95 < 100:
                severity = "good"
                color = "#10b981"  # green
            elif p95 < 500:
                severity = "warning"
                color = "#f59e0b"  # amber
            elif p95 < 1000:
                severity = "slow"
                color = "#ef4444"  # red
            else:
                severity = "critical"
                color = "#991b1b"  # dark red

            route_stats["severity"] = severity
            route_stats["color"] = color

        return slow_routes

    def get_route_performance_trend(self, route: Optional[str] = None, days_back: int = 7) -> Dict:
        """Get performance trend data for charting.

        Args:
            route: Route path, or None for all routes
            days_back: Number of days to analyze

        Returns:
            Dictionary with timestamps and metrics for Plotly charts
        """
        hourly_data = self.tracker.get_hourly_metrics(route, days_back)

        # Format for Plotly
        return {
            "timestamps": hourly_data["timestamps"],
            "avg_latency": hourly_data["avg_ms"],
            "p95_latency": hourly_data["p95_ms"],
            "cache_hit_rate": hourly_data["cache_hit_rate"],
        }

    def get_cache_effectiveness(self, days_back: int = 7) -> Dict:
        """Analyze cache effectiveness across routes.

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with cache statistics
        """
        all_stats = self.tracker.get_all_routes_stats(days_back)

        if not all_stats:
            return {
                "overall_hit_rate": 0,
                "high_hit_rate_routes": [],
                "low_hit_rate_routes": [],
                "no_cache_routes": [],
            }

        # Calculate overall hit rate
        total_requests = sum(s["count"] for s in all_stats)
        weighted_hit_rate = (
            sum(s["cache_hit_rate"] * s["count"] for s in all_stats) / total_requests if total_requests > 0 else 0
        )

        # Categorize routes
        high_hit_rate = [s for s in all_stats if s["cache_hit_rate"] >= 70]
        low_hit_rate = [s for s in all_stats if 0 < s["cache_hit_rate"] < 70]
        no_cache = [s for s in all_stats if s["cache_hit_rate"] == 0]

        return {
            "overall_hit_rate": round(weighted_hit_rate, 2),
            "high_hit_rate_routes": high_hit_rate,
            "low_hit_rate_routes": low_hit_rate,
            "no_cache_routes": no_cache,
        }

    def get_route_comparison(self, days_back: int = 7) -> List[Dict]:
        """Get comparative data for all routes.

        Args:
            days_back: Number of days to analyze

        Returns:
            List of route statistics for comparison charts
        """
        all_stats = self.tracker.get_all_routes_stats(days_back)

        # Sort by request count (most popular first)
        all_stats.sort(key=lambda x: x["count"], reverse=True)

        # Add percentile rankings
        for idx, route_stats in enumerate(all_stats):
            route_stats["popularity_rank"] = idx + 1

        return all_stats

    def get_performance_health_score(self, days_back: int = 7) -> Dict:
        """Calculate overall performance health score (0-100).

        Scoring factors:
        - P95 latency (40%)
        - Cache hit rate (30%)
        - Error rate (30%)

        Args:
            days_back: Number of days to analyze

        Returns:
            Dictionary with score and breakdown
        """
        overview = self.get_performance_overview(days_back)

        # P95 latency score (lower is better)
        # < 100ms = 100 points
        # 100-500ms = linear 100-70
        # 500-1000ms = linear 70-30
        # > 1000ms = 0 points
        p95 = overview["p95_response_time_ms"]
        if p95 < 100:
            latency_score = 100
        elif p95 < 500:
            latency_score = 100 - ((p95 - 100) / 400 * 30)
        elif p95 < 1000:
            latency_score = 70 - ((p95 - 500) / 500 * 40)
        else:
            latency_score = max(0, 30 - ((p95 - 1000) / 1000 * 30))

        # Cache hit rate score (higher is better)
        cache_score = overview["cache_hit_rate"]

        # TODO: Add error rate when we track errors
        # For now, assume no errors = 100
        error_score = 100

        # Weighted average
        total_score = (latency_score * 0.4) + (cache_score * 0.3) + (error_score * 0.3)

        return {
            "total_score": round(total_score, 1),
            "latency_score": round(latency_score, 1),
            "cache_score": round(cache_score, 1),
            "error_score": round(error_score, 1),
            "grade": self._score_to_grade(total_score),
        }

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade.

        Args:
            score: Score 0-100

        Returns:
            Letter grade (A+ to F)
        """
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def rotate_old_data(self, days_to_keep: int = 90) -> int:
        """Delete old performance data.

        Args:
            days_to_keep: Number of days to retain

        Returns:
            Number of records deleted
        """
        return self.tracker.rotate_old_metrics(days_to_keep)

    def get_storage_info(self) -> Dict:
        """Get storage information.

        Returns:
            Dictionary with database size and record count
        """
        size_info = self.tracker.get_database_size()
        record_count = self.tracker.get_metrics_count()

        return {
            "database_size": size_info["human_readable"],
            "database_size_bytes": size_info["bytes"],
            "total_records": record_count,
        }
