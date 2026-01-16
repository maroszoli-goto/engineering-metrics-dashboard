"""
Logging infrastructure for Team Metrics Dashboard.

This package provides a dual-output logging system that adapts to the execution environment:

**Interactive Mode** (when running in terminal):
- Colorful console output with emojis (✅ ❌ ⚠️ 📊)
- Real-time progress indicators: [HH:MM:SS] Progress: 5/10 (50%) - item
- Section banners and indentation

**Background Mode** (cron, launchd, redirected output):
- Structured JSON logs for parsing
- No emojis or colors
- Machine-readable format

Usage:
    >>> from src.utils.logging import setup_logging, get_logger
    >>>
    >>> # Setup logging (do this once at startup)
    >>> setup_logging(log_level='INFO', config_file='config/logging.yaml')
    >>>
    >>> # Get a logger instance
    >>> out = get_logger('team_metrics.collection')
    >>>
    >>> # Log messages with emojis (auto-adapts to interactive/background)
    >>> out.section("Data Collection")
    >>> out.info("Connected to GitHub", emoji="✅")
    >>> out.progress(5, 10, "processing repos", status_emoji="✓")
    >>> out.warning("Rate limit approaching", emoji="⚠️")
    >>> out.error("Failed to fetch data", emoji="❌")

Configuration:
    Logging behavior is configured via config/logging.yaml:
    - Log levels per module
    - File rotation settings (size, backup count, compression)
    - Log file paths

Features:
    - Automatic TTY detection (no manual configuration needed)
    - Log rotation with gzip compression (10MB files, 10 backups)
    - JSON structured logs for machine parsing
    - Thread-safe for parallel execution
    - Module-level loggers with hierarchy (team_metrics.collectors.github, etc.)
"""

from .config import get_logger, setup_logging
from .console import ConsoleOutput
from .detection import is_interactive, should_use_color
from .formatters import JSONFormatter, StructuredTextFormatter
from .handlers import CompressingRotatingFileHandler, create_rotating_handler

__all__ = [
    # Main API
    "setup_logging",
    "get_logger",
    # Classes
    "ConsoleOutput",
    "JSONFormatter",
    "StructuredTextFormatter",
    "CompressingRotatingFileHandler",
    # Utilities
    "is_interactive",
    "should_use_color",
    "create_rotating_handler",
]

__version__ = "1.0.0"
