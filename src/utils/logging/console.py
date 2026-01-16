"""
Console output wrapper for dual logging (console + file).

This module provides a ConsoleOutput class that handles both interactive
console output (with emojis) and structured file logging.
"""

import logging
from datetime import datetime
from typing import Optional

from .detection import is_interactive


class ConsoleOutput:
    """
    Dual output wrapper: emoji-rich console + structured file logs.

    This class provides methods for logging that adapt to the execution environment:
    - Interactive mode: Prints formatted messages with emojis to console
    - Background mode: Only logs to file (no console output)
    - File logs: Always structured JSON format with metadata
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize ConsoleOutput wrapper.

        Args:
            logger: The underlying Python logger to use for file output
        """
        self.logger = logger
        self.interactive = is_interactive()

    def info(self, message: str, emoji: Optional[str] = None, indent: int = 0):
        """
        Log an informational message.

        Args:
            message: The message to log
            emoji: Optional emoji to prefix (only shown in interactive mode)
            indent: Number of spaces to indent (for hierarchy)
        """
        # File log: structured with metadata
        self.logger.info(message, extra={"emoji": emoji, "indent": indent})

        # Console: with emoji if interactive
        if self.interactive:
            indent_str = " " * indent
            if emoji:
                print(f"{indent_str}{emoji} {message}")
            else:
                print(f"{indent_str}{message}")

    def progress(self, current: int, total: int, item: str, status_emoji: str = ""):
        """
        Log progress with timestamp and percentage.

        Args:
            current: Current item number
            total: Total number of items
            item: Description of current item
            status_emoji: Status emoji (✓, ⚠️, ❌, etc.)
        """
        percent = (current / total * 100) if total > 0 else 0
        timestamp = datetime.now().strftime("%H:%M:%S")

        # File log: structured with progress metadata
        self.logger.info(
            f"Progress: {current}/{total} ({percent:.1f}%) - {item}",
            extra={
                "progress": {
                    "current": current,
                    "total": total,
                    "percent": percent,
                    "item": item,
                    "status": status_emoji,
                }
            },
        )

        # Console: formatted with timestamp
        if self.interactive:
            msg = f"[{timestamp}] Progress: {current}/{total} ({percent:.1f}%) - {status_emoji} {item}"
            print(msg)

    def section(self, title: str, width: int = 70, emoji: Optional[str] = None):
        """
        Print a section header with separator lines.

        Args:
            title: Section title
            width: Width of separator line
            emoji: Optional emoji to prefix title
        """
        # File log: mark section boundary
        self.logger.info(f"Section: {title}", extra={"section": title, "emoji": emoji})

        # Console: formatted with separators
        if self.interactive:
            print()
            print("=" * width)
            if emoji:
                print(f"{emoji} {title}")
            else:
                print(title)
            print("=" * width)
            print()

    def warning(self, message: str, emoji: str = "⚠️", indent: int = 0):
        """
        Log a warning message.

        Args:
            message: The warning message
            emoji: Warning emoji (default: ⚠️)
            indent: Number of spaces to indent
        """
        # File log: structured warning
        self.logger.warning(message, extra={"emoji": emoji, "indent": indent})

        # Console: with emoji if interactive
        if self.interactive:
            indent_str = " " * indent
            print(f"{indent_str}{emoji} {message}")

    def error(self, message: str, emoji: str = "❌", indent: int = 0):
        """
        Log an error message.

        Args:
            message: The error message
            emoji: Error emoji (default: ❌)
            indent: Number of spaces to indent
        """
        # File log: structured error
        self.logger.error(message, extra={"emoji": emoji, "indent": indent})

        # Console: with emoji if interactive
        if self.interactive:
            indent_str = " " * indent
            print(f"{indent_str}{emoji} {message}")

    def success(self, message: str, emoji: str = "✅", indent: int = 0):
        """
        Log a success message.

        Args:
            message: The success message
            emoji: Success emoji (default: ✅)
            indent: Number of spaces to indent
        """
        self.info(message, emoji=emoji, indent=indent)

    def debug(self, message: str, indent: int = 0):
        """
        Log a debug message (only when debug logging is enabled).

        Args:
            message: The debug message
            indent: Number of spaces to indent
        """
        # File log: debug level
        self.logger.debug(message, extra={"indent": indent})

        # Console: only in interactive mode with debug enabled
        if self.interactive and self.logger.isEnabledFor(logging.DEBUG):
            indent_str = " " * indent
            print(f"{indent_str}[DEBUG] {message}")
