"""Data filtering utilities for dashboard

Functions for filtering GitHub and Jira data by date ranges.
"""

from datetime import datetime
from typing import Any, Dict, List, cast

import pandas as pd


def filter_github_data_by_date(raw_data: Dict, start_date: datetime, end_date: datetime) -> Dict:
    """Filter GitHub raw data by date range

    Filters pull requests, reviews, and commits to only include data
    within the specified date range.

    Args:
        raw_data: Dictionary containing 'pull_requests', 'reviews', 'commits'
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        Filtered dictionary with same structure as raw_data

    Examples:
        >>> from datetime import datetime
        >>> data = {
        ...     'pull_requests': [{'created_at': '2025-01-15T10:00:00Z'}],
        ...     'reviews': [],
        ...     'commits': []
        ... }
        >>> start = datetime(2025, 1, 1)
        >>> end = datetime(2025, 1, 31)
        >>> filtered = filter_github_data_by_date(data, start, end)
        >>> len(filtered['pull_requests'])
        1
    """
    filtered = {}

    # Filter PRs
    if "pull_requests" in raw_data and raw_data["pull_requests"]:
        prs_df = pd.DataFrame(raw_data["pull_requests"])
        if "created_at" in prs_df.columns:
            prs_df["created_at"] = pd.to_datetime(prs_df["created_at"])
            mask = (prs_df["created_at"] >= start_date) & (prs_df["created_at"] <= end_date)
            filtered["pull_requests"] = prs_df[mask].to_dict("records")
        else:
            filtered["pull_requests"] = raw_data["pull_requests"]
    else:
        filtered["pull_requests"] = []

    # Filter reviews
    if "reviews" in raw_data and raw_data["reviews"]:
        reviews_df = pd.DataFrame(raw_data["reviews"])
        if "submitted_at" in reviews_df.columns:
            reviews_df["submitted_at"] = pd.to_datetime(reviews_df["submitted_at"])
            mask = (reviews_df["submitted_at"] >= start_date) & (reviews_df["submitted_at"] <= end_date)
            filtered["reviews"] = reviews_df[mask].to_dict("records")
        else:
            filtered["reviews"] = raw_data["reviews"]
    else:
        filtered["reviews"] = []

    # Filter commits
    if "commits" in raw_data and raw_data["commits"]:
        commits_df = pd.DataFrame(raw_data["commits"])
        # Check for both 'date' and 'committed_date' field names
        date_field = "date" if "date" in commits_df.columns else "committed_date"
        if date_field in commits_df.columns:
            commits_df["commit_date"] = pd.to_datetime(commits_df[date_field], utc=True)
            mask = (commits_df["commit_date"] >= start_date) & (commits_df["commit_date"] <= end_date)
            filtered["commits"] = commits_df[mask].to_dict("records")
        else:
            filtered["commits"] = raw_data["commits"]
    else:
        filtered["commits"] = []

    return filtered


def filter_jira_data_by_date(issues: List, start_date: datetime, end_date: datetime) -> List:
    """Filter Jira issues by date range

    Includes issues if ANY of these conditions are true:
    - Created in the period
    - Resolved in the period
    - Updated in the period (for WIP items)

    Args:
        issues: List of Jira issue dictionaries
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of filtered issue dictionaries

    Examples:
        >>> from datetime import datetime
        >>> issues = [
        ...     {'key': 'ISSUE-1', 'created': '2025-01-15T10:00:00Z', 'resolved': None},
        ...     {'key': 'ISSUE-2', 'created': '2024-01-15T10:00:00Z', 'resolved': None}
        ... ]
        >>> start = datetime(2025, 1, 1, tzinfo=datetime.UTC)
        >>> end = datetime(2025, 1, 31, tzinfo=datetime.UTC)
        >>> filtered = filter_jira_data_by_date(issues, start, end)
        >>> len(filtered)
        1
    """
    if not issues:
        return []

    issues_df = pd.DataFrame(issues)

    # Convert date fields to datetime
    if "created" in issues_df.columns:
        issues_df["created"] = pd.to_datetime(issues_df["created"], utc=True)
    if "resolved" in issues_df.columns:
        issues_df["resolved"] = pd.to_datetime(issues_df["resolved"], utc=True)
    if "updated" in issues_df.columns:
        issues_df["updated"] = pd.to_datetime(issues_df["updated"], utc=True)

    # Include issue if ANY of these conditions are true:
    # - Created in period
    # - Resolved in period
    # - Updated in period (for WIP items)
    mask = pd.Series([False] * len(issues_df))

    if "created" in issues_df.columns:
        created_mask = (issues_df["created"] >= start_date) & (issues_df["created"] <= end_date)
        mask |= created_mask

    if "resolved" in issues_df.columns:
        resolved_mask = (
            issues_df["resolved"].notna() & (issues_df["resolved"] >= start_date) & (issues_df["resolved"] <= end_date)
        )
        mask |= resolved_mask

    if "updated" in issues_df.columns:
        updated_mask = (issues_df["updated"] >= start_date) & (issues_df["updated"] <= end_date)
        mask |= updated_mask

    return cast(List[Any], issues_df[mask].to_dict("records"))
