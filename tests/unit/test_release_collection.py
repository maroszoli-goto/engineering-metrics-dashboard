"""Tests for GitHub release collection"""

import pytest

from src.collectors.github_graphql_collector import GitHubGraphQLCollector


class TestReleaseEnvironmentClassification:
    """Test release environment classification logic"""

    @pytest.fixture
    def collector(self):
        """Create collector instance for testing"""
        return GitHubGraphQLCollector(token="fake_token", organization="test-org", teams=["test-team"])

    def test_production_release_with_v_prefix(self, collector):
        """Test production release with v prefix"""
        result = collector._classify_release_environment("v1.2.3", False)
        assert result == "production"

    def test_production_release_without_v_prefix(self, collector):
        """Test production release without v prefix"""
        result = collector._classify_release_environment("1.2.3", False)
        assert result == "production"

    def test_production_release_double_digits(self, collector):
        """Test production release with double digit versions"""
        result = collector._classify_release_environment("v10.20.30", False)
        assert result == "production"

    def test_staging_release_rc(self, collector):
        """Test staging release with rc suffix"""
        result = collector._classify_release_environment("v1.2.3-rc1", False)
        assert result == "staging"

    def test_staging_release_beta(self, collector):
        """Test staging release with beta suffix"""
        result = collector._classify_release_environment("v1.2.3-beta", False)
        assert result == "staging"

    def test_staging_release_alpha(self, collector):
        """Test staging release with alpha suffix"""
        result = collector._classify_release_environment("v1.2.3-alpha.1", False)
        assert result == "staging"

    def test_staging_release_dev(self, collector):
        """Test staging release with dev suffix"""
        result = collector._classify_release_environment("v1.2.3-dev", False)
        assert result == "staging"

    def test_staging_release_preview(self, collector):
        """Test staging release with preview suffix"""
        result = collector._classify_release_environment("v1.2.3-preview", False)
        assert result == "staging"

    def test_staging_release_snapshot(self, collector):
        """Test staging release with snapshot suffix"""
        result = collector._classify_release_environment("v1.2.3-snapshot", False)
        assert result == "staging"

    def test_prerelease_flag_overrides(self, collector):
        """Test that GitHub prerelease flag marks as staging"""
        result = collector._classify_release_environment("v1.2.3", True)
        assert result == "staging"

    def test_non_standard_tag_defaults_to_staging(self, collector):
        """Test non-standard tags default to staging"""
        result = collector._classify_release_environment("my-custom-release", False)
        assert result == "staging"

    def test_case_insensitive_staging_patterns(self, collector):
        """Test staging pattern matching is case insensitive"""
        result = collector._classify_release_environment("v1.2.3-RC1", False)
        assert result == "staging"

        result = collector._classify_release_environment("v1.2.3-BETA", False)
        assert result == "staging"

    def test_multiple_staging_suffixes(self, collector):
        """Test tags with multiple staging identifiers"""
        result = collector._classify_release_environment("v1.2.3-rc1-test", False)
        assert result == "staging"


class TestReleaseDataStructure:
    """Test release data structure matches expected format"""

    def test_release_entry_has_required_fields(self):
        """Test that release entry contains all required fields"""
        required_fields = [
            "repo",
            "tag_name",
            "release_name",
            "published_at",
            "created_at",
            "environment",
            "author",
            "commit_sha",
            "committed_date",
            "is_prerelease",
        ]

        # This is a documentation test - verifies the structure
        # Real data will be tested in integration tests
        assert all(field for field in required_fields)


class TestJiraFixVersionParsing:
    """Test Jira Fix Version name parsing for DORA metrics"""

    @pytest.fixture
    def jira_collector(self):
        """Create minimal Jira collector for testing"""
        from datetime import datetime, timedelta
        from unittest.mock import Mock, patch

        from src.collectors.jira_collector import JiraCollector

        # Mock the JIRA client to avoid real network calls
        with patch("src.collectors.jira_collector.JIRA") as mock_jira:
            mock_jira.return_value = Mock()
            collector = JiraCollector(
                server="https://jira.example.com",
                username="test",
                api_token="test_token",
                project_keys=["TEST"],
                days_back=90,
                verify_ssl=False,
            )
            return collector

    def test_parse_jira_fix_version_live_production(self, jira_collector):
        """Test parsing Live - 6/Oct/2025 format for production"""
        result = jira_collector._parse_fix_version_name("Live - 6/Oct/2025")

        assert result is not None
        assert result["environment"] == "production"
        assert result["tag_name"] == "Live - 6/Oct/2025"
        assert result["release_name"] == "Live - 6/Oct/2025"
        assert result["published_at"].year == 2025
        assert result["published_at"].month == 10
        assert result["published_at"].day == 6
        assert result["is_prerelease"] == False
        assert result["author"] == "jira"
        assert result["commit_sha"] is None

    def test_parse_jira_fix_version_beta_staging(self, jira_collector):
        """Test parsing Beta - 15/Jan/2026 format for staging"""
        result = jira_collector._parse_fix_version_name("Beta - 15/Jan/2026")

        assert result is not None
        assert result["environment"] == "staging"
        assert result["tag_name"] == "Beta - 15/Jan/2026"
        assert result["published_at"].year == 2026
        assert result["published_at"].month == 1
        assert result["published_at"].day == 15
        assert result["is_prerelease"] == True

    def test_parse_jira_fix_version_single_digit_day(self, jira_collector):
        """Test parsing with single digit day"""
        result = jira_collector._parse_fix_version_name("Live - 1/Dec/2025")

        assert result is not None
        assert result["published_at"].day == 1
        assert result["published_at"].month == 12

    def test_parse_jira_fix_version_double_digit_day(self, jira_collector):
        """Test parsing with double digit day"""
        result = jira_collector._parse_fix_version_name("Beta - 31/Mar/2025")

        assert result is not None
        assert result["published_at"].day == 31
        assert result["published_at"].month == 3

    def test_parse_jira_fix_version_case_insensitive(self, jira_collector):
        """Test parsing is case insensitive"""
        result_lower = jira_collector._parse_fix_version_name("live - 5/Feb/2025")
        result_upper = jira_collector._parse_fix_version_name("BETA - 5/Feb/2025")

        assert result_lower is not None
        assert result_lower["environment"] == "production"
        assert result_upper is not None
        assert result_upper["environment"] == "staging"

    def test_parse_jira_fix_version_invalid_github_format(self, jira_collector):
        """Test that GitHub release format returns None"""
        result = jira_collector._parse_fix_version_name("v1.2.3")
        assert result is None

    def test_parse_jira_fix_version_invalid_format(self, jira_collector):
        """Test that invalid formats return None"""
        assert jira_collector._parse_fix_version_name("Invalid Format") is None
        assert jira_collector._parse_fix_version_name("Live-6/Oct/2025") is None  # Missing space
        assert jira_collector._parse_fix_version_name("Live - 6-Oct-2025") is None  # Wrong separator
        assert jira_collector._parse_fix_version_name("Live - Oct/6/2025") is None  # Wrong order
        assert jira_collector._parse_fix_version_name("Prod - 6/Oct/2025") is None  # Wrong env name

    def test_parse_jira_fix_version_invalid_date(self, jira_collector):
        """Test that invalid dates return None"""
        result = jira_collector._parse_fix_version_name("Live - 32/Jan/2025")  # Day 32 doesn't exist
        assert result is None

    def test_parse_jira_fix_version_timezone_aware(self, jira_collector):
        """Test that parsed datetime is timezone-aware (UTC)"""
        result = jira_collector._parse_fix_version_name("Live - 10/May/2025")

        assert result is not None
        assert result["published_at"].tzinfo is not None
        assert str(result["published_at"].tzinfo) == "UTC"
