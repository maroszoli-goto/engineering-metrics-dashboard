"""
Tests for Jira Fix Version parsing

Tests cover:
- Fix version name parsing (various formats)
- Invalid date handling
- Month format variations
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.collectors.jira_collector import JiraCollector


class TestFixVersionNameParsing:
    """Tests for _parse_fix_version_name method"""

    @patch("src.collectors.jira_collector.JIRA")
    def test_parses_live_format(self, mock_jira_class):
        # Arrange
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"])

        # Act
        result = collector._parse_fix_version_name("Live - 21/Oct/2025")

        # Assert
        assert result is not None
        assert result["tag_name"] == "Live - 21/Oct/2025"
        assert "published_at" in result
        # Check the published_at datetime
        published_at = result["published_at"]
        assert published_at.year == 2025
        assert published_at.month == 10
        assert published_at.day == 21

    @patch("src.collectors.jira_collector.JIRA")
    def test_parses_beta_format(self, mock_jira_class):
        # Arrange
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"])

        # Act
        result = collector._parse_fix_version_name("Beta - 15/Jan/2026")

        # Assert
        assert result is not None
        assert result["tag_name"] == "Beta - 15/Jan/2026"
        published_at = result["published_at"]
        assert published_at.year == 2026
        assert published_at.month == 1
        assert published_at.day == 15

    @patch("src.collectors.jira_collector.JIRA")
    def test_parses_underscore_format(self, mock_jira_class):
        # Arrange
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"])

        # Act
        result = collector._parse_fix_version_name("RA_Web_2025_11_25")

        # Assert
        assert result is not None
        assert result["tag_name"] == "RA_Web_2025_11_25"
        published_at = result["published_at"]
        assert published_at.year == 2025
        assert published_at.month == 11
        assert published_at.day == 25

    @patch("src.collectors.jira_collector.JIRA")
    def test_handles_invalid_date_gracefully(self, mock_jira_class):
        # Arrange
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"])

        # Act - Invalid date like "32/Jan/2025"
        result = collector._parse_fix_version_name("Live - 32/Jan/2025")

        # Assert
        assert result is None

    @patch("src.collectors.jira_collector.JIRA")
    def test_handles_unparseable_format(self, mock_jira_class):
        # Arrange
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"])

        # Act
        result = collector._parse_fix_version_name("Random Version Name 1.2.3")

        # Assert
        assert result is None

    @patch("src.collectors.jira_collector.JIRA")
    def test_parses_various_month_formats(self, mock_jira_class):
        # Arrange
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        collector = JiraCollector("https://jira.example.com", "user", "token", ["PROJ"])

        # Act & Assert - Test different month abbreviations
        test_cases = [
            ("Live - 1/Jan/2025", 1),
            ("Live - 15/Feb/2025", 2),
            ("Live - 30/Mar/2025", 3),
            ("Live - 10/Apr/2025", 4),
            ("Live - 20/May/2025", 5),
            ("Live - 15/Jun/2025", 6),
            ("Live - 4/Jul/2025", 7),
            ("Live - 25/Aug/2025", 8),
            ("Live - 12/Sep/2025", 9),
            ("Live - 31/Oct/2025", 10),
            ("Live - 28/Nov/2025", 11),
            ("Live - 25/Dec/2025", 12),
        ]

        for version_name, expected_month in test_cases:
            result = collector._parse_fix_version_name(version_name)
            assert result is not None, f"Failed to parse: {version_name}"
            assert result["published_at"].month == expected_month
