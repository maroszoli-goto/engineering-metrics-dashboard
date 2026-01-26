"""Tests for PerformanceTracker."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from src.utils.performance_tracker import PerformanceTracker


class TestPerformanceTracker:
    """Tests for PerformanceTracker class."""

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

    def test_init_creates_database(self, temp_db):
        """Test that initialization creates database file."""
        tracker = PerformanceTracker(temp_db)
        assert os.path.exists(temp_db)

    def test_record_metric(self, tracker):
        """Test recording a single metric."""
        tracker.record_metric(
            route="/team/backend",
            method="GET",
            duration_ms=150.5,
            status_code=200,
            cache_hit=True,
        )

        metrics = tracker.get_route_metrics("/team/backend", days_back=1)
        assert len(metrics) == 1
        assert metrics[0][1] == "/team/backend"
        assert metrics[0][2] == "GET"
        assert metrics[0][3] == 150.5
        assert metrics[0][4] == 200
        assert metrics[0][5] == 1  # cache_hit

    def test_record_multiple_metrics(self, tracker):
        """Test recording multiple metrics."""
        for i in range(5):
            tracker.record_metric(
                route="/team/backend",
                method="GET",
                duration_ms=100 + i * 10,
                status_code=200,
            )

        metrics = tracker.get_route_metrics("/team/backend", days_back=1)
        assert len(metrics) == 5

    def test_get_route_stats(self, tracker):
        """Test getting aggregated route statistics."""
        # Record metrics with known values
        durations = [100, 150, 200, 250, 300]
        for duration in durations:
            tracker.record_metric(
                route="/team/backend",
                method="GET",
                duration_ms=duration,
                status_code=200,
                cache_hit=(duration < 200),
            )

        stats = tracker.get_route_stats("/team/backend", days_back=1)

        assert stats["route"] == "/team/backend"
        assert stats["count"] == 5
        assert stats["avg_ms"] == 200.0  # (100+150+200+250+300)/5
        assert stats["p50_ms"] == 200.0  # Median
        assert stats["cache_hit_rate"] == 40.0  # 2 out of 5

    def test_get_route_stats_empty(self, tracker):
        """Test getting stats for route with no metrics."""
        stats = tracker.get_route_stats("/nonexistent", days_back=1)

        assert stats["count"] == 0
        assert stats["avg_ms"] == 0
        assert stats["p50_ms"] == 0

    def test_get_all_routes_stats(self, tracker):
        """Test getting stats for all routes."""
        # Record metrics for multiple routes
        tracker.record_metric("/team/backend", "GET", 100, 200)
        tracker.record_metric("/team/frontend", "GET", 200, 200)
        tracker.record_metric("/person/john", "GET", 150, 200)

        all_stats = tracker.get_all_routes_stats(days_back=1)

        assert len(all_stats) == 3
        routes = [s["route"] for s in all_stats]
        assert "/team/backend" in routes
        assert "/team/frontend" in routes
        assert "/person/john" in routes

    def test_get_slowest_routes(self, tracker):
        """Test getting slowest routes by P95."""
        # Record metrics with different speeds
        tracker.record_metric("/fast", "GET", 50, 200)
        tracker.record_metric("/medium", "GET", 150, 200)
        tracker.record_metric("/slow", "GET", 500, 200)

        slowest = tracker.get_slowest_routes(limit=2, days_back=1)

        assert len(slowest) <= 2
        # Slowest first
        assert slowest[0]["p95_ms"] >= slowest[1]["p95_ms"]

    def test_get_hourly_metrics(self, tracker):
        """Test getting hourly aggregated metrics."""
        # Record several metrics
        for i in range(10):
            tracker.record_metric(
                "/test",
                "GET",
                100 + i * 10,
                200,
                cache_hit=(i % 2 == 0),
            )

        hourly = tracker.get_hourly_metrics("/test", days_back=1)

        assert "timestamps" in hourly
        assert "avg_ms" in hourly
        assert "p95_ms" in hourly
        assert "cache_hit_rate" in hourly
        assert len(hourly["timestamps"]) > 0

    def test_rotate_old_metrics(self, tracker):
        """Test rotating old metrics."""
        # Record current metric
        tracker.record_metric("/test", "GET", 100, 200)

        # Manually insert old metric (simulate old data)
        import sqlite3

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

        # Should have 2 metrics total
        assert tracker.get_metrics_count() == 2

        # Rotate, keeping only 90 days
        deleted = tracker.rotate_old_metrics(days_to_keep=90)

        assert deleted == 1
        assert tracker.get_metrics_count() == 1

    def test_get_database_size(self, tracker):
        """Test getting database size."""
        # Record some metrics
        for i in range(100):
            tracker.record_metric(f"/route{i}", "GET", 100, 200)

        size_info = tracker.get_database_size()

        assert "bytes" in size_info
        assert "human_readable" in size_info
        assert size_info["bytes"] > 0
        assert "KB" in size_info["human_readable"] or "MB" in size_info["human_readable"]

    def test_get_metrics_count(self, tracker):
        """Test getting total metrics count."""
        assert tracker.get_metrics_count() == 0

        for i in range(10):
            tracker.record_metric("/test", "GET", 100, 200)

        assert tracker.get_metrics_count() == 10

    def test_percentile_calculation(self, tracker):
        """Test P50/P95/P99 percentile calculations."""
        # Record 100 metrics with known distribution
        for i in range(1, 101):
            tracker.record_metric("/test", "GET", float(i), 200)

        stats = tracker.get_route_stats("/test", days_back=1)

        # P50 should be around 50
        assert 48 <= stats["p50_ms"] <= 52

        # P95 should be around 95
        assert 93 <= stats["p95_ms"] <= 97

        # P99 should be around 99
        assert 97 <= stats["p99_ms"] <= 101

    def test_cache_hit_rate_calculation(self, tracker):
        """Test cache hit rate calculation."""
        # 7 hits, 3 misses = 70%
        for i in range(10):
            tracker.record_metric(
                "/test",
                "GET",
                100,
                200,
                cache_hit=(i < 7),
            )

        stats = tracker.get_route_stats("/test", days_back=1)
        assert stats["cache_hit_rate"] == 70.0

    def test_days_back_filtering(self, tracker):
        """Test that days_back parameter filters correctly."""
        import sqlite3

        # Insert metric from 10 days ago
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
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

        # Insert recent metric
        tracker.record_metric("/recent", "GET", 100, 200)

        # Query last 7 days - should only get recent
        metrics_7d = tracker.get_route_metrics(None, days_back=7)
        routes = [m[1] for m in metrics_7d]
        assert "/recent" in routes
        assert "/old" not in routes

        # Query last 30 days - should get both
        metrics_30d = tracker.get_route_metrics(None, days_back=30)
        routes = [m[1] for m in metrics_30d]
        assert "/recent" in routes
        assert "/old" in routes

    def test_error_recording(self, tracker):
        """Test recording metrics with errors."""
        tracker.record_metric(
            route="/error",
            method="GET",
            duration_ms=100,
            status_code=500,
            error="Internal Server Error",
        )

        metrics = tracker.get_route_metrics("/error", days_back=1)
        assert len(metrics) == 1
        assert metrics[0][4] == 500  # status_code
