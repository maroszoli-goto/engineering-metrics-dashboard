"""
Custom log formatters for structured logging.

This module provides formatters that convert log records into structured formats
suitable for parsing, monitoring, and analysis.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON for machine parsing.

    Each log record is converted to a JSON object with standard fields:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level name (INFO, WARNING, ERROR, etc.)
    - logger: Logger name (e.g., team_metrics.collection)
    - message: The formatted log message
    - module: Python module name
    - function: Function name where log was called
    - line: Line number where log was called

    Additional custom fields from log record extras are also included.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON string representation of the log record
        """
        # Build base log data
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add custom fields from extras
        if hasattr(record, "progress"):
            log_data["progress"] = record.progress

        if hasattr(record, "emoji"):
            log_data["emoji_used"] = record.emoji

        if hasattr(record, "section"):
            log_data["section"] = record.section

        if hasattr(record, "indent"):
            log_data["indent"] = record.indent

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_data)


class StructuredTextFormatter(logging.Formatter):
    """
    Format log records as human-readable structured text.

    This formatter is useful for file logs that need to be human-readable
    but still maintain structure.

    Format: [TIMESTAMP] LEVEL logger.name - message
    Example: [2026-01-15T14:30:15] INFO team_metrics.collection - Connected to Jira
    """

    def __init__(self):
        """Initialize with a standard format string."""
        super().__init__(fmt="[%(asctime)s] %(levelname)s %(name)s - %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as structured text.

        Args:
            record: The log record to format

        Returns:
            Formatted text string
        """
        # Format the base message
        result = super().format(record)

        # Add progress info if present
        if hasattr(record, "progress"):
            progress = record.progress
            result += f" [Progress: {progress['current']}/{progress['total']} ({progress['percent']:.1f}%)]"

        # Add section marker if present
        if hasattr(record, "section"):
            result = f"\n{'=' * 70}\n{result}\n{'=' * 70}"

        return result
