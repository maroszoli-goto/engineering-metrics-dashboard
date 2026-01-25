"""Input validation utilities for dashboard

Security-focused validation functions to prevent XSS and path traversal.
"""

import re


def validate_identifier(value: str, name: str) -> str:
    """Validate team name or username - only allow safe characters

    Prevents XSS attacks and path traversal by restricting input to
    alphanumeric characters, spaces, and common safe punctuation.

    Args:
        value: The input value to validate
        name: Name of the parameter (for error messages)

    Returns:
        The validated value (unchanged if valid)

    Raises:
        ValueError: If value contains unsafe characters or is too long

    Examples:
        >>> validate_identifier("Native Team", "team name")
        'Native Team'
        >>> validate_identifier("john.doe-123", "username")
        'john.doe-123'
        >>> validate_identifier("invalid<script>", "team")
        Traceback (most recent call last):
        ...
        ValueError: Invalid team: contains unsafe characters
        >>> validate_identifier("a" * 101, "name")
        Traceback (most recent call last):
        ...
        ValueError: Invalid name: too long
    """
    # Allow: letters, numbers, underscore, hyphen, space, dot
    # This matches typical team names and usernames
    if not re.match(r"^[a-zA-Z0-9_\- .]+$", value):
        raise ValueError(f"Invalid {name}: contains unsafe characters")

    # Additional length check
    if len(value) > 100:
        raise ValueError(f"Invalid {name}: too long")

    return value
