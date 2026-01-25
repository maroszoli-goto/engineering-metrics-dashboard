"""Error handling utilities for dashboard API

Provides consistent error handling and logging for API endpoints.
"""

import traceback
from typing import Tuple

from flask import Response, jsonify

# Import from parent's logger (will be injected)
_logger = None


def set_logger(logger):
    """Set the logger instance for error handling"""
    global _logger
    _logger = logger


def handle_api_error(e: Exception, context: str) -> Tuple[Response, int]:
    """Handle API errors with proper logging and generic user message

    Logs full exception details server-side while returning a generic
    error message to the user to prevent information leakage.

    Args:
        e: The exception that occurred
        context: Description of what operation failed (e.g., "Metrics refresh")

    Returns:
        Tuple of (Flask JSON response, HTTP status code 500)

    Examples:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> with app.app_context():
        ...     response, code = handle_api_error(ValueError("test"), "test operation")
        ...     code
        500
    """
    # Log full details server-side
    if _logger:
        _logger.error(f"{context} failed: {str(e)}")
        _logger.error(traceback.format_exc())

    # Return generic message to user
    return jsonify({"error": "An error occurred while processing your request"}), 500
