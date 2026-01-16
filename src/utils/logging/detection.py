"""
Interactive mode detection for logging output.

This module determines whether the application is running in an interactive
terminal (TTY) or in a background/automated environment.
"""

import os
import sys


def is_interactive() -> bool:
    """
    Detect if running in an interactive terminal.

    Returns True if:
    - stdout is a TTY
    - TERM environment variable is set
    - Not running in CI environment

    Returns:
        bool: True if interactive terminal, False otherwise
    """
    # Check if stdout is a TTY
    if not sys.stdout.isatty():
        return False

    # Check if TERM is set (indicates terminal emulator)
    if not os.getenv("TERM"):
        return False

    # Don't use interactive mode in CI/automation environments
    ci_vars = ["CI", "JENKINS_URL", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI"]
    if any(os.getenv(var) for var in ci_vars):
        return False

    return True


def should_use_color() -> bool:
    """
    Determine if colored output should be used.

    Returns True if:
    - Running in interactive mode
    - NO_COLOR environment variable is not set
    - TERM is not 'dumb'

    Returns:
        bool: True if colors should be used, False otherwise
    """
    if not is_interactive():
        return False

    # Respect NO_COLOR convention (https://no-color.org/)
    if os.getenv("NO_COLOR"):
        return False

    # Don't use colors in dumb terminals
    if os.getenv("TERM") == "dumb":
        return False

    return True
