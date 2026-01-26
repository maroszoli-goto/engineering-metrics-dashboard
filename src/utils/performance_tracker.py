"""Performance metrics tracking with SQLite storage.

Stores route performance metrics for long-term analysis:
- Request duration
- Cache hit/miss rates
- HTTP status codes
- 90-day retention with automatic rotation
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PerformanceTracker:
    """Tracks and stores performance metrics in SQLite database.

    Stores metrics for routes and provides aggregation capabilities
    for P50/P95/P99 latency analysis and cache hit rate tracking.
    """

    def __init__(self, db_path: str = "logs/performance/metrics.db"):
        """Initialize performance tracker.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS route_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    route TEXT NOT NULL,
                    method TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    status_code INTEGER NOT NULL,
                    cache_hit INTEGER DEFAULT 0,
                    error TEXT
                )
            """)

            # Index for fast queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_route_timestamp
                ON route_metrics(route, timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON route_metrics(timestamp)
            """)

            conn.commit()

    def record_metric(
        self,
        route: str,
        method: str,
        duration_ms: float,
        status_code: int,
        cache_hit: bool = False,
        error: Optional[str] = None,
    ):
        """Record a performance metric.

        Args:
            route: Route path (e.g., "/team/<team_name>")
            method: HTTP method (GET, POST, etc.)
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
            cache_hit: Whether cache was hit
            error: Error message if any
        """
        timestamp = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO route_metrics
                (timestamp, route, method, duration_ms, status_code, cache_hit, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, route, method, duration_ms, status_code, int(cache_hit), error),
            )
            conn.commit()

    def get_route_metrics(
        self,
        route: Optional[str] = None,
        days_back: int = 7,
    ) -> List[Tuple]:
        """Get metrics for a specific route or all routes.

        Args:
            route: Route path, or None for all routes
            days_back: Number of days to look back

        Returns:
            List of tuples: (timestamp, route, method, duration_ms, status_code, cache_hit)
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if route:
                cursor.execute(
                    """
                    SELECT timestamp, route, method, duration_ms, status_code, cache_hit
                    FROM route_metrics
                    WHERE route = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    """,
                    (route, cutoff_date),
                )
            else:
                cursor.execute(
                    """
                    SELECT timestamp, route, method, duration_ms, status_code, cache_hit
                    FROM route_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    """,
                    (cutoff_date,),
                )

            return cursor.fetchall()

    def get_route_stats(self, route: str, days_back: int = 7) -> Dict:
        """Get aggregated statistics for a route.

        Args:
            route: Route path
            days_back: Number of days to look back

        Returns:
            Dictionary with P50, P95, P99, avg, count, cache_hit_rate
        """
        metrics = self.get_route_metrics(route, days_back)

        if not metrics:
            return {
                "route": route,
                "count": 0,
                "avg_ms": 0,
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "cache_hit_rate": 0,
            }

        # Extract durations and cache hits
        durations = [m[3] for m in metrics]  # duration_ms
        cache_hits = [m[5] for m in metrics]  # cache_hit

        # Sort for percentile calculations
        durations_sorted = sorted(durations)
        count = len(durations)

        # Calculate percentiles
        def percentile(data, p):
            if not data:
                return 0
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] * (1 - c) + data[f + 1] * c
            else:
                return data[f]

        p50 = percentile(durations_sorted, 0.50)
        p95 = percentile(durations_sorted, 0.95)
        p99 = percentile(durations_sorted, 0.99)
        avg = sum(durations) / count

        # Cache hit rate
        cache_hit_rate = (sum(cache_hits) / count * 100) if count > 0 else 0

        return {
            "route": route,
            "count": count,
            "avg_ms": round(avg, 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "cache_hit_rate": round(cache_hit_rate, 2),
        }

    def get_all_routes_stats(self, days_back: int = 7) -> List[Dict]:
        """Get statistics for all routes.

        Args:
            days_back: Number of days to look back

        Returns:
            List of route statistics dictionaries
        """
        # Get unique routes
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT route
                FROM route_metrics
                WHERE timestamp >= ?
                """,
                (cutoff_date,),
            )
            routes = [row[0] for row in cursor.fetchall()]

        # Get stats for each route
        stats = []
        for route in routes:
            route_stats = self.get_route_stats(route, days_back)
            stats.append(route_stats)

        # Sort by average duration (slowest first)
        stats.sort(key=lambda x: x["avg_ms"], reverse=True)

        return stats

    def get_slowest_routes(self, limit: int = 10, days_back: int = 7) -> List[Dict]:
        """Get the slowest routes by P95 latency.

        Args:
            limit: Number of routes to return
            days_back: Number of days to look back

        Returns:
            List of route statistics dictionaries
        """
        all_stats = self.get_all_routes_stats(days_back)

        # Sort by P95 (worst case performance)
        all_stats.sort(key=lambda x: x["p95_ms"], reverse=True)

        return all_stats[:limit]

    def get_hourly_metrics(self, route: Optional[str] = None, days_back: int = 1) -> Dict[str, List]:
        """Get hourly aggregated metrics for charting.

        Args:
            route: Route path, or None for all routes
            days_back: Number of days to look back

        Returns:
            Dictionary with timestamps and corresponding metrics
        """
        metrics = self.get_route_metrics(route, days_back)

        # Group by hour
        hourly_data = {}

        for metric in metrics:
            timestamp_str, route_name, method, duration_ms, status_code, cache_hit = metric

            # Parse timestamp and round to hour
            dt = datetime.fromisoformat(timestamp_str)
            hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()

            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    "durations": [],
                    "cache_hits": [],
                    "total": 0,
                }

            hourly_data[hour_key]["durations"].append(duration_ms)
            hourly_data[hour_key]["cache_hits"].append(cache_hit)
            hourly_data[hour_key]["total"] += 1

        # Calculate aggregates
        timestamps = []
        avg_durations = []
        p95_durations = []
        cache_hit_rates = []

        for hour_key in sorted(hourly_data.keys()):
            data = hourly_data[hour_key]
            durations = sorted(data["durations"])

            timestamps.append(hour_key)
            avg_durations.append(sum(durations) / len(durations))

            # P95
            p95_idx = int(len(durations) * 0.95)
            p95_durations.append(durations[p95_idx] if p95_idx < len(durations) else durations[-1])

            # Cache hit rate
            cache_rate = sum(data["cache_hits"]) / data["total"] * 100 if data["total"] > 0 else 0
            cache_hit_rates.append(cache_rate)

        return {
            "timestamps": timestamps,
            "avg_ms": avg_durations,
            "p95_ms": p95_durations,
            "cache_hit_rate": cache_hit_rates,
        }

    def rotate_old_metrics(self, days_to_keep: int = 90):
        """Delete metrics older than specified days.

        Args:
            days_to_keep: Number of days to retain
        """
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM route_metrics WHERE timestamp < ?",
                (cutoff_date,),
            )
            deleted = cursor.rowcount
            conn.commit()

        return deleted

    def get_database_size(self) -> Dict:
        """Get database size information.

        Returns:
            Dictionary with size in bytes and human-readable format
        """
        if not os.path.exists(self.db_path):
            return {"bytes": 0, "human_readable": "0 B"}

        size_bytes = os.path.getsize(self.db_path)

        # Human readable
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                human = f"{size_bytes:.2f} {unit}"
                break
            size_bytes /= 1024.0
        else:
            human = f"{size_bytes:.2f} TB"

        return {
            "bytes": os.path.getsize(self.db_path),
            "human_readable": human,
        }

    def get_metrics_count(self) -> int:
        """Get total number of metrics stored.

        Returns:
            Total count of metrics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM route_metrics")
            return cursor.fetchone()[0]
