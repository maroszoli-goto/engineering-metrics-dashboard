"""Tests for formatting utilities"""

from datetime import datetime, timedelta, timezone

import pytest

from src.dashboard.utils.formatting import format_time_ago, format_value_for_csv


class TestFormatTimeAgo:
    """Test format_time_ago function"""

    def test_none_timestamp(self):
        """Should return 'Unknown' for None timestamp"""
        assert format_time_ago(None) == "Unknown"

    def test_just_now(self):
        """Should return 'Just now' for timestamps < 60 seconds ago"""
        now = datetime.now(timezone.utc)
        assert format_time_ago(now) == "Just now"
        assert format_time_ago(now - timedelta(seconds=30)) == "Just now"
        assert format_time_ago(now - timedelta(seconds=59)) == "Just now"

    def test_minutes_ago(self):
        """Should return 'X minutes ago' for timestamps < 1 hour ago"""
        now = datetime.now(timezone.utc)
        assert format_time_ago(now - timedelta(minutes=1)) == "1 minute ago"
        assert format_time_ago(now - timedelta(minutes=5)) == "5 minutes ago"
        assert format_time_ago(now - timedelta(minutes=30)) == "30 minutes ago"
        assert format_time_ago(now - timedelta(minutes=59)) == "59 minutes ago"

    def test_hours_ago(self):
        """Should return 'X hours ago' for timestamps < 1 day ago"""
        now = datetime.now(timezone.utc)
        assert format_time_ago(now - timedelta(hours=1)) == "1 hour ago"
        assert format_time_ago(now - timedelta(hours=2)) == "2 hours ago"
        assert format_time_ago(now - timedelta(hours=12)) == "12 hours ago"
        assert format_time_ago(now - timedelta(hours=23)) == "23 hours ago"

    def test_days_ago(self):
        """Should return 'X days ago' for timestamps >= 1 day ago"""
        now = datetime.now(timezone.utc)
        assert format_time_ago(now - timedelta(days=1)) == "1 day ago"
        assert format_time_ago(now - timedelta(days=3)) == "3 days ago"
        assert format_time_ago(now - timedelta(days=30)) == "30 days ago"
        assert format_time_ago(now - timedelta(days=365)) == "365 days ago"

    def test_naive_timestamp_assumed_utc(self):
        """Should treat naive timestamps as UTC"""
        now_utc = datetime.now(timezone.utc)
        now_naive = datetime.now()  # Naive timestamp
        result = format_time_ago(now_naive)
        # Should not crash and should return a reasonable value
        assert result in ["Just now", "1 minute ago", "2 minutes ago"]

    def test_singular_plural_forms(self):
        """Should use correct singular/plural forms"""
        now = datetime.now(timezone.utc)
        # Singular
        assert "minute ago" in format_time_ago(now - timedelta(minutes=1))
        assert "hour ago" in format_time_ago(now - timedelta(hours=1))
        assert "day ago" in format_time_ago(now - timedelta(days=1))
        # Plural
        assert "minutes ago" in format_time_ago(now - timedelta(minutes=2))
        assert "hours ago" in format_time_ago(now - timedelta(hours=2))
        assert "days ago" in format_time_ago(now - timedelta(days=2))


class TestFormatValueForCsv:
    """Test format_value_for_csv function"""

    def test_integer_unchanged(self):
        """Should return integers unchanged"""
        assert format_value_for_csv(42) == 42
        assert format_value_for_csv(0) == 0
        assert format_value_for_csv(-10) == -10

    def test_float_rounded(self):
        """Should round floats to 2 decimal places"""
        assert format_value_for_csv(3.14159) == 3.14
        assert format_value_for_csv(2.5) == 2.5
        assert format_value_for_csv(0.123456) == 0.12
        assert format_value_for_csv(1.999) == 2.0

    def test_datetime_formatted(self):
        """Should format datetime to ISO-like string"""
        dt = datetime(2025, 1, 25, 14, 30, 0)
        assert format_value_for_csv(dt) == "2025-01-25 14:30:00"

    def test_none_empty_string(self):
        """Should return empty string for None"""
        assert format_value_for_csv(None) == ""

    def test_string_unchanged(self):
        """Should return strings unchanged"""
        assert format_value_for_csv("text") == "text"
        assert format_value_for_csv("123") == "123"
        assert format_value_for_csv("") == ""

    def test_boolean_to_string(self):
        """Should convert booleans to strings"""
        assert format_value_for_csv(True) == "True"
        assert format_value_for_csv(False) == "False"

    def test_list_to_string(self):
        """Should convert lists to strings"""
        assert format_value_for_csv([1, 2, 3]) == "[1, 2, 3]"
        assert format_value_for_csv(["a", "b"]) == "['a', 'b']"

    def test_dict_to_string(self):
        """Should convert dicts to strings"""
        result = format_value_for_csv({"key": "value"})
        assert "key" in result
        assert "value" in result
