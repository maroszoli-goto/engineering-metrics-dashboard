"""Tests for performance analysis tool."""

import json
import tempfile
from pathlib import Path

import pytest

from tools.analyze_performance import calculate_percentiles, generate_histogram, group_by_name, parse_log_file


class TestParseLogFile:
    """Tests for log file parsing."""

    def test_parse_json_logs(self, tmp_path):
        """Test parsing structured JSON logs."""
        log_file = tmp_path / "test.log"
        log_data = [
            {"type": "route", "route": "index", "duration_ms": 123.45, "status_code": 200},
            {"type": "api_call", "operation": "github_fetch", "duration_ms": 456.78, "success": True},
            {"type": "operation", "operation": "cache_load", "duration_ms": 12.34, "success": True},
        ]

        with open(log_file, "w") as f:
            for entry in log_data:
                f.write(json.dumps(entry) + "\n")

        entries = parse_log_file(str(log_file))

        assert len(entries) == 3
        assert entries[0]["type"] == "route"
        assert entries[0]["route"] == "index"
        assert entries[0]["duration_ms"] == 123.45

    def test_parse_plain_text_logs(self, tmp_path):
        """Test parsing plain text logs."""
        log_file = tmp_path / "test.log"
        with open(log_file, "w") as f:
            f.write("[PERF] Route timing route=index duration=123.45ms status=200\n")
            f.write("[PERF] API call: github_fetch duration=456.78ms\n")
            f.write("[PERF] Operation: cache_load duration=12.34ms\n")

        entries = parse_log_file(str(log_file))

        assert len(entries) == 3
        assert entries[0]["type"] == "route"
        assert entries[0]["route"] == "index"
        assert entries[0]["duration_ms"] == 123.45

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file."""
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        entries = parse_log_file(str(log_file))
        assert entries == []

    def test_parse_nonexistent_file(self, capsys):
        """Test parsing nonexistent file."""
        with pytest.raises(SystemExit) as exc:
            parse_log_file("/nonexistent/file.log")

        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err


class TestGroupByName:
    """Tests for grouping performance data."""

    def test_group_by_route(self):
        """Test grouping route entries."""
        entries = [
            {"type": "route", "route": "index", "duration_ms": 100},
            {"type": "route", "route": "index", "duration_ms": 150},
            {"type": "route", "route": "team_dashboard", "duration_ms": 200},
        ]

        grouped = group_by_name(entries, "route")

        assert len(grouped) == 2
        assert grouped["index"] == [100, 150]
        assert grouped["team_dashboard"] == [200]

    def test_group_by_api_call(self):
        """Test grouping API call entries."""
        entries = [
            {"type": "api_call", "operation": "github_fetch", "duration_ms": 300},
            {"type": "api_call", "operation": "github_fetch", "duration_ms": 350},
            {"type": "api_call", "operation": "jira_fetch", "duration_ms": 400},
        ]

        grouped = group_by_name(entries, "api_call")

        assert len(grouped) == 2
        assert grouped["github_fetch"] == [300, 350]
        assert grouped["jira_fetch"] == [400]

    def test_group_all_types(self):
        """Test grouping all entry types."""
        entries = [
            {"type": "route", "route": "index", "duration_ms": 100},
            {"type": "api_call", "operation": "fetch", "duration_ms": 200},
            {"type": "operation", "operation": "cache", "duration_ms": 50},
        ]

        grouped = group_by_name(entries)

        assert len(grouped) == 3
        assert grouped["index"] == [100]
        assert grouped["fetch"] == [200]
        assert grouped["cache"] == [50]

    def test_group_skips_missing_duration(self):
        """Test grouping skips entries without duration."""
        entries = [
            {"type": "route", "route": "index", "duration_ms": 100},
            {"type": "route", "route": "index"},  # Missing duration
        ]

        grouped = group_by_name(entries, "route")

        assert grouped["index"] == [100]


class TestCalculatePercentiles:
    """Tests for percentile calculation."""

    def test_calculate_percentiles_basic(self):
        """Test basic percentile calculation."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        percentiles = calculate_percentiles(values, [50, 95, 99])

        assert percentiles[50] == 55.0  # Median
        assert percentiles[95] >= 95.0
        assert percentiles[99] >= 99.0

    def test_calculate_percentiles_single_value(self):
        """Test percentiles with single value."""
        values = [42.5]
        percentiles = calculate_percentiles(values, [50, 95, 99])

        assert percentiles[50] == 42.5
        assert percentiles[95] == 42.5
        assert percentiles[99] == 42.5

    def test_calculate_percentiles_empty(self):
        """Test percentiles with empty list."""
        values = []
        percentiles = calculate_percentiles(values, [50, 95, 99])

        assert percentiles[50] == 0.0
        assert percentiles[95] == 0.0
        assert percentiles[99] == 0.0

    def test_calculate_percentiles_min_max(self):
        """Test 0th and 100th percentiles."""
        values = [10, 20, 30, 40, 50]
        percentiles = calculate_percentiles(values, [0, 100])

        assert percentiles[0] == 10
        assert percentiles[100] == 50


class TestGenerateHistogram:
    """Tests for histogram generation."""

    def test_generate_histogram_basic(self):
        """Test basic histogram generation."""
        values = list(range(1, 101))  # 1-100
        histogram = generate_histogram(values, bins=10)

        assert len(histogram) == 10
        # Each bin should have 10 values
        for bin_start, bin_end, count in histogram:
            assert count == 10
            assert bin_end > bin_start

    def test_generate_histogram_single_value(self):
        """Test histogram with single value."""
        values = [42.5]
        histogram = generate_histogram(values, bins=5)

        assert len(histogram) == 1
        assert histogram[0][2] == 1  # Count

    def test_generate_histogram_empty(self):
        """Test histogram with empty list."""
        values = []
        histogram = generate_histogram(values, bins=10)

        assert histogram == []

    def test_generate_histogram_custom_bins(self):
        """Test histogram with custom number of bins."""
        values = list(range(1, 21))  # 1-20
        histogram = generate_histogram(values, bins=4)

        assert len(histogram) == 4
        # Total count should equal number of values
        total_count = sum(count for _, _, count in histogram)
        assert total_count == 20
