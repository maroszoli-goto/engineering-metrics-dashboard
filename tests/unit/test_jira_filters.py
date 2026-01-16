"""Tests for Jira filters utility module

This module tests the Jira filter utility functions including:
- Listing user filters
- Searching filters by name
- Getting filter JQL
- Exporting filter mappings
- Printing filters table
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.utils.jira_filters import (
    export_filter_mapping,
    get_filter_jql,
    list_user_filters,
    print_filters_table,
    search_filters_by_name,
)


class TestListUserFilters:
    """Tests for list_user_filters function"""

    def test_list_filters_success(self):
        """Test successfully listing filters"""
        # Mock Jira client
        mock_jira = Mock()

        # Mock filter objects
        filter1 = Mock()
        filter1.id = "12345"
        filter1.name = "My Test Filter"
        filter1.jql = "project = TEST"
        filter1.owner = Mock(displayName="John Doe")

        filter2 = Mock()
        filter2.id = "12346"
        filter2.name = "Another Filter"
        filter2.jql = "assignee = currentUser()"
        filter2.owner = Mock(displayName="Jane Smith")

        mock_jira.favourite_filters.return_value = [filter1, filter2]

        # Execute
        result = list_user_filters(mock_jira)

        # Verify
        assert len(result) == 2
        assert result[0]["id"] == "12345"
        assert result[0]["name"] == "My Test Filter"
        assert result[0]["jql"] == "project = TEST"
        assert result[0]["owner"] == "John Doe"
        assert result[0]["favourite"] is True

        assert result[1]["id"] == "12346"
        assert result[1]["name"] == "Another Filter"

    def test_list_filters_missing_jql(self):
        """Test handling filters without JQL attribute"""
        mock_jira = Mock()

        # Mock filter without JQL
        filter_obj = Mock(spec=["id", "name", "owner"])
        filter_obj.id = "12345"
        filter_obj.name = "Test Filter"
        filter_obj.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter_obj]

        result = list_user_filters(mock_jira)

        assert len(result) == 1
        assert result[0]["jql"] == "N/A"

    def test_list_filters_missing_owner(self):
        """Test handling filters without owner attribute"""
        mock_jira = Mock()

        # Mock filter without owner
        filter_obj = Mock(spec=["id", "name", "jql"])
        filter_obj.id = "12345"
        filter_obj.name = "Test Filter"
        filter_obj.jql = "project = TEST"

        mock_jira.favourite_filters.return_value = [filter_obj]

        result = list_user_filters(mock_jira)

        assert len(result) == 1
        assert result[0]["owner"] == "N/A"

    def test_list_filters_empty(self):
        """Test listing when no filters exist"""
        mock_jira = Mock()
        mock_jira.favourite_filters.return_value = []

        result = list_user_filters(mock_jira)

        assert result == []

    def test_list_filters_error_handling(self, capsys):
        """Test graceful error handling"""
        mock_jira = Mock()
        mock_jira.favourite_filters.side_effect = Exception("API Error")

        result = list_user_filters(mock_jira)

        assert result == []
        captured = capsys.readouterr()
        assert "Error fetching favourite filters" in captured.out


class TestSearchFiltersByName:
    """Tests for search_filters_by_name function"""

    def test_search_exact_match(self):
        """Test searching with exact match"""
        mock_jira = Mock()

        filter1 = Mock()
        filter1.id = "1"
        filter1.name = "Rescue Native Team"
        filter1.jql = "project = RSC"
        filter1.owner = Mock(displayName="User")

        filter2 = Mock()
        filter2.id = "2"
        filter2.name = "WebTC Team"
        filter2.jql = "project = WEB"
        filter2.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter1, filter2]

        result = search_filters_by_name(mock_jira, "Rescue Native")

        assert len(result) == 1
        assert result[0]["name"] == "Rescue Native Team"

    def test_search_case_insensitive(self):
        """Test that search is case-insensitive"""
        mock_jira = Mock()

        filter_obj = Mock()
        filter_obj.id = "1"
        filter_obj.name = "Rescue Native Team"
        filter_obj.jql = "project = RSC"
        filter_obj.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter_obj]

        result1 = search_filters_by_name(mock_jira, "rescue native")
        result2 = search_filters_by_name(mock_jira, "RESCUE NATIVE")
        result3 = search_filters_by_name(mock_jira, "Rescue Native")

        assert len(result1) == 1
        assert len(result2) == 1
        assert len(result3) == 1

    def test_search_partial_match(self):
        """Test searching with partial match"""
        mock_jira = Mock()

        filter1 = Mock()
        filter1.id = "1"
        filter1.name = "Rescue Native Bugs"
        filter1.jql = "project = RSC AND type = Bug"
        filter1.owner = Mock(displayName="User")

        filter2 = Mock()
        filter2.id = "2"
        filter2.name = "Rescue Native WIP"
        filter2.jql = "project = RSC AND status = 'In Progress'"
        filter2.owner = Mock(displayName="User")

        filter3 = Mock()
        filter3.id = "3"
        filter3.name = "WebTC Team"
        filter3.jql = "project = WEB"
        filter3.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter1, filter2, filter3]

        result = search_filters_by_name(mock_jira, "Native")

        assert len(result) == 2
        assert all("Native" in f["name"] for f in result)

    def test_search_no_matches(self):
        """Test searching with no matches"""
        mock_jira = Mock()

        filter_obj = Mock()
        filter_obj.id = "1"
        filter_obj.name = "Some Filter"
        filter_obj.jql = "project = TEST"
        filter_obj.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter_obj]

        result = search_filters_by_name(mock_jira, "NonExistent")

        assert result == []


class TestGetFilterJQL:
    """Tests for get_filter_jql function"""

    def test_get_jql_success(self):
        """Test successfully retrieving filter JQL"""
        mock_jira = Mock()

        mock_filter = Mock()
        mock_filter.jql = "project = TEST AND status = Open"

        mock_jira.filter.return_value = mock_filter

        result = get_filter_jql(mock_jira, "12345")

        assert result == "project = TEST AND status = Open"
        mock_jira.filter.assert_called_once_with("12345")

    def test_get_jql_missing_jql_attribute(self):
        """Test handling filter without JQL attribute"""
        mock_jira = Mock()

        mock_filter = Mock(spec=["id", "name"])  # No jql attribute

        mock_jira.filter.return_value = mock_filter

        result = get_filter_jql(mock_jira, "12345")

        assert result is None

    def test_get_jql_error_handling(self, capsys):
        """Test error handling when filter not found"""
        mock_jira = Mock()
        mock_jira.filter.side_effect = Exception("Filter not found")

        result = get_filter_jql(mock_jira, "99999")

        assert result is None
        captured = capsys.readouterr()
        assert "Error fetching filter 99999" in captured.out


class TestExportFilterMapping:
    """Tests for export_filter_mapping function"""

    def test_export_single_pattern(self):
        """Test exporting with single search pattern"""
        mock_jira = Mock()

        filter1 = Mock()
        filter1.id = "123"
        filter1.name = "Native Bugs"
        filter1.jql = "project = RSC AND type = Bug"
        filter1.owner = Mock(displayName="User")

        filter2 = Mock()
        filter2.id = "124"
        filter2.name = "Native WIP"
        filter2.jql = "project = RSC AND status = WIP"
        filter2.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter1, filter2]

        result = export_filter_mapping(mock_jira, ["Native"])

        assert "Native" in result
        assert len(result["Native"]) == 2
        assert result["Native"][0]["id"] == "123"
        assert result["Native"][0]["name"] == "Native Bugs"
        assert result["Native"][0]["jql"] == "project = RSC AND type = Bug"

    def test_export_multiple_patterns(self):
        """Test exporting with multiple search patterns"""
        mock_jira = Mock()

        filter1 = Mock()
        filter1.id = "1"
        filter1.name = "Team A Filter"
        filter1.jql = "project = A"
        filter1.owner = Mock(displayName="User")

        filter2 = Mock()
        filter2.id = "2"
        filter2.name = "Team B Filter"
        filter2.jql = "project = B"
        filter2.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter1, filter2]

        result = export_filter_mapping(mock_jira, ["Team A", "Team B"])

        assert "Team A" in result
        assert "Team B" in result
        assert len(result["Team A"]) == 1
        assert len(result["Team B"]) == 1
        assert result["Team A"][0]["name"] == "Team A Filter"
        assert result["Team B"][0]["name"] == "Team B Filter"

    def test_export_no_matches(self):
        """Test exporting when pattern has no matches"""
        mock_jira = Mock()

        filter_obj = Mock()
        filter_obj.id = "1"
        filter_obj.name = "Some Filter"
        filter_obj.jql = "project = TEST"
        filter_obj.owner = Mock(displayName="User")

        mock_jira.favourite_filters.return_value = [filter_obj]

        result = export_filter_mapping(mock_jira, ["NonExistent"])

        assert "NonExistent" in result
        assert result["NonExistent"] == []

    def test_export_empty_patterns(self):
        """Test exporting with empty pattern list"""
        mock_jira = Mock()

        result = export_filter_mapping(mock_jira, [])

        assert result == {}


class TestPrintFiltersTable:
    """Tests for print_filters_table function"""

    def test_print_filters(self, capsys):
        """Test printing filters table"""
        filters = [
            {"id": "12345", "name": "Test Filter 1", "owner": "John Doe"},
            {"id": "12346", "name": "Test Filter 2", "owner": "Jane Smith"},
        ]

        print_filters_table(filters)

        captured = capsys.readouterr()
        assert "ID" in captured.out
        assert "Name" in captured.out
        assert "Owner" in captured.out
        assert "12345" in captured.out
        assert "Test Filter 1" in captured.out
        assert "John Doe" in captured.out
        assert "12346" in captured.out

    def test_print_empty_filters(self, capsys):
        """Test printing empty filter list"""
        print_filters_table([])

        captured = capsys.readouterr()
        assert "No filters found" in captured.out

    def test_print_filters_truncates_long_names(self, capsys):
        """Test that long filter names are truncated"""
        filters = [{"id": "1", "name": "A" * 60, "owner": "User"}]  # Very long name

        print_filters_table(filters)

        captured = capsys.readouterr()
        # Name should be truncated to 48 chars
        assert "A" * 48 in captured.out
        assert "A" * 60 not in captured.out

    def test_print_filters_truncates_long_owner(self, capsys):
        """Test that long owner names are truncated"""
        filters = [{"id": "1", "name": "Filter", "owner": "Z" * 30}]  # Very long owner name

        print_filters_table(filters)

        captured = capsys.readouterr()
        # Owner should be truncated to 23 chars
        assert "Z" * 23 in captured.out
        assert "Z" * 30 not in captured.out

    def test_print_filters_missing_owner(self, capsys):
        """Test printing filter without owner field"""
        filters = [{"id": "1", "name": "Filter"}]  # No owner field

        print_filters_table(filters)

        captured = capsys.readouterr()
        assert "N/A" in captured.out
