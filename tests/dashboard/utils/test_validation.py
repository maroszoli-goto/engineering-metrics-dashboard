"""Tests for input validation utilities"""

import pytest

from src.dashboard.utils.validation import validate_identifier


class TestValidateIdentifier:
    """Test validate_identifier function"""

    def test_valid_team_names(self):
        """Should accept valid team names"""
        assert validate_identifier("Native Team", "team name") == "Native Team"
        assert validate_identifier("Backend", "team name") == "Backend"
        assert validate_identifier("Frontend-UI", "team name") == "Frontend-UI"
        assert validate_identifier("Team_Alpha", "team name") == "Team_Alpha"
        assert validate_identifier("Dev Ops", "team name") == "Dev Ops"

    def test_valid_usernames(self):
        """Should accept valid usernames"""
        assert validate_identifier("johndoe", "username") == "johndoe"
        assert validate_identifier("john.doe", "username") == "john.doe"
        assert validate_identifier("john-doe", "username") == "john-doe"
        assert validate_identifier("john_doe", "username") == "john_doe"
        assert validate_identifier("john123", "username") == "john123"

    def test_alphanumeric_only(self):
        """Should accept alphanumeric identifiers"""
        assert validate_identifier("Team123", "name") == "Team123"
        assert validate_identifier("ABC", "name") == "ABC"
        assert validate_identifier("123", "name") == "123"

    def test_with_spaces(self):
        """Should accept identifiers with spaces"""
        assert validate_identifier("Native Team", "name") == "Native Team"
        assert validate_identifier("Team A", "name") == "Team A"

    def test_with_hyphens(self):
        """Should accept identifiers with hyphens"""
        assert validate_identifier("team-name", "name") == "team-name"
        assert validate_identifier("multi-word-name", "name") == "multi-word-name"

    def test_with_underscores(self):
        """Should accept identifiers with underscores"""
        assert validate_identifier("team_name", "name") == "team_name"
        assert validate_identifier("multi_word_name", "name") == "multi_word_name"

    def test_with_dots(self):
        """Should accept identifiers with dots"""
        assert validate_identifier("john.doe", "name") == "john.doe"
        assert validate_identifier("team.alpha", "name") == "team.alpha"

    def test_reject_script_tags(self):
        """Should reject HTML/script tags (XSS prevention)"""
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("<script>alert('xss')</script>", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("<div>", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("name<tag>", "name")

    def test_reject_special_characters(self):
        """Should reject special characters"""
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("name@domain", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("name#tag", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("name$var", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("name%20", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("name&other", "name")

    def test_reject_path_traversal(self):
        """Should reject path traversal attempts"""
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("../etc/passwd", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("..\\windows\\system32", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("/etc/passwd", "name")

    def test_reject_sql_injection_patterns(self):
        """Should reject SQL injection patterns"""
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("'; DROP TABLE--", "name")
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("' OR '1'='1", "name")

    def test_reject_too_long(self):
        """Should reject identifiers > 100 characters"""
        long_name = "a" * 101
        with pytest.raises(ValueError, match="too long"):
            validate_identifier(long_name, "name")

    def test_accept_max_length(self):
        """Should accept identifiers exactly 100 characters"""
        max_name = "a" * 100
        assert validate_identifier(max_name, "name") == max_name

    def test_reject_empty_string(self):
        """Should reject empty string"""
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_identifier("", "name")

    def test_error_message_includes_parameter_name(self):
        """Should include parameter name in error message"""
        try:
            validate_identifier("<script>", "team name")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "team name" in str(e)

        try:
            validate_identifier("a" * 101, "username")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "username" in str(e)

    def test_real_world_team_names(self):
        """Should accept real-world team names from config"""
        # From project's actual team names
        assert validate_identifier("Native Team", "team") == "Native Team"
        assert validate_identifier("WebTC Team", "team") == "WebTC Team"
        assert validate_identifier("Rescue Team", "team") == "Rescue Team"
        assert validate_identifier("QA-Automation", "team") == "QA-Automation"

    def test_real_world_usernames(self):
        """Should accept real-world GitHub/Jira usernames"""
        assert validate_identifier("zmaros", "username") == "zmaros"
        assert validate_identifier("john.smith", "username") == "john.smith"
        assert validate_identifier("dev_user123", "username") == "dev_user123"
