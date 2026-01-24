"""Realistic GitHub GraphQL API response fixtures for integration tests.

This module provides mock responses that closely match the actual GitHub GraphQL API,
including repository queries, pull request data, reviews, commits, and releases.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


def create_repository_query_response(repos: List[str], has_next_page: bool = False) -> Dict[str, Any]:
    """Create a mock repository query response.

    Args:
        repos: List of repository names (e.g., ['repo1', 'repo2'])
        has_next_page: Whether there are more pages

    Returns:
        GraphQL response dict
    """
    nodes = [
        {
            "name": repo_name,
            "nameWithOwner": f"test-org/{repo_name}",
            "isPrivate": False,
            "isArchived": False,
            "isFork": False,
        }
        for repo_name in repos
    ]

    return {
        "data": {
            "organization": {
                "repositories": {
                    "nodes": nodes,
                    "pageInfo": {"hasNextPage": has_next_page, "endCursor": "cursor123" if has_next_page else None},
                }
            }
        }
    }


def create_pull_request(
    number: int,
    title: str,
    author: str,
    state: str = "MERGED",
    created_at: datetime = None,
    merged_at: datetime = None,
    additions: int = 50,
    deletions: int = 20,
    reviews: List[Dict] = None,
    commits: List[Dict] = None,
) -> Dict[str, Any]:
    """Create a mock pull request.

    Args:
        number: PR number
        title: PR title
        author: Author username
        state: PR state (OPEN, CLOSED, MERGED)
        created_at: Creation timestamp
        merged_at: Merge timestamp
        additions: Lines added
        deletions: Lines deleted
        reviews: List of review dicts
        commits: List of commit dicts

    Returns:
        PR data dict
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc) - timedelta(days=7)
    if merged_at is None and state == "MERGED":
        merged_at = datetime.now(timezone.utc) - timedelta(days=3)

    return {
        "number": number,
        "title": title,
        "state": state,
        "createdAt": created_at.isoformat(),
        "mergedAt": merged_at.isoformat() if merged_at else None,
        "closedAt": merged_at.isoformat() if state in ["MERGED", "CLOSED"] else None,
        "additions": additions,
        "deletions": deletions,
        "author": {"login": author},
        "baseRefName": "main",
        "headRefName": f"feature/pr-{number}",
        "reviews": {"nodes": reviews or []},
        "commits": {"nodes": commits or []},
    }


def create_review(reviewer: str, state: str = "APPROVED", submitted_at: datetime = None) -> Dict[str, Any]:
    """Create a mock PR review.

    Args:
        reviewer: Reviewer username
        state: Review state (APPROVED, CHANGES_REQUESTED, COMMENTED)
        submitted_at: Submission timestamp

    Returns:
        Review data dict
    """
    if submitted_at is None:
        submitted_at = datetime.now(timezone.utc) - timedelta(days=2)

    return {"author": {"login": reviewer}, "state": state, "submittedAt": submitted_at.isoformat()}


def create_commit(author: str, committed_date: datetime = None) -> Dict[str, Any]:
    """Create a mock commit.

    Args:
        author: Commit author username
        committed_date: Commit timestamp

    Returns:
        Commit data dict
    """
    if committed_date is None:
        committed_date = datetime.now(timezone.utc) - timedelta(days=5)

    return {"commit": {"author": {"user": {"login": author}}, "committedDate": committed_date.isoformat()}}


def create_pr_query_response(prs: List[Dict], has_next_page: bool = False) -> Dict[str, Any]:
    """Create a mock PR query response.

    Args:
        prs: List of PR dicts (from create_pull_request)
        has_next_page: Whether there are more pages

    Returns:
        GraphQL response dict
    """
    return {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": prs,
                    "pageInfo": {"hasNextPage": has_next_page, "endCursor": "cursor456" if has_next_page else None},
                }
            }
        }
    }


def create_release(
    tag_name: str, name: str, published_at: datetime = None, is_prerelease: bool = False
) -> Dict[str, Any]:
    """Create a mock release.

    Args:
        tag_name: Release tag (e.g., 'v1.0.0', 'Live - 21/Oct/2025')
        name: Release name
        published_at: Publication timestamp
        is_prerelease: Whether this is a pre-release

    Returns:
        Release data dict
    """
    if published_at is None:
        published_at = datetime.now(timezone.utc) - timedelta(days=30)

    return {
        "tagName": tag_name,
        "name": name,
        "publishedAt": published_at.isoformat(),
        "isPrerelease": is_prerelease,
        "isDraft": False,
    }


def create_releases_query_response(releases: List[Dict], has_next_page: bool = False) -> Dict[str, Any]:
    """Create a mock releases query response.

    Args:
        releases: List of release dicts (from create_release)
        has_next_page: Whether there are more pages

    Returns:
        GraphQL response dict
    """
    return {
        "data": {
            "repository": {
                "releases": {
                    "nodes": releases,
                    "pageInfo": {"hasNextPage": has_next_page, "endCursor": "cursor789" if has_next_page else None},
                }
            }
        }
    }


def create_rate_limit_response(remaining: int = 5000, reset_at: datetime = None) -> Dict[str, Any]:
    """Create a mock rate limit response.

    Args:
        remaining: Remaining API points
        reset_at: Rate limit reset timestamp

    Returns:
        GraphQL response dict
    """
    if reset_at is None:
        reset_at = datetime.now(timezone.utc) + timedelta(hours=1)

    return {"data": {"rateLimit": {"remaining": remaining, "resetAt": reset_at.isoformat(), "cost": 1}}}


def create_error_response(message: str, error_type: str = "INTERNAL") -> Dict[str, Any]:
    """Create a mock error response.

    Args:
        message: Error message
        error_type: Error type (INTERNAL, RATE_LIMITED, FORBIDDEN, etc.)

    Returns:
        GraphQL error response dict
    """
    return {"errors": [{"message": message, "type": error_type}]}


def create_combined_pr_releases_response(
    prs: List[Dict], releases: List[Dict], has_next_pr_page: bool = False, has_next_release_page: bool = False
) -> Dict[str, Any]:
    """Create a mock combined PR and releases query response.

    This simulates the batched query optimization where PRs and releases
    are fetched in a single GraphQL query.

    Args:
        prs: List of PR dicts
        releases: List of release dicts
        has_next_pr_page: Whether there are more PR pages
        has_next_release_page: Whether there are more release pages

    Returns:
        GraphQL response dict
    """
    return {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": prs,
                    "pageInfo": {
                        "hasNextPage": has_next_pr_page,
                        "endCursor": "pr_cursor" if has_next_pr_page else None,
                    },
                },
                "releases": {
                    "nodes": releases,
                    "pageInfo": {
                        "hasNextPage": has_next_release_page,
                        "endCursor": "release_cursor" if has_next_release_page else None,
                    },
                },
            }
        }
    }


# Pre-built fixtures for common test scenarios

SAMPLE_TEAM_MEMBERS = ["alice", "bob", "charlie", "diana"]

SAMPLE_REPOS = [
    "frontend-app",
    "backend-api",
    "mobile-ios",
    "mobile-android",
    "infrastructure",
    "documentation",
    "analytics",
    "auth-service",
    "payment-service",
    "notification-service",
]


def create_sample_prs_for_team(count: int = 10, team_members: List[str] = None) -> List[Dict]:
    """Create sample PRs for a team.

    Args:
        count: Number of PRs to create
        team_members: List of team member usernames

    Returns:
        List of PR dicts
    """
    if team_members is None:
        team_members = SAMPLE_TEAM_MEMBERS

    prs = []
    base_date = datetime.now(timezone.utc)

    for i in range(count):
        author = team_members[i % len(team_members)]
        reviewer = team_members[(i + 1) % len(team_members)]

        pr = create_pull_request(
            number=100 + i,
            title=f"Feature: Add feature {i}",
            author=author,
            state="MERGED",
            created_at=base_date - timedelta(days=14 - i),
            merged_at=base_date - timedelta(days=7 - (i // 2)),
            additions=50 + (i * 10),
            deletions=20 + (i * 5),
            reviews=[create_review(reviewer, "APPROVED", base_date - timedelta(days=8 - (i // 2)))],
            commits=[create_commit(author, base_date - timedelta(days=10 - i))],
        )
        prs.append(pr)

    return prs


def create_sample_releases(count: int = 5) -> List[Dict]:
    """Create sample releases.

    Args:
        count: Number of releases to create

    Returns:
        List of release dicts
    """
    releases = []
    base_date = datetime.now(timezone.utc)

    for i in range(count):
        release = create_release(
            tag_name=f"Live - {i+1}/Jan/2025",
            name=f"Production Release {i+1}",
            published_at=base_date - timedelta(days=30 * (count - i)),
            is_prerelease=False,
        )
        releases.append(release)

    return releases
