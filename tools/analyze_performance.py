#!/usr/bin/env python3
"""Performance log analyzer.

Parses performance logs from the dashboard and collectors to identify bottlenecks
and generate performance reports with percentiles and histograms.

Usage:
    python tools/analyze_performance.py logs/team_metrics.log
    python tools/analyze_performance.py logs/team_metrics.log --type route
    python tools/analyze_performance.py logs/team_metrics.log --percentiles 50 90 95 99
    python tools/analyze_performance.py logs/team_metrics.log --histogram
    python tools/analyze_performance.py logs/team_metrics.log --top 5
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def parse_log_file(log_file_path: str) -> List[Dict[str, Any]]:
    """Parse performance logs from log file.

    Args:
        log_file_path: Path to log file

    Returns:
        List of performance log entries (dicts)
    """
    perf_entries = []

    try:
        with open(log_file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                # Try to parse as JSON (structured logging)
                try:
                    entry = json.loads(line)
                    # Check if this is a performance log entry
                    if isinstance(entry, dict) and entry.get("type") in ["route", "api_call", "operation"]:
                        perf_entries.append(entry)
                except json.JSONDecodeError:
                    # Try to parse plain text format: [PERF] ...
                    if "[PERF]" in line:
                        # Extract key information from plain text
                        # Format: [PERF] Type: name duration=XXXms ...
                        entry = {"raw": line, "type": "unknown"}
                        if "route=" in line:
                            entry["type"] = "route"
                            entry["route"] = extract_value(line, "route=")
                        elif "operation=" in line:
                            entry["type"] = "operation"
                            entry["operation"] = extract_value(line, "operation=")
                        elif "API call" in line:
                            entry["type"] = "api_call"

                        duration_str = extract_value(line, "duration=")
                        if duration_str:
                            try:
                                entry["duration_ms"] = float(duration_str.replace("ms", ""))
                            except ValueError:
                                pass

                        if "duration_ms" in entry:
                            perf_entries.append(entry)

    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file_path}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied reading: {log_file_path}", file=sys.stderr)
        sys.exit(1)

    return perf_entries


def extract_value(line: str, prefix: str) -> str:
    """Extract value from log line after prefix."""
    try:
        start = line.index(prefix) + len(prefix)
        # Find the end (space or end of line)
        end = line.find(" ", start)
        if end == -1:
            end = len(line)
        return line[start:end]
    except ValueError:
        return ""


def group_by_name(entries: List[Dict[str, Any]], entry_type: str = None) -> Dict[str, List[float]]:
    """Group duration values by name (route/operation/api_call).

    Args:
        entries: List of log entries
        entry_type: Filter by type ('route', 'api_call', 'operation', or None for all)

    Returns:
        Dict mapping names to lists of durations
    """
    grouped = defaultdict(list)

    for entry in entries:
        if entry_type and entry.get("type") != entry_type:
            continue

        duration = entry.get("duration_ms")
        if duration is None:
            continue

        # Get the name based on type
        name = entry.get("route") or entry.get("operation") or entry.get("api_call") or "unknown"
        grouped[name].append(duration)

    return dict(grouped)


def calculate_percentiles(values: List[float], percentiles: List[int]) -> Dict[int, float]:
    """Calculate percentiles for a list of values.

    Args:
        values: List of numeric values
        percentiles: List of percentile values (e.g., [50, 95, 99])

    Returns:
        Dict mapping percentile to value
    """
    if not values:
        return {p: 0.0 for p in percentiles}

    sorted_values = sorted(values)
    results = {}

    for p in percentiles:
        if p == 0:
            results[p] = sorted_values[0]
        elif p == 100:
            results[p] = sorted_values[-1]
        else:
            index = (p / 100.0) * (len(sorted_values) - 1)
            lower = int(index)
            upper = lower + 1

            if upper >= len(sorted_values):
                results[p] = sorted_values[-1]
            else:
                # Linear interpolation
                fraction = index - lower
                results[p] = sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])

    return results


def generate_histogram(values: List[float], bins: int = 10) -> List[tuple]:
    """Generate histogram data.

    Args:
        values: List of numeric values
        bins: Number of histogram bins

    Returns:
        List of (bin_start, bin_end, count) tuples
    """
    if not values:
        return []

    min_val = min(values)
    max_val = max(values)
    bin_width = (max_val - min_val) / bins

    if bin_width == 0:
        return [(min_val, max_val, len(values))]

    histogram = []
    for i in range(bins):
        bin_start = min_val + i * bin_width
        bin_end = bin_start + bin_width
        count = sum(1 for v in values if bin_start <= v < bin_end or (i == bins - 1 and v == bin_end))
        histogram.append((bin_start, bin_end, count))

    return histogram


def print_report(
    grouped_data: Dict[str, List[float]], percentiles: List[int], show_histogram: bool = False, top_n: int = None
):
    """Print performance analysis report.

    Args:
        grouped_data: Dict mapping names to durations
        percentiles: List of percentiles to calculate
        show_histogram: Whether to show histogram
        top_n: Only show top N slowest operations
    """
    if not grouped_data:
        print("No performance data found in log file.")
        return

    # Calculate summary statistics for each operation
    summaries = []
    for name, durations in grouped_data.items():
        summary = {
            "name": name,
            "count": len(durations),
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "min": min(durations),
            "max": max(durations),
            "percentiles": calculate_percentiles(durations, percentiles),
        }
        summaries.append(summary)

    # Sort by mean duration (slowest first)
    summaries.sort(key=lambda x: x["mean"], reverse=True)

    # Limit to top N if requested
    if top_n:
        summaries = summaries[:top_n]

    # Print report
    print("=" * 80)
    print("PERFORMANCE ANALYSIS REPORT")
    print("=" * 80)
    print()

    for summary in summaries:
        print(f"Operation: {summary['name']}")
        print(f"  Count:   {summary['count']}")
        print(f"  Mean:    {summary['mean']:.2f} ms")
        print(f"  Median:  {summary['median']:.2f} ms")
        print(f"  Min:     {summary['min']:.2f} ms")
        print(f"  Max:     {summary['max']:.2f} ms")
        print(f"  Percentiles:")
        for p, value in sorted(summary["percentiles"].items()):
            print(f"    p{p}:    {value:.2f} ms")

        if show_histogram:
            print(f"  Histogram:")
            hist = generate_histogram(grouped_data[summary["name"]], bins=10)
            max_count = max(count for _, _, count in hist)
            for bin_start, bin_end, count in hist:
                bar_width = int(40 * count / max_count) if max_count > 0 else 0
                bar = "█" * bar_width
                print(f"    {bin_start:7.1f} - {bin_end:7.1f} ms: {bar} ({count})")

        print()


def print_summary(entries: List[Dict[str, Any]]):
    """Print overall summary of performance data."""
    route_count = sum(1 for e in entries if e.get("type") == "route")
    api_count = sum(1 for e in entries if e.get("type") == "api_call")
    operation_count = sum(1 for e in entries if e.get("type") == "operation")

    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"Total performance entries: {len(entries)}")
    print(f"  Routes:       {route_count}")
    print(f"  API calls:    {api_count}")
    print(f"  Operations:   {operation_count}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze performance logs from team metrics dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all performance data
  python tools/analyze_performance.py logs/team_metrics.log

  # Show only routes
  python tools/analyze_performance.py logs/team_metrics.log --type route

  # Show custom percentiles
  python tools/analyze_performance.py logs/team_metrics.log --percentiles 50 90 95 99

  # Show histograms
  python tools/analyze_performance.py logs/team_metrics.log --histogram

  # Show top 5 slowest operations
  python tools/analyze_performance.py logs/team_metrics.log --top 5
        """,
    )

    parser.add_argument("log_file", help="Path to log file")
    parser.add_argument("--type", choices=["route", "api_call", "operation"], help="Filter by entry type")
    parser.add_argument(
        "--percentiles", type=int, nargs="+", default=[50, 95, 99], help="Percentiles to calculate (default: 50 95 99)"
    )
    parser.add_argument("--histogram", action="store_true", help="Show histogram for each operation")
    parser.add_argument("--top", type=int, metavar="N", help="Show only top N slowest operations")

    args = parser.parse_args()

    # Parse log file
    entries = parse_log_file(args.log_file)

    if not entries:
        print(f"No performance data found in {args.log_file}")
        print("Ensure the dashboard is running with performance monitoring enabled.")
        sys.exit(1)

    # Print summary
    print_summary(entries)

    # Group by name and generate report
    grouped_data = group_by_name(entries, args.type)
    print_report(grouped_data, args.percentiles, args.histogram, args.top)


if __name__ == "__main__":
    main()
