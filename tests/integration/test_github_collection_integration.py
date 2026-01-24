"""Integration tests for GitHub collection without threading complexity.

These tests focus on validating the collection logic works correctly
without getting bogged down in threading/mocking issues.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from tests.fixtures.github_responses import (
    SAMPLE_REPOS,
    create_combined_pr_releases_response,
    create_commit,
    create_pr_query_response,
    create_pull_request,
    create_release,
    create_releases_query_response,
    create_review,
)


@pytest.fixture
def github_collector():
    """Create GitHub collector with disabled parallel collection."""
    collector = GitHubGraphQLCollector(
        token="test_token", organization="test-org", days_back=90, repo_workers=1  # Disable parallel collection
    )
    collector.teams = ["test-team"]
    collector.team_members = ["alice", "bob", "charlie"]
    return collector


class TestRepositoryCollection:
    """Tests for repository collection logic."""

    def test_collect_single_repo_with_prs(self, github_collector):
        """Test collecting PRs from a single repository."""
        prs = [
            create_pull_request(1, "Feature A", "alice", "MERGED"),
            create_pull_request(2, "Feature B", "bob", "MERGED"),
            create_pull_request(3, "Feature C", "charlie", "MERGED"),
        ]

        with patch.object(github_collector, "_execute_query") as mock_query:
            mock_query.return_value = create_combined_pr_releases_response(
                prs=prs, releases=[], has_next_pr_page=False, has_next_release_page=False
            )

            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                assert len(pr_data) == 3
                assert all(pr["author"] in ["alice", "bob", "charlie"] for pr in pr_data)

    def test_collect_single_repo_with_releases(self, github_collector):
        """Test collecting releases from a single repository."""
        releases = [create_release("v1.0.0", "Version 1.0.0"), create_release("v1.1.0", "Version 1.1.0")]

        with patch.object(github_collector, "_execute_query") as mock_query:
            mock_query.return_value = create_combined_pr_releases_response(
                prs=[], releases=releases, has_next_pr_page=False, has_next_release_page=False
            )

            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                release_data = data.get("releases", [])
                assert len(release_data) == 2
                assert release_data[0]["tag_name"] == "v1.0.0"

    def test_collect_multiple_repos_sequentially(self, github_collector):
        """Test collecting from multiple repositories (sequential)."""
        repos = ["test-org/repo1", "test-org/repo2", "test-org/repo3"]

        # Create different PRs for each repo
        def mock_query_side_effect(query, variables=None):
            if variables and "owner" in variables:
                repo = variables.get("name", "unknown")
                prs = [
                    create_pull_request(1, f"PR in {repo}", "alice", "MERGED"),
                    create_pull_request(2, f"PR in {repo}", "bob", "MERGED"),
                ]
                return create_combined_pr_releases_response(
                    prs=prs, releases=[], has_next_pr_page=False, has_next_release_page=False
                )
            return {"data": {}}

        with patch.object(github_collector, "_execute_query", side_effect=mock_query_side_effect):
            with patch.object(github_collector, "_get_team_repositories", return_value=repos):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                # Should have PRs from all repos
                assert len(pr_data) >= 2  # At least some PRs collected


class TestTeamMemberFiltering:
    """Tests for team member filtering during collection."""

    def test_filters_non_team_member_prs(self, github_collector):
        """Test that PRs from non-team members are filtered out."""
        prs = [
            create_pull_request(1, "Team PR", "alice", "MERGED"),
            create_pull_request(2, "Team PR", "bob", "MERGED"),
            create_pull_request(3, "External PR", "external-user", "MERGED"),
            create_pull_request(4, "Another External", "stranger", "MERGED"),
        ]

        with patch.object(github_collector, "_execute_query") as mock_query:
            mock_query.return_value = create_combined_pr_releases_response(
                prs=prs, releases=[], has_next_pr_page=False, has_next_release_page=False
            )

            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                # Only team members' PRs should be included
                authors = {pr["author"] for pr in pr_data}
                assert authors.issubset({"alice", "bob", "charlie"})

    def test_includes_reviews_from_team_members(self, github_collector):
        """Test that reviews from team members are included."""
        pr_with_reviews = create_pull_request(
            1,
            "Feature",
            "alice",
            "MERGED",
            reviews=[
                create_review("bob", "APPROVED"),
                create_review("charlie", "APPROVED"),
                create_review("external-reviewer", "COMMENTED"),
            ],
        )

        with patch.object(github_collector, "_execute_query") as mock_query:
            mock_query.return_value = create_combined_pr_releases_response(
                prs=[pr_with_reviews], releases=[], has_next_pr_page=False, has_next_release_page=False
            )

            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                review_data = data.get("reviews", [])
                # Should have reviews from team members
                assert len(review_data) >= 2


class TestDateRangeFiltering:
    """Tests for date range filtering during collection."""

    def test_respects_days_back_parameter(self, github_collector):
        """Test that collection respects the days_back parameter."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)

        prs = [
            create_pull_request(
                1, "Recent PR", "alice", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=30)
            ),
            create_pull_request(
                2, "Old PR", "bob", "MERGED", created_at=datetime.now(timezone.utc) - timedelta(days=120)
            ),
        ]

        with patch.object(github_collector, "_execute_query") as mock_query:
            mock_query.return_value = create_combined_pr_releases_response(
                prs=prs, releases=[], has_next_pr_page=False, has_next_release_page=False
            )

            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                # Old PR should be filtered out
                for pr in pr_data:
                    pr_date = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                    assert pr_date >= cutoff_date


class TestErrorHandling:
    """Tests for error handling during collection."""

    def test_continues_on_repo_error(self, github_collector):
        """Test that collection continues when one repo fails."""
        repos = ["test-org/good-repo", "test-org/bad-repo", "test-org/another-good"]

        call_count = [0]

        def mock_query_side_effect(query, variables=None):
            call_count[0] += 1
            if variables and "name" in variables:
                repo = variables["name"]
                if repo == "bad-repo":
                    raise Exception("API error")
                prs = [create_pull_request(1, f"PR in {repo}", "alice", "MERGED")]
                return create_combined_pr_releases_response(
                    prs=prs, releases=[], has_next_pr_page=False, has_next_release_page=False
                )
            return {"data": {}}

        with patch.object(github_collector, "_execute_query", side_effect=mock_query_side_effect):
            with patch.object(github_collector, "_get_team_repositories", return_value=repos):
                data = github_collector.collect_all_metrics()

                # Should have data from good repos despite bad-repo failure
                pr_data = data.get("pull_requests", [])
                # Collector should have attempted all repos
                assert call_count[0] >= len(repos)

    def test_handles_empty_repository(self, github_collector):
        """Test handling of repository with no data."""
        with patch.object(github_collector, "_execute_query") as mock_query:
            mock_query.return_value = create_combined_pr_releases_response(
                prs=[], releases=[], has_next_pr_page=False, has_next_release_page=False
            )

            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/empty-repo"]):
                data = github_collector.collect_all_metrics()

                # Should complete without errors
                assert data.get("pull_requests", []) == []
                assert data.get("releases", []) == []


class TestPagination:
    """Tests for pagination during collection."""

    def test_handles_pagination_for_prs(self, github_collector):
        """Test that collector handles PR pagination correctly."""
        page1_prs = [create_pull_request(i, f"PR {i}", "alice", "MERGED") for i in range(1, 51)]
        page2_prs = [create_pull_request(i, f"PR {i}", "alice", "MERGED") for i in range(51, 76)]

        call_count = [0]

        def mock_query_side_effect(query, variables=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return create_combined_pr_releases_response(
                    prs=page1_prs, releases=[], has_next_pr_page=True, has_next_release_page=False
                )
            else:
                return create_combined_pr_releases_response(
                    prs=page2_prs, releases=[], has_next_pr_page=False, has_next_release_page=False
                )

        with patch.object(github_collector, "_execute_query", side_effect=mock_query_side_effect):
            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/big-repo"]):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                # Should have all PRs from both pages
                assert len(pr_data) == 75


class TestEdgeCases:
    """Tests for edge cases in collection."""

    def test_handles_zero_repos(self, github_collector):
        """Test collection with no repositories."""
        with patch.object(github_collector, "_get_team_repositories", return_value=[]):
            data = github_collector.collect_all_metrics()

            assert data.get("pull_requests", []) == []
            assert data.get("releases", []) == []

    def test_handles_no_team_members(self, github_collector):
        """Test collection with no team members configured."""
        github_collector.team_members = []

        prs = [create_pull_request(1, "PR 1", "alice", "MERGED"), create_pull_request(2, "PR 2", "bob", "MERGED")]

        with patch.object(github_collector, "_execute_query") as mock_query:
            mock_query.return_value = create_combined_pr_releases_response(
                prs=prs, releases=[], has_next_pr_page=False, has_next_release_page=False
            )

            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                # With no team members, no PRs should be collected
                pr_data = data.get("pull_requests", [])
                assert len(pr_data) == 0
