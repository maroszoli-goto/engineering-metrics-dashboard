"""Tests for date range utilities"""

from datetime import datetime, timedelta, timezone

import pytest

from src.utils.date_ranges import (
    DateRange,
    DateRangeError,
    format_date_for_github_graphql,
    format_date_for_jira_jql,
    get_cache_filename,
    get_preset_ranges,
    parse_date_range,
)


class TestDateRange:
    """Tests for DateRange class"""

    def test_date_range_creation(self):
        """Test creating a valid DateRange"""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        dr = DateRange(start, end, "test", "Test range")

        assert dr.start_date == start
        assert dr.end_date == end
        assert dr.range_key == "test"
        assert dr.description == "Test range"

    def test_date_range_days_calculation(self):
        """Test days property"""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)

        dr = DateRange(start, end, "30d", "30 days")

        assert dr.days == 30

    def test_date_range_invalid_order(self):
        """Test that start_date must be before end_date"""
        start = datetime(2024, 12, 31, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(DateRangeError, match="start_date must be before end_date"):
            DateRange(start, end, "invalid", "Invalid")

    def test_date_range_repr(self):
        """Test string representation"""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)

        dr = DateRange(start, end, "2024", "Year 2024")

        repr_str = repr(dr)
        assert "2024" in repr_str
        assert "2024-01-01" in repr_str
        assert "2024-12-31" in repr_str


class TestParseDateRangeDays:
    """Tests for parsing days-based ranges (30d, 90d, etc.)"""

    def test_parse_30d(self):
        """Test parsing 30-day range"""
        reference = datetime(2024, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
        dr = parse_date_range("30d", reference)

        assert dr.range_key == "30d"
        assert dr.description == "Last 30 days"
        assert dr.days == 30
        assert dr.end_date == reference
        assert dr.start_date == reference - timedelta(days=30)

    def test_parse_90d(self):
        """Test parsing 90-day range"""
        reference = datetime(2024, 12, 31, tzinfo=timezone.utc)
        dr = parse_date_range("90d", reference)

        assert dr.range_key == "90d"
        assert dr.description == "Last 90 days"
        assert dr.days == 90

    def test_parse_365d(self):
        """Test parsing 365-day range"""
        reference = datetime(2024, 12, 31, tzinfo=timezone.utc)
        dr = parse_date_range("365d", reference)

        assert dr.range_key == "365d"
        assert dr.description == "Last 365 days"
        assert dr.days == 365

    def test_parse_days_case_insensitive(self):
        """Test that days format is case-insensitive"""
        reference = datetime(2024, 12, 31, tzinfo=timezone.utc)

        dr1 = parse_date_range("90d", reference)
        dr2 = parse_date_range("90D", reference)

        assert dr1.range_key == dr2.range_key
        assert dr1.days == dr2.days

    def test_parse_days_invalid_zero(self):
        """Test that zero days is invalid"""
        with pytest.raises(DateRangeError, match="Days must be positive"):
            parse_date_range("0d")

    def test_parse_days_invalid_negative(self):
        """Test that negative days is invalid"""
        with pytest.raises(DateRangeError, match="Days must be positive"):
            parse_date_range("-90d")

    def test_parse_days_too_large(self):
        """Test that excessive days (>10 years) is rejected"""
        with pytest.raises(DateRangeError, match="Days too large"):
            parse_date_range("5000d")


class TestParseDateRangeQuarters:
    """Tests for parsing quarter-based ranges (Q1-2025, etc.)"""

    def test_parse_q1(self):
        """Test parsing Q1"""
        dr = parse_date_range("Q1-2025")

        assert dr.range_key == "Q1-2025"
        assert dr.description == "Q1 2025"
        assert dr.start_date == datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert dr.end_date == datetime(2025, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert dr.days == 89  # Jan + Feb + Mar (non-leap year)

    def test_parse_q2(self):
        """Test parsing Q2"""
        dr = parse_date_range("Q2-2024")

        assert dr.start_date == datetime(2024, 4, 1, tzinfo=timezone.utc)
        assert dr.end_date == datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
        assert dr.days == 90  # Days between Apr 1 and Jun 30 23:59:59

    def test_parse_q3(self):
        """Test parsing Q3"""
        dr = parse_date_range("Q3-2024")

        assert dr.start_date == datetime(2024, 7, 1, tzinfo=timezone.utc)
        assert dr.end_date == datetime(2024, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
        assert dr.days == 91  # Days between Jul 1 and Sep 30 23:59:59

    def test_parse_q4(self):
        """Test parsing Q4"""
        dr = parse_date_range("Q4-2024")

        assert dr.start_date == datetime(2024, 10, 1, tzinfo=timezone.utc)
        assert dr.end_date == datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert dr.days == 91  # Days between Oct 1 and Dec 31 23:59:59

    def test_parse_quarter_case_insensitive(self):
        """Test that quarter format is case-insensitive"""
        dr1 = parse_date_range("Q1-2025")
        dr2 = parse_date_range("q1-2025")

        assert dr1.range_key == dr2.range_key.upper()
        assert dr1.start_date == dr2.start_date

    def test_parse_quarter_invalid_number(self):
        """Test that quarter must be 1-4"""
        with pytest.raises(DateRangeError):
            parse_date_range("Q5-2025")

        with pytest.raises(DateRangeError):
            parse_date_range("Q0-2025")

    def test_parse_quarter_invalid_year(self):
        """Test that year must be in valid range"""
        with pytest.raises(DateRangeError, match="Year out of range"):
            parse_date_range("Q1-1999")

        with pytest.raises(DateRangeError, match="Year out of range"):
            parse_date_range("Q1-2101")


class TestParseDateRangeYears:
    """Tests for parsing full year ranges (2024, 2025, etc.)"""

    def test_parse_year_2024(self):
        """Test parsing year 2024"""
        dr = parse_date_range("2024")

        assert dr.range_key == "2024"
        assert dr.description == "Year 2024"
        assert dr.start_date == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert dr.end_date == datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert (
            dr.days == 365
        )  # Days between Jan 1 and Dec 31 23:59:59 (2024 is a leap year, but not counting the last day)

    def test_parse_year_2025(self):
        """Test parsing year 2025 (non-leap)"""
        dr = parse_date_range("2025")

        assert dr.days == 364  # Days between Jan 1 and Dec 31 23:59:59

    def test_parse_year_invalid_range(self):
        """Test that year must be 2000-2100"""
        with pytest.raises(DateRangeError, match="Year out of range"):
            parse_date_range("1999")

        with pytest.raises(DateRangeError, match="Year out of range"):
            parse_date_range("2101")


class TestParseDateRangeCustom:
    """Tests for parsing custom date ranges (YYYY-MM-DD:YYYY-MM-DD)"""

    def test_parse_custom_range(self):
        """Test parsing custom date range"""
        dr = parse_date_range("2024-01-01:2024-03-31")

        assert dr.range_key == "custom_2024-01-01_2024-03-31"
        assert dr.description == "2024-01-01 to 2024-03-31"
        assert dr.start_date == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert dr.end_date == datetime(2024, 3, 31, 23, 59, 59, tzinfo=timezone.utc)

    def test_parse_custom_single_day(self):
        """Test custom range for a single day"""
        dr = parse_date_range("2024-12-25:2024-12-25")

        assert dr.start_date.date() == dr.end_date.date()
        assert dr.days == 0  # Same day

    def test_parse_custom_invalid_format(self):
        """Test invalid custom date format"""
        with pytest.raises(DateRangeError, match="Invalid date format"):
            parse_date_range("2024-13-01:2024-12-31")  # Invalid month

        with pytest.raises(DateRangeError, match="Invalid date format"):
            parse_date_range("2024-01-32:2024-12-31")  # Invalid day

    def test_parse_custom_reversed_dates(self):
        """Test that start must be before end"""
        with pytest.raises(DateRangeError, match="start_date must be before end_date"):
            parse_date_range("2024-12-31:2024-01-01")


class TestParseInvalidFormats:
    """Tests for invalid date range formats"""

    def test_parse_invalid_empty(self):
        """Test empty string"""
        with pytest.raises(DateRangeError, match="Invalid date range format"):
            parse_date_range("")

    def test_parse_invalid_format(self):
        """Test completely invalid format"""
        with pytest.raises(DateRangeError, match="Invalid date range format"):
            parse_date_range("invalid")

    def test_parse_invalid_just_number(self):
        """Test that bare number (without 'd') is interpreted as year"""
        dr = parse_date_range("2024")  # Valid year
        assert dr.range_key == "2024"

        with pytest.raises(DateRangeError):
            parse_date_range("123")  # Invalid as year (too small)


class TestUtilityFunctions:
    """Tests for utility functions"""

    def test_get_preset_ranges(self):
        """Test getting preset ranges"""
        presets = get_preset_ranges()

        assert len(presets) >= 5
        assert ("30d", "Last 30 days") in presets
        assert ("90d", "Last 90 days") in presets
        assert ("365d", "Last 365 days") in presets

    def test_get_cache_filename(self):
        """Test cache filename generation"""
        assert get_cache_filename("90d") == "metrics_cache_90d.pkl"
        assert get_cache_filename("Q1-2025") == "metrics_cache_Q1-2025.pkl"
        assert get_cache_filename("2024") == "metrics_cache_2024.pkl"

    def test_get_cache_filename_sanitization(self):
        """Test that special characters are sanitized"""
        # Colons in custom ranges should be converted to underscores
        filename = get_cache_filename("custom_2024-01-01_2024-12-31")
        assert ":" not in filename
        assert "/" not in filename

    def test_format_date_for_github_graphql(self):
        """Test GitHub GraphQL date formatting"""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        formatted = format_date_for_github_graphql(dt)

        assert formatted == "2024-01-15T10:30:00Z"

    def test_format_date_for_github_graphql_naive(self):
        """Test that naive datetime is converted to UTC"""
        dt = datetime(2024, 1, 15, 10, 30, 0)  # No timezone
        formatted = format_date_for_github_graphql(dt)

        assert formatted == "2024-01-15T10:30:00Z"

    def test_format_date_for_jira_jql(self):
        """Test Jira JQL date formatting"""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        formatted = format_date_for_jira_jql(dt)

        assert formatted == "2024-01-15"


class TestDateRangeEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_parse_with_whitespace(self):
        """Test that whitespace is trimmed"""
        dr = parse_date_range("  90d  ")

        assert dr.range_key == "90d"

    def test_parse_reference_date_none(self):
        """Test that None reference_date uses current time"""
        dr = parse_date_range("30d", reference_date=None)

        # Should be close to now
        assert abs((datetime.now(timezone.utc) - dr.end_date).total_seconds()) < 5

    def test_parse_reference_date_naive(self):
        """Test that naive reference_date is converted to UTC"""
        reference = datetime(2024, 12, 31, 12, 0, 0)  # No timezone
        dr = parse_date_range("30d", reference)

        # Should work without error
        assert dr.end_date.tzinfo == timezone.utc

    def test_quarter_end_times(self):
        """Test that quarter end dates include full last day"""
        dr = parse_date_range("Q1-2025")

        # End date should be end of March 31st
        assert dr.end_date.hour == 23
        assert dr.end_date.minute == 59
        assert dr.end_date.second == 59

    def test_year_end_times(self):
        """Test that year end dates include full last day"""
        dr = parse_date_range("2024")

        # End date should be end of December 31st
        assert dr.end_date.hour == 23
        assert dr.end_date.minute == 59
        assert dr.end_date.second == 59

    def test_custom_range_end_times(self):
        """Test that custom range end dates are adjusted to end of day"""
        dr = parse_date_range("2024-01-01:2024-01-31")

        # End date should be end of Jan 31st
        assert dr.end_date.hour == 23
        assert dr.end_date.minute == 59
        assert dr.end_date.second == 59
