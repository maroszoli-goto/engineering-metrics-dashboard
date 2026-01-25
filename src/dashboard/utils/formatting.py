"""Formatting utilities for dashboard data display

Pure formatting functions with zero external dependencies.
"""

from datetime import datetime, timezone
from typing import Any, Optional, Union


def format_time_ago(timestamp: Optional[datetime]) -> str:
    """Convert timestamp to 'X hours ago' format

    Args:
        timestamp: datetime object to convert

    Returns:
        Human-readable time ago string (e.g., "2 hours ago", "Just now")

    Examples:
        >>> from datetime import datetime, timedelta, timezone
        >>> now = datetime.now(timezone.utc)
        >>> format_time_ago(now)
        'Just now'
        >>> format_time_ago(now - timedelta(hours=2))
        '2 hours ago'
        >>> format_time_ago(now - timedelta(days=3))
        '3 days ago'
        >>> format_time_ago(None)
        'Unknown'
    """
    if not timestamp:
        return "Unknown"

    now = datetime.now(timezone.utc)

    # If timestamp is naive, assume UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    delta = now - timestamp

    if delta.total_seconds() < 60:
        return "Just now"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(delta.total_seconds() / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def format_value_for_csv(value: Any) -> Union[str, int, float]:
    """Format value for CSV export

    Converts various data types to CSV-friendly formats:
    - Booleans: String representation ("True"/"False")
    - Numbers: Rounded floats, unchanged integers
    - Datetimes: ISO format strings
    - None: Empty string
    - Others: String representation

    Args:
        value: Value to format

    Returns:
        CSV-compatible value (str, int, or float)

    Examples:
        >>> format_value_for_csv(3.14159)
        3.14
        >>> format_value_for_csv(42)
        42
        >>> format_value_for_csv(None)
        ''
        >>> format_value_for_csv("text")
        'text'
        >>> format_value_for_csv(True)
        'True'
    """
    # Check bool before int/float since bool is subclass of int
    if isinstance(value, bool):
        return str(value)
    elif isinstance(value, (int, float)):
        return round(value, 2) if isinstance(value, float) else value
    elif isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    elif value is None:
        return ""
    else:
        return str(value)
