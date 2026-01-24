"""Realistic Jira REST API response fixtures for integration tests.

This module provides mock responses that closely match the actual Jira REST API,
including issue searches, filter results, fix versions, and pagination.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def create_issue(
    key: str,
    summary: str,
    issue_type: str = "Story",
    status: str = "Done",
    assignee: str = "alice",
    created: datetime = None,
    resolved: datetime = None,
    fix_versions: List[str] = None,
    changelog: List[Dict] = None,
) -> Dict[str, Any]:
    """Create a mock Jira issue.

    Args:
        key: Issue key (e.g., 'PROJ-123')
        summary: Issue summary
        issue_type: Issue type (Story, Bug, Task, Incident)
        status: Current status
        assignee: Assignee username
        created: Creation timestamp
        resolved: Resolution timestamp
        fix_versions: List of fix version names
        changelog: List of status transitions

    Returns:
        Issue data dict
    """
    if created is None:
        created = datetime.now(timezone.utc) - timedelta(days=30)
    if resolved is None and status == "Done":
        resolved = datetime.now(timezone.utc) - timedelta(days=5)

    issue_dict = {
        "key": key,
        "fields": {
            "summary": summary,
            "issuetype": {"name": issue_type},
            "status": {"name": status, "statusCategory": {"name": "Done" if status == "Done" else "In Progress"}},
            "assignee": {"name": assignee, "displayName": assignee.capitalize()} if assignee else None,
            "created": created.strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
            "resolutiondate": resolved.strftime("%Y-%m-%dT%H:%M:%S.000+0000") if resolved else None,
            "fixVersions": [{"name": v} for v in (fix_versions or [])],
        },
    }

    if changelog:
        issue_dict["changelog"] = {"histories": changelog}

    return issue_dict


def create_status_transition(
    from_status: str, to_status: str, changed_at: datetime = None, author: str = "alice"
) -> Dict[str, Any]:
    """Create a mock status transition for changelog.

    Args:
        from_status: Previous status
        to_status: New status
        changed_at: Transition timestamp
        author: User who made the change

    Returns:
        Changelog history dict
    """
    if changed_at is None:
        changed_at = datetime.now(timezone.utc) - timedelta(days=10)

    return {
        "author": {"name": author},
        "created": changed_at.strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
        "items": [{"field": "status", "fromString": from_status, "toString": to_status}],
    }


def create_search_response(
    issues: List[Dict], start_at: int = 0, max_results: int = 50, total: int = None
) -> Dict[str, Any]:
    """Create a mock Jira search response.

    Args:
        issues: List of issue dicts
        start_at: Starting index
        max_results: Maximum results per page
        total: Total number of issues (defaults to len(issues))

    Returns:
        Search response dict
    """
    if total is None:
        total = len(issues)

    return {"startAt": start_at, "maxResults": max_results, "total": total, "issues": issues}


def create_fix_version(name: str, released: bool = True, release_date: datetime = None) -> Dict[str, Any]:
    """Create a mock fix version.

    Args:
        name: Version name (e.g., 'Live - 21/Oct/2025')
        released: Whether the version is released
        release_date: Release date

    Returns:
        Fix version dict
    """
    if release_date is None:
        release_date = datetime.now(timezone.utc) - timedelta(days=30)

    return {"name": name, "released": released, "releaseDate": release_date.strftime("%Y-%m-%d") if released else None}


def create_filter(filter_id: int, name: str, jql: str) -> Dict[str, Any]:
    """Create a mock Jira filter.

    Args:
        filter_id: Filter ID
        name: Filter name
        jql: JQL query

    Returns:
        Filter dict
    """
    return {"id": str(filter_id), "name": name, "jql": jql, "owner": {"name": "admin"}}


def create_count_response(count: int) -> Dict[str, Any]:
    """Create a mock count response (maxResults=0).

    Args:
        count: Total issue count

    Returns:
        Search response with count only
    """
    return {"startAt": 0, "maxResults": 0, "total": count, "issues": []}


def create_timeout_error() -> Exception:
    """Create a mock 504 Gateway Timeout error.

    Returns:
        Exception simulating Jira timeout
    """
    import requests
    from requests.exceptions import HTTPError

    response = requests.Response()
    response.status_code = 504
    response._content = b"Gateway Timeout"
    return HTTPError(response=response)


def create_server_error() -> Exception:
    """Create a mock 500 Internal Server Error.

    Returns:
        Exception simulating Jira server error
    """
    import requests
    from requests.exceptions import HTTPError

    response = requests.Response()
    response.status_code = 500
    response._content = b"Internal Server Error"
    return HTTPError(response=response)


def create_auth_error() -> Exception:
    """Create a mock 401 Unauthorized error.

    Returns:
        Exception simulating authentication failure
    """
    import requests
    from requests.exceptions import HTTPError

    response = requests.Response()
    response.status_code = 401
    response._content = b"Unauthorized"
    return HTTPError(response=response)


# Pre-built fixtures for common test scenarios

SAMPLE_PROJECTS = ["PROJ", "RSC", "WEB"]
SAMPLE_TEAM_MEMBERS = ["alice", "bob", "charlie", "diana"]


def create_sample_issues_small(count: int = 50) -> List[Dict]:
    """Create a small dataset (<500 issues) for testing.

    Args:
        count: Number of issues to create

    Returns:
        List of issue dicts
    """
    issues = []
    base_date = datetime.now(timezone.utc)

    for i in range(count):
        project = SAMPLE_PROJECTS[i % len(SAMPLE_PROJECTS)]
        assignee = SAMPLE_TEAM_MEMBERS[i % len(SAMPLE_TEAM_MEMBERS)]

        # Mix of issue types
        issue_types = ["Story", "Bug", "Task"]
        issue_type = issue_types[i % len(issue_types)]

        issue = create_issue(
            key=f"{project}-{100 + i}",
            summary=f"Sample issue {i}",
            issue_type=issue_type,
            status="Done",
            assignee=assignee,
            created=base_date - timedelta(days=60 - i),
            resolved=base_date - timedelta(days=30 - (i // 2)),
            fix_versions=[f"Live - {(i // 10) + 1}/Jan/2025"],
        )
        issues.append(issue)

    return issues


def create_sample_issues_medium(count: int = 1500) -> List[Dict]:
    """Create a medium dataset (500-2000 issues) for testing.

    Args:
        count: Number of issues to create

    Returns:
        List of issue dicts
    """
    # For efficiency, create a template and reuse with variations
    issues = []
    base_date = datetime.now(timezone.utc)

    for i in range(count):
        project = SAMPLE_PROJECTS[i % len(SAMPLE_PROJECTS)]
        assignee = SAMPLE_TEAM_MEMBERS[i % len(SAMPLE_TEAM_MEMBERS)]

        issue = create_issue(
            key=f"{project}-{1000 + i}",
            summary=f"Medium dataset issue {i}",
            issue_type="Story",
            status="Done" if i % 3 != 0 else "In Progress",
            assignee=assignee,
            created=base_date - timedelta(days=90 - (i % 90)),
            resolved=base_date - timedelta(days=45 - (i % 45)) if i % 3 != 0 else None,
        )
        issues.append(issue)

    return issues


def create_sample_issues_huge(count: int = 6000) -> List[Dict]:
    """Create a huge dataset (>5000 issues) for testing.

    Args:
        count: Number of issues to create

    Returns:
        List of issue dicts (without changelog for performance)
    """
    issues = []
    base_date = datetime.now(timezone.utc)

    for i in range(count):
        project = SAMPLE_PROJECTS[i % len(SAMPLE_PROJECTS)]
        assignee = SAMPLE_TEAM_MEMBERS[i % len(SAMPLE_TEAM_MEMBERS)]

        # Simplified issues without changelog
        issue = create_issue(
            key=f"{project}-{10000 + i}",
            summary=f"Huge dataset issue {i}",
            issue_type="Story",
            status="Done",
            assignee=assignee,
            created=base_date - timedelta(days=180 - (i % 180)),
            resolved=base_date - timedelta(days=90 - (i % 90)),
        )
        issues.append(issue)

    return issues


def create_sample_incidents(count: int = 10) -> List[Dict]:
    """Create sample incident issues.

    Args:
        count: Number of incidents to create

    Returns:
        List of incident issue dicts
    """
    incidents = []
    base_date = datetime.now(timezone.utc)

    for i in range(count):
        project = SAMPLE_PROJECTS[i % len(SAMPLE_PROJECTS)]

        incident = create_issue(
            key=f"{project}-INC-{i}",
            summary=f"Production incident {i}",
            issue_type="Incident",
            status="Done",
            assignee=SAMPLE_TEAM_MEMBERS[i % len(SAMPLE_TEAM_MEMBERS)],
            created=base_date - timedelta(days=60 - (i * 5)),
            resolved=base_date - timedelta(days=60 - (i * 5) - 2),  # Resolved 2 days after created
            fix_versions=[f"Live - {(i // 2) + 1}/Jan/2025"],
        )
        incidents.append(incident)

    return incidents


def create_sample_fix_versions(count: int = 10) -> List[Dict]:
    """Create sample fix versions.

    Args:
        count: Number of versions to create

    Returns:
        List of fix version dicts
    """
    versions = []
    base_date = datetime.now(timezone.utc)

    for i in range(count):
        version = create_fix_version(
            name=f"Live - {i+1}/Jan/2025", released=True, release_date=base_date - timedelta(days=30 * (count - i))
        )
        versions.append(version)

    # Add some beta/staging versions
    for i in range(3):
        version = create_fix_version(
            name=f"Beta - {i+1}/Jan/2025", released=True, release_date=base_date - timedelta(days=15 * (3 - i))
        )
        versions.append(version)

    return versions


def create_paginated_responses(issues: List[Dict], batch_size: int = 500) -> List[Dict[str, Any]]:
    """Create a list of paginated search responses.

    Args:
        issues: Full list of issues
        batch_size: Issues per page

    Returns:
        List of search response dicts for each page
    """
    responses = []
    total = len(issues)

    for start_at in range(0, total, batch_size):
        batch = issues[start_at : start_at + batch_size]
        response = create_search_response(issues=batch, start_at=start_at, max_results=batch_size, total=total)
        responses.append(response)

    return responses
