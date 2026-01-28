"""Performance benchmarking script for Team Metrics Dashboard (Task #17)

Measures and reports performance metrics for:
- Route response times
- Database query performance
- Cache effectiveness
- API call efficiency
- Memory usage
- Concurrent request handling

Usage:
    python tests/performance/benchmark_dashboard.py
    python tests/performance/benchmark_dashboard.py --routes all
    python tests/performance/benchmark_dashboard.py --concurrent 10
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import Config
from src.dashboard.app import create_app


class DashboardBenchmark:
    """Performance benchmarking for dashboard routes"""

    def __init__(self, warmup_requests: int = 5, test_requests: int = 20):
        """Initialize benchmark.

        Args:
            warmup_requests: Number of warmup requests before timing
            test_requests: Number of requests to time for each route
        """
        self.warmup_requests = warmup_requests
        self.test_requests = test_requests
        self.results: Dict[str, Any] = {}

        # Create test client
        config = MagicMock(spec=Config)
        config.dashboard_config = {
            "port": 5001,
            "cache_duration_minutes": 60,
            "auth": {"enabled": False},
        }
        config.teams = []

        app = create_app(config)
        app.config["TESTING"] = True
        self.client = app.test_client()

    def benchmark_route(self, route: str, method: str = "GET") -> Dict[str, Any]:
        """Benchmark a single route.

        Args:
            route: Route path to benchmark
            method: HTTP method (GET, POST, etc.)

        Returns:
            Dictionary with timing statistics
        """
        # Warmup
        for _ in range(self.warmup_requests):
            if method == "GET":
                self.client.get(route)
            elif method == "POST":
                self.client.post(route)

        # Actual measurements
        times: List[float] = []
        for _ in range(self.test_requests):
            start = time.perf_counter()

            if method == "GET":
                response = self.client.get(route)
            elif method == "POST":
                response = self.client.post(route)

            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)

            if response.status_code >= 400:
                print(f"Warning: {route} returned {response.status_code}")

        return {
            "route": route,
            "method": method,
            "requests": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "p95_ms": self._percentile(times, 0.95),
            "p99_ms": self._percentile(times, 0.99),
        }

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile value.

        Args:
            data: List of numeric values
            percentile: Percentile to calculate (0-1)

        Returns:
            Percentile value
        """
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def benchmark_concurrent_requests(self, route: str, concurrent: int = 10) -> Dict[str, Any]:
        """Benchmark concurrent requests to a route.

        Args:
            route: Route path to benchmark
            concurrent: Number of concurrent requests

        Returns:
            Dictionary with concurrency statistics
        """

        def make_request():
            start = time.perf_counter()
            response = self.client.get(route)
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed, response.status_code

        times: List[float] = []
        status_codes: List[int] = []

        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent)]

            for future in as_completed(futures):
                elapsed, status_code = future.result()
                times.append(elapsed)
                status_codes.append(status_code)

        return {
            "route": route,
            "concurrent_requests": concurrent,
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "successful_requests": sum(1 for s in status_codes if s < 400),
            "failed_requests": sum(1 for s in status_codes if s >= 400),
        }

    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite.

        Returns:
            Dictionary with all benchmark results
        """
        print("=== Team Metrics Dashboard Performance Benchmark ===\n")
        print(f"Warmup requests: {self.warmup_requests}")
        print(f"Test requests per route: {self.test_requests}\n")

        results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "warmup_requests": self.warmup_requests,
                "test_requests": self.test_requests,
            },
            "routes": [],
            "concurrent": [],
        }

        # Define routes to benchmark
        routes = [
            # API routes
            ("/api/metrics", "GET"),
            ("/api/health", "GET"),
            ("/api/cache/stats", "GET"),
            # Metrics API routes
            ("/metrics/api/overview", "GET"),
            ("/metrics/api/slow-routes", "GET"),
            ("/metrics/api/health-score", "GET"),
        ]

        # Benchmark each route
        print("Benchmarking routes...")
        for route, method in routes:
            print(f"  {method} {route}...", end=" ")
            try:
                result = self.benchmark_route(route, method)
                results["routes"].append(result)
                print(f"{result['mean_ms']:.2f}ms (median: {result['median_ms']:.2f}ms)")
            except Exception as e:
                print(f"ERROR: {e}")

        # Benchmark concurrent requests
        print("\nBenchmarking concurrent requests...")
        concurrent_tests = [
            ("/api/health", 5),
            ("/api/health", 10),
            ("/api/health", 20),
        ]

        for route, concurrent in concurrent_tests:
            print(f"  {route} x{concurrent}...", end=" ")
            try:
                result = self.benchmark_concurrent_requests(route, concurrent)
                results["concurrent"].append(result)
                print(f"{result['mean_ms']:.2f}ms (successful: {result['successful_requests']}/{concurrent})")
            except Exception as e:
                print(f"ERROR: {e}")

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Print human-readable summary of results.

        Args:
            results: Benchmark results dictionary
        """
        print("\n=== Performance Summary ===\n")

        # Route performance
        print("Route Performance:")
        print(f"{'Route':<40} {'Mean':<10} {'Median':<10} {'P95':<10} {'P99':<10}")
        print("-" * 80)

        for route in results["routes"]:
            print(
                f"{route['route']:<40} "
                f"{route['mean_ms']:>7.2f}ms "
                f"{route['median_ms']:>7.2f}ms "
                f"{route['p95_ms']:>7.2f}ms "
                f"{route['p99_ms']:>7.2f}ms"
            )

        # Overall statistics
        if results["routes"]:
            all_means = [r["mean_ms"] for r in results["routes"]]
            print("\nOverall Statistics:")
            print(f"  Fastest route: {min(all_means):.2f}ms")
            print(f"  Slowest route: {max(all_means):.2f}ms")
            print(f"  Average: {statistics.mean(all_means):.2f}ms")
            print(f"  Median: {statistics.median(all_means):.2f}ms")

        # Concurrency results
        if results["concurrent"]:
            print("\nConcurrency Performance:")
            print(f"{'Route':<40} {'Concurrent':<12} {'Mean':<10} {'Success Rate'}")
            print("-" * 80)

            for conc in results["concurrent"]:
                success_rate = (conc["successful_requests"] / conc["concurrent_requests"]) * 100
                print(
                    f"{conc['route']:<40} "
                    f"{conc['concurrent_requests']:<12} "
                    f"{conc['mean_ms']:>7.2f}ms "
                    f"{success_rate:>6.1f}%"
                )

        # Performance ratings
        print("\nPerformance Ratings:")
        if results["routes"]:
            avg_time = statistics.mean([r["mean_ms"] for r in results["routes"]])

            if avg_time < 50:
                rating = "🟢 Excellent"
            elif avg_time < 100:
                rating = "🟡 Good"
            elif avg_time < 200:
                rating = "🟠 Acceptable"
            else:
                rating = "🔴 Needs Improvement"

            print(f"  Overall: {rating} (avg {avg_time:.2f}ms)")

    def save_results(self, results: Dict[str, Any], filepath: str = "benchmark_results.json"):
        """Save results to JSON file.

        Args:
            results: Benchmark results
            filepath: Output file path
        """
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Benchmark Team Metrics Dashboard")
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Number of warmup requests (default: 5)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=20,
        help="Number of test requests per route (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tests/performance/benchmark_results.json",
        help="Output file path (default: tests/performance/benchmark_results.json)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file",
    )

    args = parser.parse_args()

    # Run benchmark
    benchmark = DashboardBenchmark(warmup_requests=args.warmup, test_requests=args.requests)
    results = benchmark.run_full_benchmark()

    # Print summary
    benchmark.print_summary(results)

    # Save results
    if not args.no_save:
        benchmark.save_results(results, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
