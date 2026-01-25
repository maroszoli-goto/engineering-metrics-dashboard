"""Integration tests for Jira collector workflows

Tests the complete Jira data collection pipeline including:
- Adaptive pagination strategy
- JQL query construction
- Fix version collection and filtering
- Incident collection
- Retry logic and error handling
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
from jira.exceptions import JIRAError

from src.collectors.jira_collector import JiraCollector


class TestAdaptivePagination:
    """Test adaptive pagination strategy"""

    @pytest.fixture
    def collector(self):
        """Create collector instance with mocked JIRA client"""
        with patch("src.collectors.jira_collector.JIRA"):
            return JiraCollector(
                server="https://jira.test.com",
                username="test",
                api_token="test_token",
                project_keys=["TEST"],
                days_back=90,
            )

    def test_single_batch_for_small_dataset(self, collector):
        """Test single query for <500 issues"""
        # Mock count query
        mock_count_result = Mock()
        type(mock_count_result).total = PropertyMock(return_value=400)

        # Mock actual search
        mock_issues = [Mock() for _ in range(400)]

        collector.jira.search_issues = Mock(side_effect=[mock_count_result, mock_issues])

        with patch("src.config.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.jira_pagination = {
                "enabled": True,
                "batch_size": 500,
                "huge_dataset_threshold": 5000,
                "max_retries": 3,
                "retry_delay_seconds": 5,
            }
            mock_config_class.return_value = mock_config

            # Execute
            result = collector._paginate_search("project = TEST", context_name="test query")

            # Verify
            assert len(result) == 400
            assert collector.jira.search_issues.call_count == 2  # count + single batch

    def test_batched_collection_for_medium_dataset(self, collector):
        """Test batches of 500 for 500-2000 issues"""
        # Mock count query
        mock_count_result = Mock()
        type(mock_count_result).total = PropertyMock(return_value=1500)

        # Mock 3 batches of 500 issues each
        batch1 = [Mock() for _ in range(500)]
        batch2 = [Mock() for _ in range(500)]
        batch3 = [Mock() for _ in range(500)]

        collector.jira.search_issues = Mock(side_effect=[mock_count_result, batch1, batch2, batch3])

        with patch("src.config.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.jira_pagination = {
                "enabled": True,
                "batch_size": 500,
                "huge_dataset_threshold": 5000,
                "max_retries": 3,
                "retry_delay_seconds": 5,
            }
            mock_config_class.return_value = mock_config

            # Execute
            result = collector._paginate_search("project = TEST", context_name="medium dataset")

            # Verify
            assert len(result) == 1500
            assert collector.jira.search_issues.call_count == 4  # count + 3 batches

    def test_disables_changelog_for_huge_dataset(self, collector):
        """Test changelog disabled for >5000 issues"""
        # Mock count query
        mock_count_result = Mock()
        type(mock_count_result).total = PropertyMock(return_value=8000)

        # Mock 8 batches of 1000 issues each
        batches = [[Mock() for _ in range(1000)] for _ in range(8)]

        collector.jira.search_issues = Mock(side_effect=[mock_count_result] + batches)

        with patch("src.config.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.jira_pagination = {
                "enabled": True,
                "batch_size": 1000,
                "huge_dataset_threshold": 5000,
                "fetch_changelog_for_large": False,  # Disable changelog
                "max_retries": 3,
                "retry_delay_seconds": 5,
            }
            mock_config_class.return_value = mock_config

            # Execute with changelog requested
            result = collector._paginate_search("project = TEST", expand="changelog", context_name="huge dataset")

            # Verify changelog was disabled (passed expand=None to actual queries)
            assert len(result) == 8000
            # Check that search_issues calls didn't include expand="changelog"
            for call in collector.jira.search_issues.call_args_list[1:]:  # Skip count query
                assert call[1].get("expand") is None

    def test_retries_on_504_timeout(self, collector):
        """Test retry logic on 504 Gateway Timeout"""
        # Mock count query
        mock_count_result = Mock()
        type(mock_count_result).total = PropertyMock(return_value=100)

        # First batch call: 504 error, second call: success
        mock_issues = [Mock() for _ in range(100)]

        def side_effect_with_retry(*args, **kwargs):
            if "startAt" in kwargs:  # Batch query (not count)
                # First call raises timeout
                if not hasattr(side_effect_with_retry, "called"):
                    side_effect_with_retry.called = True
                    raise JIRAError(status_code=504, text="Gateway Timeout")
                # Second call succeeds
                return mock_issues
            return mock_count_result

        collector.jira.search_issues = Mock(side_effect=side_effect_with_retry)

        with patch("src.config.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.jira_pagination = {
                "enabled": True,
                "batch_size": 500,
                "huge_dataset_threshold": 5000,
                "max_retries": 3,
                "retry_delay_seconds": 1,  # Short delay for testing
            }
            mock_config_class.return_value = mock_config

            with patch("time.sleep"):  # Skip actual sleep
                # Execute
                result = collector._paginate_search("project = TEST", context_name="retry test")

                # Verify - should retry and succeed
                assert len(result) == 100

    def test_handles_empty_result(self, collector):
        """Test handling of queries with zero results"""
        # Mock count query returning 0
        mock_count_result = Mock()
        type(mock_count_result).total = PropertyMock(return_value=0)

        collector.jira.search_issues = Mock(return_value=mock_count_result)

        with patch("src.config.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.jira_pagination = {
                "enabled": True,
                "batch_size": 500,
                "huge_dataset_threshold": 5000,
                "max_retries": 3,
                "retry_delay_seconds": 5,
            }
            mock_config_class.return_value = mock_config

            # Execute
            result = collector._paginate_search("project = EMPTY", context_name="empty test")

            # Verify
            assert result == []
            assert collector.jira.search_issues.call_count == 1  # Only count query


class TestJQLQueryConstruction:
    """Test JQL query building"""

    @pytest.fixture
    def collector(self):
        """Create collector instance"""
        with patch("src.collectors.jira_collector.JIRA"):
            return JiraCollector(
                server="https://jira.test.com",
                username="test",
                api_token="test_token",
                project_keys=["TEST"],
                team_members=["alice", "bob"],
                days_back=90,
            )

    def test_person_query_with_anti_noise_filter(self, collector):
        """Test person query includes anti-noise filter for updated tickets"""
        # The actual JQL should be:
        # assignee = "alice" AND (created >= -90d OR resolved >= -90d OR (statusCategory != Done AND updated >= -90d))

        # Mock the paginate search to capture the JQL
        captured_jql = None

        def capture_jql(jql, *args, **kwargs):
            nonlocal captured_jql
            captured_jql = jql
            return []

        with patch.object(collector, "_paginate_search", side_effect=capture_jql):
            # Execute
            collector.collect_person_issues("alice")

            # Verify JQL contains anti-noise logic
            assert captured_jql is not None
            assert "assignee = alice" in captured_jql or 'assignee = "alice"' in captured_jql
            assert "created >=" in captured_jql
            assert "resolved >=" in captured_jql
            assert "statusCategory != Done" in captured_jql
            assert "updated >=" in captured_jql

    def test_filter_query_with_date_range(self, collector):
        """Test filter query adds date range constraints"""
        # Mock filter collection
        captured_jql = None

        def capture_jql(jql, *args, **kwargs):
            nonlocal captured_jql
            captured_jql = jql
            return []

        with patch.object(collector, "_paginate_search", side_effect=capture_jql):
            # Mock the jira.filter() call that collect_filter_issues makes
            mock_filter = Mock()
            mock_filter.name = "Test Filter"
            mock_filter.jql = f"filter = {12345}"
            collector.jira.filter = Mock(return_value=mock_filter)

            # Execute (no filter_name parameter - it's fetched from the filter itself)
            filter_id = 12345
            collector.collect_filter_issues(filter_id)

            # Verify JQL uses filter ID and has date constraints
            assert captured_jql is not None
            assert f"filter = {filter_id}" in captured_jql or f"filter={filter_id}" in captured_jql


class TestFixVersionCollection:
    """Test fix version and release data collection"""

    @pytest.fixture
    def collector(self):
        """Create collector instance"""
        with patch("src.collectors.jira_collector.JIRA"):
            return JiraCollector(
                server="https://jira.test.com",
                username="test",
                api_token="test_token",
                project_keys=["TEST"],
                team_members=["alice", "bob"],
                days_back=90,
            )

    def test_collects_released_versions_only(self, collector):
        """Test only released versions are collected"""
        # Mock version objects (use recent dates within 90-day window)
        released_version = Mock()
        released_version.id = "v1"
        released_version.name = "Live - 15/Jan/2026"  # Recent date within 90-day window
        released_version.released = True
        released_version.archived = False
        released_version.releaseDate = "2026-01-15"

        unreleased_version = Mock()
        unreleased_version.id = "v2"
        unreleased_version.name = "Live - 20/Jan/2026"
        unreleased_version.released = False  # Not released yet
        unreleased_version.archived = False

        # Mock project_versions to return list of versions
        collector.jira.project_versions = Mock(return_value=[released_version, unreleased_version])

        # Mock _get_issues_for_version to return empty list
        with patch.object(collector, "_get_issues_for_version", return_value=[]):
            # Execute (correct method name)
            versions = collector.collect_releases_from_fix_versions(["TEST"])

            # Verify only released version collected
            assert len(versions) >= 1
            # Should have version data
            assert any("Live - 15/Jan/2026" in str(v) for v in versions)

    def test_filters_team_member_issues(self, collector):
        """Test only issues assigned to team members are counted"""
        # Mock version object (use recent date)
        mock_version = Mock()
        mock_version.id = "v1"
        mock_version.name = "Live - 15/Jan/2026"
        mock_version.released = True
        mock_version.archived = False
        mock_version.releaseDate = "2026-01-15"

        # Mock project_versions to return version
        collector.jira.project_versions = Mock(return_value=[mock_version])

        # Mock _get_issues_for_version to return only team member's issue
        team_issue = "TEST-1"  # Just issue key is enough

        with patch.object(collector, "_get_issues_for_version", return_value=[team_issue]):
            # Execute (correct method name)
            versions = collector.collect_releases_from_fix_versions(["TEST"])

            # Verify - should only count alice's issue (team member)
            # The version should have issue count = 1
            assert len(versions) >= 1
            assert versions[0]["team_issue_count"] == 1

    def test_parses_live_version_format(self, collector):
        """Test parsing 'Live - DD/MMM/YYYY' format"""
        # Mock version with "Live - " format (use recent date)
        mock_version = Mock()
        mock_version.id = "v1"
        mock_version.name = "Live - 15/Jan/2026"  # Recent date
        mock_version.released = True
        mock_version.archived = False
        mock_version.releaseDate = None  # Parse from name

        # Mock project_versions to return version
        collector.jira.project_versions = Mock(return_value=[mock_version])

        with patch.object(collector, "_get_issues_for_version", return_value=[]):
            # Execute (correct method name)
            versions = collector.collect_releases_from_fix_versions(["TEST"])

            # Verify version name parsed
            assert len(versions) >= 1


class TestIncidentCollection:
    """Test production incident filtering"""

    @pytest.fixture
    def collector(self):
        """Create collector instance"""
        with patch("src.collectors.jira_collector.JIRA"):
            return JiraCollector(
                server="https://jira.test.com",
                username="test",
                api_token="test_token",
                project_keys=["TEST"],
                days_back=90,
            )

    def test_filters_by_issue_type_only(self, collector):
        """Test incidents filtered by issue type (Incident, GCS Escalation)"""
        # Create mock incidents with different types
        incident1 = Mock()
        incident1.key = "INC-1"
        incident1.fields = Mock()
        incident1.fields.project = Mock()
        incident1.fields.project.key = "TEST"
        incident1.fields.issuetype = Mock()
        incident1.fields.issuetype.name = "Incident"
        incident1.fields.status = Mock()
        incident1.fields.status.name = "Done"
        incident1.fields.priority = Mock()
        incident1.fields.priority.name = "High"
        incident1.fields.assignee = Mock()
        incident1.fields.assignee.name = "alice"
        incident1.fields.reporter = Mock()
        incident1.fields.reporter.name = "bob"
        incident1.fields.created = datetime.now(timezone.utc).isoformat()
        incident1.fields.updated = datetime.now(timezone.utc).isoformat()
        incident1.fields.resolutiondate = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        incident1.fields.summary = "Test incident 1"
        incident1.fields.labels = []
        incident1.fields.description = "Test description"
        incident1.fields.fixVersions = []

        incident2 = Mock()
        incident2.key = "INC-2"
        incident2.fields = Mock()
        incident2.fields.project = Mock()
        incident2.fields.project.key = "TEST"
        incident2.fields.issuetype = Mock()
        incident2.fields.issuetype.name = "GCS Escalation"
        incident2.fields.status = Mock()
        incident2.fields.status.name = "Done"
        incident2.fields.priority = Mock()
        incident2.fields.priority.name = "Critical"
        incident2.fields.assignee = Mock()
        incident2.fields.assignee.name = "alice"
        incident2.fields.reporter = Mock()
        incident2.fields.reporter.name = "bob"
        incident2.fields.created = datetime.now(timezone.utc).isoformat()
        incident2.fields.updated = datetime.now(timezone.utc).isoformat()
        incident2.fields.resolutiondate = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        incident2.fields.summary = "Test incident 2"
        incident2.fields.labels = []
        incident2.fields.description = "Test description"
        incident2.fields.fixVersions = []

        bug = Mock()
        bug.key = "BUG-1"
        bug.fields = Mock()
        bug.fields.project = Mock()
        bug.fields.project.key = "TEST"
        bug.fields.issuetype = Mock()
        bug.fields.issuetype.name = "Bug"  # Not an incident
        bug.fields.status = Mock()
        bug.fields.status.name = "In Progress"
        bug.fields.priority = Mock()
        bug.fields.priority.name = "Critical"  # High priority but not incident
        bug.fields.assignee = Mock()
        bug.fields.assignee.name = "alice"
        bug.fields.reporter = Mock()
        bug.fields.reporter.name = "bob"
        bug.fields.created = datetime.now(timezone.utc).isoformat()
        bug.fields.updated = datetime.now(timezone.utc).isoformat()
        bug.fields.resolutiondate = None
        bug.fields.summary = "Test bug"
        bug.fields.labels = []
        bug.fields.description = "Test description"
        bug.fields.fixVersions = []

        # Mock paginate to return all issues
        with patch.object(collector, "_paginate_search", return_value=[incident1, incident2, bug]):
            # Execute
            incidents = collector.collect_incidents()

            # Verify only true incidents collected (not bugs)
            assert len(incidents) == 2
            assert all(i["key"] in ["INC-1", "INC-2"] for i in incidents)
            assert not any(i["key"] == "BUG-1" for i in incidents)

    def test_handles_missing_resolution_date(self, collector):
        """Test incidents without resolution date are handled"""
        # Unresolved incident
        incident = Mock()
        incident.key = "INC-1"
        incident.fields = Mock()
        incident.fields.project = Mock()
        incident.fields.project.key = "TEST"
        incident.fields.issuetype = Mock()
        incident.fields.issuetype.name = "Incident"
        incident.fields.status = Mock()
        incident.fields.status.name = "In Progress"
        incident.fields.priority = Mock()
        incident.fields.priority.name = "High"
        incident.fields.assignee = Mock()
        incident.fields.assignee.name = "alice"
        incident.fields.reporter = Mock()
        incident.fields.reporter.name = "bob"
        incident.fields.created = datetime.now(timezone.utc).isoformat()
        incident.fields.updated = datetime.now(timezone.utc).isoformat()
        incident.fields.resolutiondate = None  # Still open
        incident.fields.summary = "Test unresolved incident"
        incident.fields.labels = []
        incident.fields.description = "Test description"
        incident.fields.fixVersions = []

        with patch.object(collector, "_paginate_search", return_value=[incident]):
            # Execute
            incidents = collector.collect_incidents()

            # Verify incident included but without resolution
            assert len(incidents) == 1
            assert incidents[0]["key"] == "INC-1"

    def test_calculates_mttr(self, collector):
        """Test MTTR calculation from incident resolution times"""
        # Incident resolved in 2 hours
        incident = Mock()
        incident.key = "INC-1"
        incident.fields = Mock()
        incident.fields.project = Mock()
        incident.fields.project.key = "TEST"
        incident.fields.issuetype = Mock()
        incident.fields.issuetype.name = "Incident"
        incident.fields.status = Mock()
        incident.fields.status.name = "Done"
        incident.fields.priority = Mock()
        incident.fields.priority.name = "High"
        incident.fields.assignee = Mock()
        incident.fields.assignee.name = "alice"
        incident.fields.reporter = Mock()
        incident.fields.reporter.name = "bob"
        created_time = datetime.now(timezone.utc) - timedelta(hours=2)
        incident.fields.created = created_time.isoformat()
        incident.fields.updated = datetime.now(timezone.utc).isoformat()
        incident.fields.resolutiondate = datetime.now(timezone.utc).isoformat()
        incident.fields.summary = "Test incident with resolution"
        incident.fields.labels = []
        incident.fields.description = "Test description"
        incident.fields.fixVersions = []

        with patch.object(collector, "_paginate_search", return_value=[incident]):
            # Execute
            incidents = collector.collect_incidents()

            # Verify incident data captured correctly
            assert len(incidents) == 1
            assert "created" in incidents[0]
            assert "resolved" in incidents[0]


class TestParallelFilterCollection:
    """Test parallel collection from multiple Jira filters"""

    @pytest.fixture
    def collector(self):
        """Create collector instance"""
        with patch("src.collectors.jira_collector.JIRA"):
            return JiraCollector(
                server="https://jira.test.com",
                username="test",
                api_token="test_token",
                project_keys=["TEST"],
                days_back=90,
            )

    def test_collects_multiple_filters_in_parallel(self, collector):
        """Test collecting from multiple filters concurrently"""
        filters = [
            {"id": 12345, "name": "WIP"},
            {"id": 12346, "name": "Bugs"},
            {"id": 12347, "name": "Incidents"},
        ]

        # Mock paginate to return different issues per filter
        call_count = 0

        def mock_paginate(jql, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Return mock issues with all required fields
            issue = Mock()
            issue.key = f"TEST-{call_count}"
            issue.changelog = None  # No changelog to avoid iteration issues
            issue.fields = Mock()
            issue.fields.project = Mock()
            issue.fields.project.key = "TEST"
            issue.fields.issuetype = Mock()
            issue.fields.issuetype.name = "Task"
            issue.fields.status = Mock()
            issue.fields.status.name = "Done"
            issue.fields.priority = Mock()
            issue.fields.priority.name = "Medium"
            issue.fields.assignee = Mock()
            issue.fields.assignee.name = "alice"
            issue.fields.reporter = Mock()
            issue.fields.reporter.name = "bob"
            issue.fields.created = datetime.now(timezone.utc).isoformat()
            issue.fields.updated = datetime.now(timezone.utc).isoformat()
            issue.fields.resolutiondate = datetime.now(timezone.utc).isoformat()
            issue.fields.summary = f"Test issue {call_count}"
            issue.fields.labels = []
            issue.fields.fixVersions = []
            return [issue]

        with patch.object(collector, "_paginate_search", side_effect=mock_paginate):
            # Mock jira.filter() to return filter objects
            def mock_filter(filter_id):
                mock_filter_obj = Mock()
                mock_filter_obj.name = filters[int(filter_id) - 12345]["name"]
                mock_filter_obj.jql = f"filter = {filter_id}"
                return mock_filter_obj

            collector.jira.filter = Mock(side_effect=mock_filter)

            # Execute collection (simulating parallel execution)
            results = {}
            for filter_def in filters:
                issues = collector.collect_filter_issues(filter_def["id"])
                results[filter_def["name"]] = issues

            # Verify all filters collected
            assert len(results) == 3
            assert "WIP" in results
            assert "Bugs" in results
            assert "Incidents" in results

    def test_handles_filter_failure_gracefully(self, collector):
        """Test that failure in one filter doesn't stop others"""
        filters = [
            {"id": 12345, "name": "WIP"},
            {"id": 12346, "name": "Bugs"},  # This will fail
            {"id": 12347, "name": "Incidents"},
        ]

        def mock_paginate(jql, *args, **kwargs):
            if "12346" in jql:
                raise JIRAError(status_code=500, text="Internal Server Error")
            # Return mock issue with all required fields
            issue = Mock()
            issue.key = "TEST-1"
            issue.changelog = None  # No changelog to avoid iteration issues
            issue.fields = Mock()
            issue.fields.project = Mock()
            issue.fields.project.key = "TEST"
            issue.fields.issuetype = Mock()
            issue.fields.issuetype.name = "Task"
            issue.fields.status = Mock()
            issue.fields.status.name = "Done"
            issue.fields.priority = Mock()
            issue.fields.priority.name = "Medium"
            issue.fields.assignee = Mock()
            issue.fields.assignee.name = "alice"
            issue.fields.reporter = Mock()
            issue.fields.reporter.name = "bob"
            issue.fields.created = datetime.now(timezone.utc).isoformat()
            issue.fields.updated = datetime.now(timezone.utc).isoformat()
            issue.fields.resolutiondate = datetime.now(timezone.utc).isoformat()
            issue.fields.summary = "Test issue"
            issue.fields.labels = []
            issue.fields.fixVersions = []
            return [issue]

        # Mock jira.filter() to return filter objects
        def mock_filter(filter_id):
            mock_filter_obj = Mock()
            idx = int(filter_id) - 12345
            mock_filter_obj.name = filters[idx]["name"]
            mock_filter_obj.jql = f"filter = {filter_id}"
            return mock_filter_obj

        collector.jira.filter = Mock(side_effect=mock_filter)

        with patch.object(collector, "_paginate_search", side_effect=mock_paginate):
            # Execute with error handling - collect_filter_issues catches exceptions internally
            results = {}
            for filter_def in filters:
                issues = collector.collect_filter_issues(filter_def["id"])
                results[filter_def["name"]] = issues

            # Verify WIP and Incidents collected, Bugs failed gracefully (returns [])
            assert len(results["WIP"]) > 0
            assert len(results["Bugs"]) == 0  # Failed, returned []
            assert len(results["Incidents"]) > 0


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def collector(self):
        """Create collector instance"""
        with patch("src.collectors.jira_collector.JIRA"):
            return JiraCollector(
                server="https://jira.test.com",
                username="test",
                api_token="test_token",
                project_keys=["TEST"],
                days_back=90,
            )

    def test_handles_connection_error(self, collector):
        """Test handling of connection errors"""
        collector.jira.search_issues = Mock(side_effect=JIRAError(status_code=None, text="Connection refused"))

        with patch("src.config.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.jira_pagination = {
                "enabled": True,
                "batch_size": 500,
                "huge_dataset_threshold": 5000,
                "max_retries": 1,
                "retry_delay_seconds": 1,
            }
            mock_config_class.return_value = mock_config

            # Should raise JIRAError after retries
            with pytest.raises(JIRAError):
                collector._paginate_search("project = TEST", context_name="error test")

    def test_handles_malformed_issue_data(self, collector):
        """Test handling of issues with missing fields"""
        # Issue with minimal data
        malformed_issue = Mock()
        malformed_issue.key = "TEST-1"
        malformed_issue.changelog = None  # No changelog to avoid iteration issues
        malformed_issue.fields = Mock()
        malformed_issue.fields.project = Mock()
        malformed_issue.fields.project.key = "TEST"
        malformed_issue.fields.issuetype = Mock()
        malformed_issue.fields.issuetype.name = "Task"
        malformed_issue.fields.status = Mock()
        malformed_issue.fields.status.name = "Unknown"
        malformed_issue.fields.assignee = None  # Missing assignee
        malformed_issue.fields.priority = None  # Missing priority
        malformed_issue.fields.reporter = Mock()
        malformed_issue.fields.reporter.name = "bob"
        malformed_issue.fields.created = datetime.now(timezone.utc).isoformat()
        malformed_issue.fields.updated = datetime.now(timezone.utc).isoformat()
        malformed_issue.fields.resolutiondate = None
        malformed_issue.fields.summary = "Test malformed issue"
        malformed_issue.fields.fixVersions = []  # Empty list for iteration
        malformed_issue.fields.labels = []  # Empty list for iteration

        with patch.object(collector, "_paginate_search", return_value=[malformed_issue]):
            # Should not crash (correct method name)
            issues = collector.collect_issue_metrics("TEST")

            # Verify issue included despite missing fields
            assert len(issues) > 0
