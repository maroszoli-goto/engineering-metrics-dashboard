"""
Unit tests for data validation logic in collect_data.py

Tests the improved validation that distinguishes:
- API failures vs legitimate low-activity periods
- Per-team validation
- Collection status tracking
"""

# Import the validation functions we're testing
# Note: Since collect_data.py is a script, we need to import it carefully
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from collect_data import validate_github_collection, validate_team_github_data


class TestZeroDataValidation:
    """Test validation logic for zero data scenarios"""

    def test_zero_data_with_more_failures_than_successes(self):
        """Zero data + more failures than successes → reject"""
        github_data = {"pull_requests": [], "commits": []}
        team_members = ["user1", "user2"]
        collection_status = {
            "successful_repos": ["repo1"],
            "failed_repos": ["repo2", "repo3", "repo4"],  # 4 failures vs 1 success
            "partial_repos": [],
        }

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        assert not is_valid
        assert not should_cache
        assert any("API failure" in w for w in warnings)

    def test_zero_data_with_all_repos_succeeded(self):
        """Zero data + all repos succeeded → cache (low activity)"""
        github_data = {"pull_requests": [], "commits": []}
        team_members = ["user1", "user2"]
        collection_status = {"successful_repos": ["repo1", "repo2", "repo3"], "failed_repos": [], "partial_repos": []}

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        # Should be valid (low activity is legitimate)
        assert is_valid
        assert should_cache
        assert any("low-activity period" in w for w in warnings)

    def test_zero_data_with_no_repos_collected(self):
        """Zero data + no repos collected → reject (config issue)"""
        github_data = {"pull_requests": [], "commits": []}
        team_members = ["user1", "user2"]
        collection_status = {"successful_repos": [], "failed_repos": [], "partial_repos": []}

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        assert not is_valid
        assert not should_cache
        assert any("No repositories collected" in w for w in warnings)

    def test_some_data_collected_is_valid(self):
        """Some PRs/commits collected → valid"""
        github_data = {
            "pull_requests": [{"author": "user1", "title": "PR 1"}],
            "commits": [{"author": "user1", "message": "commit 1"}],
        }
        team_members = ["user1", "user2"]
        collection_status = {"successful_repos": ["repo1"], "failed_repos": [], "partial_repos": []}

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        # Should be valid (has data)
        assert should_cache
        # May have warnings about missing members, but not critical


class TestCollectionStatusTracking:
    """Test collection status aggregation and tracking"""

    def test_failed_repos_generate_warning(self):
        """Failed repos should generate warnings"""
        github_data = {"pull_requests": [{"author": "user1"}], "commits": []}
        team_members = ["user1"]
        collection_status = {"successful_repos": ["repo1"], "failed_repos": ["repo2", "repo3"], "partial_repos": []}

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        assert any("repositories failed to collect" in w for w in warnings)

    def test_too_many_failures_prevents_caching(self):
        """More failures than successes → don't cache"""
        github_data = {"pull_requests": [{"author": "user1"}], "commits": []}
        team_members = ["user1"]
        collection_status = {
            "successful_repos": ["repo1"],
            "failed_repos": ["repo2", "repo3", "repo4"],  # 3 failures vs 1 success
            "partial_repos": [],
        }

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        assert not should_cache
        assert any("Too many failures" in w for w in warnings)

    def test_equal_successes_and_failures_allows_caching(self):
        """Equal successes and failures → cache (not more failures)"""
        github_data = {"pull_requests": [{"author": "user1"}], "commits": []}
        team_members = ["user1"]
        collection_status = {
            "successful_repos": ["repo1", "repo2"],
            "failed_repos": ["repo3", "repo4"],  # Equal
            "partial_repos": [],
        }

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        # Should cache (not MORE failures than successes)
        assert should_cache


class TestPerTeamValidation:
    """Test per-team validation function"""

    def test_team_with_api_failures(self):
        """Team with API failures generates warning"""
        github_data = {"pull_requests": [], "commits": []}
        team_members = ["user1", "user2"]
        collection_status = {
            "successful_repos": ["repo1"],
            "failed_repos": ["repo2", "repo3"],  # More failures
            "partial_repos": [],
        }

        warnings, should_warn = validate_team_github_data("Team A", github_data, team_members, collection_status)

        assert should_warn
        assert any("API failures detected" in w for w in warnings)

    def test_team_with_no_activity(self):
        """Team with no activity (but successful collection) generates info"""
        github_data = {"pull_requests": [], "commits": []}
        team_members = ["user1", "user2"]
        collection_status = {"successful_repos": ["repo1", "repo2"], "failed_repos": [], "partial_repos": []}

        warnings, should_warn = validate_team_github_data("Team B", github_data, team_members, collection_status)

        assert should_warn
        assert any("No activity in date range" in w for w in warnings)

    def test_team_with_inactive_members(self):
        """Team with some inactive members generates warning"""
        github_data = {
            "pull_requests": [{"author": "user1", "title": "PR 1"}],
            "commits": [{"author": "user1", "message": "commit 1"}],
        }
        team_members = ["user1", "user2", "user3"]  # user2 and user3 inactive
        collection_status = {"successful_repos": ["repo1"], "failed_repos": [], "partial_repos": []}

        warnings, should_warn = validate_team_github_data("Team C", github_data, team_members, collection_status)

        assert should_warn
        assert any("inactive members" in w for w in warnings)

    def test_team_with_all_members_active(self):
        """Team with all members active → no warnings"""
        github_data = {
            "pull_requests": [{"author": "user1", "title": "PR 1"}],
            "commits": [{"author": "user2", "message": "commit 1"}],
        }
        team_members = ["user1", "user2"]
        collection_status = {"successful_repos": ["repo1"], "failed_repos": [], "partial_repos": []}

        warnings, should_warn = validate_team_github_data("Team D", github_data, team_members, collection_status)

        # No warnings about activity or members
        assert not should_warn
        assert len(warnings) == 0


class TestMissingMembers:
    """Test detection of members with no GitHub data"""

    def test_some_missing_members_generates_warning(self):
        """Some members missing data → warning"""
        github_data = {"pull_requests": [{"author": "user1"}], "commits": []}
        team_members = ["user1", "user2", "user3"]
        collection_status = {"successful_repos": ["repo1"], "failed_repos": [], "partial_repos": []}

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        assert any("members have no GitHub data" in w for w in warnings)
        # Should still cache despite warning
        assert should_cache

    def test_all_members_have_data(self):
        """All members have data → no missing member warning"""
        github_data = {"pull_requests": [{"author": "user1"}, {"author": "user2"}], "commits": []}
        team_members = ["user1", "user2"]
        collection_status = {"successful_repos": ["repo1"], "failed_repos": [], "partial_repos": []}

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        # No missing member warning
        assert not any("members have no GitHub data" in w for w in warnings)
        assert should_cache


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_collection_status_dict(self):
        """Empty collection_status dict should handle gracefully"""
        github_data = {"pull_requests": [{"author": "user1"}], "commits": []}
        team_members = ["user1"]
        collection_status = {}  # Empty dict

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        # Should handle gracefully (assumes no failures)
        assert should_cache

    def test_missing_keys_in_collection_status(self):
        """Missing keys in collection_status should handle gracefully"""
        github_data = {"pull_requests": [], "commits": []}
        team_members = ["user1"]
        collection_status = {
            "successful_repos": ["repo1"]
            # Missing failed_repos and partial_repos
        }

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        # Should handle gracefully with .get() defaults
        assert is_valid  # Low activity case
        assert should_cache

    def test_empty_team_members_list(self):
        """Empty team members list should handle gracefully"""
        github_data = {"pull_requests": [{"author": "user1"}], "commits": []}
        team_members = []  # Empty
        collection_status = {"successful_repos": ["repo1"], "failed_repos": [], "partial_repos": []}

        is_valid, warnings, should_cache = validate_github_collection(github_data, team_members, collection_status)

        # Should not crash
        assert should_cache
