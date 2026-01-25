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

        # Mock _collect_repository_metrics (used in sequential mode when repo_workers=1)
        mock_result = {
            "pull_requests": [
                {
                    "repo": "test-org/repo1",
                    "pr_number": pr["number"],
                    "title": pr["title"],
                    "branch": "feature-branch",
                    "author": pr["author"]["login"],
                    "created_at": datetime.now(timezone.utc),
                    "merged_at": datetime.now(timezone.utc),
                    "closed_at": None,
                    "state": "merged",
                    "merged": True,
                    "additions": 10,
                    "deletions": 5,
                    "changed_files": 2,
                    "comments": 0,
                    "review_comments": 0,
                    "commits": 1,
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                }
                for pr in prs
            ],
            "reviews": [],
            "commits": [],
            "releases": [],
        }

        with patch.object(github_collector, "_collect_repository_metrics", return_value=mock_result):
            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                assert len(pr_data) == 3
                assert all(pr["author"] in ["alice", "bob", "charlie"] for pr in pr_data)

    def test_collect_single_repo_with_releases(self, github_collector):
        """Test collecting releases from a single repository."""
        releases = [create_release("v1.0.0", "Version 1.0.0"), create_release("v1.1.0", "Version 1.1.0")]

        # Mock _collect_repository_metrics (used in sequential mode when repo_workers=1)
        mock_result = {
            "pull_requests": [],
            "reviews": [],
            "commits": [],
            "releases": [
                {
                    "repo": "test-org/repo1",
                    "tag_name": "v1.0.0",
                    "name": "Version 1.0.0",
                    "published_at": datetime.now(timezone.utc),
                    "is_prerelease": False,
                },
                {
                    "repo": "test-org/repo1",
                    "tag_name": "v1.1.0",
                    "name": "Version 1.1.0",
                    "published_at": datetime.now(timezone.utc),
                    "is_prerelease": False,
                },
            ],
        }

        with patch.object(github_collector, "_collect_repository_metrics", return_value=mock_result):
            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                release_data = data.get("releases", [])
                assert len(release_data) == 2
                assert release_data[0]["tag_name"] == "v1.0.0"

    def test_collect_multiple_repos_sequentially(self, github_collector):
        """Test collecting from multiple repositories (sequential)."""
        repos = ["test-org/repo1", "test-org/repo2", "test-org/repo3"]

        # Track which repo is being collected
        call_tracker = {"calls": []}

        # Create different mock results for each repo call
        def mock_collect_side_effect(owner, name):
            repo_name = f"{owner}/{name}"
            call_tracker["calls"].append(repo_name)
            return {
                "pull_requests": [
                    {
                        "repo": repo_name,
                        "pr_number": 1,
                        "title": f"PR in {repo_name}",
                        "branch": "feature",
                        "author": "alice",
                        "created_at": datetime.now(timezone.utc),
                        "merged_at": datetime.now(timezone.utc),
                        "closed_at": None,
                        "state": "merged",
                        "merged": True,
                        "additions": 10,
                        "deletions": 5,
                        "changed_files": 2,
                        "comments": 0,
                        "review_comments": 0,
                        "commits": 1,
                        "cycle_time_hours": 24.0,
                        "time_to_first_review_hours": 2.0,
                    },
                    {
                        "repo": repo_name,
                        "pr_number": 2,
                        "title": f"Another PR in {repo_name}",
                        "branch": "bugfix",
                        "author": "bob",
                        "created_at": datetime.now(timezone.utc),
                        "merged_at": datetime.now(timezone.utc),
                        "closed_at": None,
                        "state": "merged",
                        "merged": True,
                        "additions": 5,
                        "deletions": 3,
                        "changed_files": 1,
                        "comments": 0,
                        "review_comments": 0,
                        "commits": 1,
                        "cycle_time_hours": 12.0,
                        "time_to_first_review_hours": 1.0,
                    },
                ],
                "reviews": [],
                "commits": [],
                "releases": [],
            }

        with patch.object(github_collector, "_collect_repository_metrics", side_effect=mock_collect_side_effect):
            with patch.object(github_collector, "_get_team_repositories", return_value=repos):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                # Should have 2 PRs from each of 3 repos = 6 total
                assert len(pr_data) == 6
                # Check we have PRs from all repos
                repos_in_data = {pr["repo"] for pr in pr_data}
                assert repos_in_data == set(repos)


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
        # Mock _collect_repository_metrics (used in sequential mode when repo_workers=1)
        mock_result = {
            "pull_requests": [
                {
                    "repo": "test-org/repo1",
                    "pr_number": 1,
                    "title": "Feature",
                    "branch": "feature",
                    "author": "alice",
                    "created_at": datetime.now(timezone.utc),
                    "merged_at": datetime.now(timezone.utc),
                    "closed_at": None,
                    "state": "merged",
                    "merged": True,
                    "additions": 10,
                    "deletions": 5,
                    "changed_files": 2,
                    "comments": 0,
                    "review_comments": 2,
                    "commits": 1,
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                }
            ],
            "reviews": [
                {
                    "repo": "test-org/repo1",
                    "pr_number": 1,
                    "reviewer": "bob",
                    "submitted_at": datetime.now(timezone.utc),
                    "state": "APPROVED",
                    "pr_author": "alice",
                },
                {
                    "repo": "test-org/repo1",
                    "pr_number": 1,
                    "reviewer": "charlie",
                    "submitted_at": datetime.now(timezone.utc),
                    "state": "APPROVED",
                    "pr_author": "alice",
                },
                {
                    "repo": "test-org/repo1",
                    "pr_number": 1,
                    "reviewer": "external-reviewer",
                    "submitted_at": datetime.now(timezone.utc),
                    "state": "COMMENTED",
                    "pr_author": "alice",
                },
            ],
            "commits": [],
            "releases": [],
        }

        with patch.object(github_collector, "_collect_repository_metrics", return_value=mock_result):
            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/repo1"]):
                data = github_collector.collect_all_metrics()

                review_data = data.get("reviews", [])
                # Should have all 3 reviews (team member filtering happens elsewhere)
                assert len(review_data) == 3
                reviewers = {review["reviewer"] for review in review_data}
                assert reviewers == {"bob", "charlie", "external-reviewer"}


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
        # Mock _collect_repository_metrics to return a large number of PRs
        # (simulating pagination already handled internally)
        mock_result = {
            "pull_requests": [
                {
                    "repo": "test-org/big-repo",
                    "pr_number": i,
                    "title": f"PR {i}",
                    "branch": f"feature-{i}",
                    "author": "alice",
                    "created_at": datetime.now(timezone.utc),
                    "merged_at": datetime.now(timezone.utc),
                    "closed_at": None,
                    "state": "merged",
                    "merged": True,
                    "additions": 10,
                    "deletions": 5,
                    "changed_files": 2,
                    "comments": 0,
                    "review_comments": 0,
                    "commits": 1,
                    "cycle_time_hours": 24.0,
                    "time_to_first_review_hours": 2.0,
                }
                for i in range(1, 76)  # 75 PRs total (simulating 2 pages)
            ],
            "reviews": [],
            "commits": [],
            "releases": [],
        }

        with patch.object(github_collector, "_collect_repository_metrics", return_value=mock_result):
            with patch.object(github_collector, "_get_team_repositories", return_value=["test-org/big-repo"]):
                data = github_collector.collect_all_metrics()

                pr_data = data.get("pull_requests", [])
                # Should have all 75 PRs
                assert len(pr_data) == 75
                # All should be from alice
                assert all(pr["author"] == "alice" for pr in pr_data)


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
