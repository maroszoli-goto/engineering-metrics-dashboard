"""Tests for PerformanceMetricsService."""

import os
import tempfile

import pytest

from src.dashboard.services.performance_metrics_service import PerformanceMetricsService
from src.utils.performance_tracker import PerformanceTracker


class TestPerformanceMetricsService:
    """Tests for PerformanceMetricsService class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def tracker(self, temp_db):
        """Create tracker with temporary database."""
        return PerformanceTracker(temp_db)

    @pytest.fixture
    def service(self, tracker):
        """Create service with test tracker."""
        return PerformanceMetricsService(tracker)

    def test_init_default_tracker(self):
        """Test initialization with default tracker."""
        service = PerformanceMetricsService()
        assert service.tracker is not None

    def test_init_custom_tracker(self, tracker):
        """Test initialization with custom tracker."""
        service = PerformanceMetricsService(tracker)
        assert service.tracker == tracker

    def test_get_performance_overview_empty(self, service):
        """Test overview with no metrics."""
        overview = service.get_performance_overview(days_back=7)

        assert overview["total_routes"] == 0
        assert overview["total_requests"] == 0
        assert overview["avg_response_time_ms"] == 0
        assert overview["slowest_route"] is None

    def test_get_performance_overview_with_data(self, service, tracker):
        """Test overview with metrics data."""
        # Record metrics for multiple routes
        tracker.record_metric("/route1", "GET", 100, 200, cache_hit=True)
        tracker.record_metric("/route1", "GET", 150, 200, cache_hit=False)
        tracker.record_metric("/route2", "GET", 200, 200, cache_hit=True)

        overview = service.get_performance_overview(days_back=7)

        assert overview["total_routes"] == 2
        assert overview["total_requests"] == 3
        assert overview["avg_response_time_ms"] > 0
        assert overview["p95_response_time_ms"] > 0
        assert overview["slowest_route"] in ["/route1", "/route2"]

    def test_get_slow_routes(self, service, tracker):
        """Test getting slowest routes with severity levels."""
        # Fast route
        tracker.record_metric("/fast", "GET", 50, 200)

        # Warning route
        tracker.record_metric("/warning", "GET", 250, 200)

        # Slow route
        tracker.record_metric("/slow", "GET", 700, 200)

        # Critical route
        tracker.record_metric("/critical", "GET", 1500, 200)

        slow_routes = service.get_slow_routes(limit=10, days_back=7)

        assert len(slow_routes) == 4

        # Check severity assignment
        critical = [r for r in slow_routes if r["route"] == "/critical"][0]
        assert critical["severity"] == "critical"
        assert critical["color"] == "#991b1b"

        slow = [r for r in slow_routes if r["route"] == "/slow"][0]
        assert slow["severity"] == "slow"

        warning = [r for r in slow_routes if r["route"] == "/warning"][0]
        assert warning["severity"] == "warning"

        fast = [r for r in slow_routes if r["route"] == "/fast"][0]
        assert fast["severity"] == "good"

    def test_get_route_performance_trend(self, service, tracker):
        """Test getting performance trend data."""
        # Record some metrics
        for i in range(10):
            tracker.record_metric("/test", "GET", 100 + i * 10, 200, cache_hit=(i % 2 == 0))

        trend = service.get_route_performance_trend("/test", days_back=7)

        assert "timestamps" in trend
        assert "avg_latency" in trend
        assert "p95_latency" in trend
        assert "cache_hit_rate" in trend

    def test_get_cache_effectiveness(self, service, tracker):
        """Test cache effectiveness analysis."""
        # High hit rate route (80%)
        for i in range(10):
            tracker.record_metric("/high", "GET", 100, 200, cache_hit=(i < 8))

        # Low hit rate route (40%)
        for i in range(10):
            tracker.record_metric("/low", "GET", 100, 200, cache_hit=(i < 4))

        # No cache route
        for i in range(10):
            tracker.record_metric("/none", "GET", 100, 200, cache_hit=False)

        cache_data = service.get_cache_effectiveness(days_back=7)

        assert cache_data["overall_hit_rate"] > 0
        assert len(cache_data["high_hit_rate_routes"]) == 1
        assert len(cache_data["low_hit_rate_routes"]) == 1
        assert len(cache_data["no_cache_routes"]) == 1

    def test_get_cache_effectiveness_empty(self, service):
        """Test cache effectiveness with no data."""
        cache_data = service.get_cache_effectiveness(days_back=7)

        assert cache_data["overall_hit_rate"] == 0
        assert cache_data["high_hit_rate_routes"] == []
        assert cache_data["low_hit_rate_routes"] == []
        assert cache_data["no_cache_routes"] == []

    def test_get_route_comparison(self, service, tracker):
        """Test route comparison with popularity ranking."""
        # Different request counts
        for i in range(20):
            tracker.record_metric("/popular", "GET", 100, 200)

        for i in range(5):
            tracker.record_metric("/unpopular", "GET", 100, 200)

        comparison = service.get_route_comparison(days_back=7)

        assert len(comparison) == 2
        # Most popular first
        assert comparison[0]["route"] == "/popular"
        assert comparison[0]["popularity_rank"] == 1
        assert comparison[1]["route"] == "/unpopular"
        assert comparison[1]["popularity_rank"] == 2

    def test_get_performance_health_score_perfect(self, service, tracker):
        """Test health score with perfect performance."""
        # Very fast responses, 100% cache hit
        for i in range(10):
            tracker.record_metric("/test", "GET", 50, 200, cache_hit=True)

        health = service.get_performance_health_score(days_back=7)

        assert health["total_score"] >= 90
        assert health["latency_score"] == 100  # < 100ms
        assert health["cache_score"] == 100  # 100% hit rate
        assert health["grade"] in ["A+", "A"]

    def test_get_performance_health_score_poor(self, service, tracker):
        """Test health score with poor performance."""
        # Slow responses, 0% cache hit
        for i in range(10):
            tracker.record_metric("/test", "GET", 2000, 200, cache_hit=False)

        health = service.get_performance_health_score(days_back=7)

        assert health["total_score"] < 50
        assert health["latency_score"] < 50  # > 1000ms
        assert health["cache_score"] == 0  # 0% hit rate
        assert health["grade"] == "F"

    def test_score_to_grade(self, service):
        """Test score to grade conversion."""
        assert service._score_to_grade(97) == "A+"
        assert service._score_to_grade(92) == "A"
        assert service._score_to_grade(87) == "B+"
        assert service._score_to_grade(82) == "B"
        assert service._score_to_grade(77) == "C+"
        assert service._score_to_grade(72) == "C"
        assert service._score_to_grade(65) == "D"
        assert service._score_to_grade(50) == "F"

    def test_rotate_old_data(self, service, tracker):
        """Test rotating old performance data."""
        import sqlite3
        from datetime import datetime, timedelta

        # Insert old data
        old_timestamp = (datetime.now() - timedelta(days=100)).isoformat()
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO route_metrics
                (timestamp, route, method, duration_ms, status_code, cache_hit)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (old_timestamp, "/old", "GET", 100, 200, 0),
            )
            conn.commit()

        # Insert recent data
        tracker.record_metric("/recent", "GET", 100, 200)

        # Rotate
        deleted = service.rotate_old_data(days_to_keep=90)

        assert deleted == 1

    def test_get_storage_info(self, service, tracker):
        """Test getting storage information."""
        # Record some metrics
        for i in range(50):
            tracker.record_metric(f"/route{i}", "GET", 100, 200)

        storage = service.get_storage_info()

        assert "database_size" in storage
        assert "database_size_bytes" in storage
        assert "total_records" in storage
        assert storage["total_records"] == 50
        assert storage["database_size_bytes"] > 0

    def test_weighted_average_calculation(self, service, tracker):
        """Test that weighted averages are calculated correctly."""
        # Route 1: 10 fast requests (100ms)
        for i in range(10):
            tracker.record_metric("/route1", "GET", 100, 200)

        # Route 2: 1 slow request (1000ms)
        tracker.record_metric("/route2", "GET", 1000, 200)

        overview = service.get_performance_overview(days_back=7)

        # Weighted avg should be closer to 100 than 1000
        # (10*100 + 1*1000) / 11 = 181.8
        assert 175 <= overview["avg_response_time_ms"] <= 190

    def test_cache_effectiveness_weighted(self, service, tracker):
        """Test weighted cache hit rate calculation."""
        # Route 1: 100 requests, 90% hit rate
        for i in range(100):
            tracker.record_metric("/route1", "GET", 100, 200, cache_hit=(i < 90))

        # Route 2: 10 requests, 0% hit rate
        for i in range(10):
            tracker.record_metric("/route2", "GET", 100, 200, cache_hit=False)

        cache_data = service.get_cache_effectiveness(days_back=7)

        # Weighted: (100*90 + 10*0) / 110 = 81.8%
        assert 80 <= cache_data["overall_hit_rate"] <= 83
