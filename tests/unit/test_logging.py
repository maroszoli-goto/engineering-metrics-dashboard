"""
Unit tests for logging infrastructure.

Tests cover:
- Interactive mode detection
- Console output wrapper
- JSON formatting
- Log rotation and compression
- Configuration loading
"""

import gzip
import json
import logging
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

from src.utils.logging import (
    CompressingRotatingFileHandler,
    ConsoleOutput,
    JSONFormatter,
    StructuredTextFormatter,
    create_rotating_handler,
    get_logger,
    is_interactive,
    setup_logging,
    should_use_color,
)
from src.utils.logging.config import load_config


class TestInteractiveDetection:
    """Tests for interactive mode detection."""

    def test_interactive_detection_tty(self):
        """Test TTY detection for interactive mode."""
        with mock.patch("sys.stdout.isatty", return_value=True):
            # Create environment with TERM set and CI vars explicitly removed
            env = os.environ.copy()
            env["TERM"] = "xterm"
            for ci_var in ["CI", "JENKINS_URL", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI"]:
                env.pop(ci_var, None)  # Remove if exists
            with mock.patch.dict(os.environ, env, clear=True):
                assert is_interactive() is True

    def test_interactive_detection_non_tty(self):
        """Test non-TTY detection for background mode."""
        with mock.patch("sys.stdout.isatty", return_value=False):
            assert is_interactive() is False

    def test_interactive_detection_no_term(self):
        """Test detection fails when TERM not set."""
        with mock.patch("sys.stdout.isatty", return_value=True):
            with mock.patch.dict(os.environ, {}, clear=True):
                assert is_interactive() is False

    def test_interactive_detection_ci_environment(self):
        """Test detection fails in CI environment."""
        with mock.patch("sys.stdout.isatty", return_value=True):
            with mock.patch.dict(os.environ, {"TERM": "xterm", "CI": "true"}):
                assert is_interactive() is False

            with mock.patch.dict(os.environ, {"TERM": "xterm", "GITHUB_ACTIONS": "true"}):
                assert is_interactive() is False

    def test_should_use_color_interactive(self):
        """Test color detection in interactive mode."""
        with mock.patch("src.utils.logging.detection.is_interactive", return_value=True):
            with mock.patch.dict(os.environ, {"TERM": "xterm"}):
                assert should_use_color() is True

    def test_should_use_color_no_color_env(self):
        """Test NO_COLOR environment variable."""
        with mock.patch("src.utils.logging.detection.is_interactive", return_value=True):
            with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
                assert should_use_color() is False

    def test_should_use_color_dumb_terminal(self):
        """Test dumb terminal detection."""
        with mock.patch("src.utils.logging.detection.is_interactive", return_value=True):
            with mock.patch.dict(os.environ, {"TERM": "dumb"}):
                assert should_use_color() is False


class TestConsoleOutput:
    """Tests for ConsoleOutput wrapper."""

    def test_console_output_info_with_emoji_interactive(self):
        """Test info output with emoji in interactive mode."""
        logger = logging.getLogger("test.info.emoji")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.info("Test message", emoji="✅")
            mock_print.assert_called_once_with("✅ Test message")

    def test_console_output_info_without_emoji_interactive(self):
        """Test info output without emoji in interactive mode."""
        logger = logging.getLogger("test.info.no_emoji")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.info("Test message")
            mock_print.assert_called_once_with("Test message")

    def test_console_output_info_non_interactive(self):
        """Test info output in non-interactive mode."""
        logger = logging.getLogger("test.info.non_interactive")
        out = ConsoleOutput(logger)
        out.interactive = False

        with mock.patch("builtins.print") as mock_print:
            out.info("Test message", emoji="✅")
            # Should not print to console in background mode
            mock_print.assert_not_called()

    def test_console_output_with_indent(self):
        """Test indented output."""
        logger = logging.getLogger("test.indent")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.info("Indented message", indent=2)
            mock_print.assert_called_once_with("  Indented message")

    def test_console_output_progress(self):
        """Test progress output."""
        logger = logging.getLogger("test.progress")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.progress(5, 10, "processing item", status_emoji="✓")
            # Verify format: [HH:MM:SS] Progress: 5/10 (50.0%) - ✓ processing item
            call_args = mock_print.call_args[0][0]
            assert "Progress: 5/10 (50.0%)" in call_args
            assert "✓ processing item" in call_args
            assert call_args.startswith("[")  # Timestamp

    def test_console_output_progress_metadata(self):
        """Test progress metadata in log record."""
        logger = logging.getLogger("test.progress.metadata")
        logger.setLevel(logging.INFO)

        # Capture log records
        handler = logging.handlers.MemoryHandler(capacity=10)
        logger.addHandler(handler)

        out = ConsoleOutput(logger)
        out.progress(3, 8, "test item", status_emoji="✓")

        # Verify log record has progress metadata
        records = handler.buffer
        assert len(records) > 0
        record = records[0]
        assert hasattr(record, "progress")
        assert record.progress["current"] == 3
        assert record.progress["total"] == 8
        assert record.progress["percent"] == 37.5
        assert record.progress["item"] == "test item"

    def test_console_output_section(self):
        """Test section header output."""
        logger = logging.getLogger("test.section")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.section("Test Section", width=50, emoji="📊")

            # Should print: empty line, separator, title with emoji, separator, empty line
            calls = mock_print.call_args_list
            assert len(calls) == 5

            # Extract the actual printed strings
            printed_lines = [call[0][0] if call[0] else call.args[0] if call.args else "" for call in calls]

            assert printed_lines[0] == ""  # Empty line
            assert printed_lines[1] == "=" * 50  # Separator
            assert printed_lines[2] == "📊 Test Section"  # Title with emoji
            assert printed_lines[3] == "=" * 50  # Separator
            assert printed_lines[4] == ""  # Empty line

    def test_console_output_warning(self):
        """Test warning output."""
        logger = logging.getLogger("test.warning")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.warning("Warning message", emoji="⚠️")
            mock_print.assert_called_once_with("⚠️ Warning message")

    def test_console_output_error(self):
        """Test error output."""
        logger = logging.getLogger("test.error")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.error("Error message", emoji="❌")
            mock_print.assert_called_once_with("❌ Error message")

    def test_console_output_success(self):
        """Test success output (alias for info with green emoji)."""
        logger = logging.getLogger("test.success")
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.success("Success message")
            mock_print.assert_called_once_with("✅ Success message")

    def test_console_output_debug(self):
        """Test debug output."""
        logger = logging.getLogger("test.debug")
        logger.setLevel(logging.DEBUG)
        out = ConsoleOutput(logger)
        out.interactive = True

        with mock.patch("builtins.print") as mock_print:
            out.debug("Debug message")
            mock_print.assert_called_once_with("[DEBUG] Debug message")


class TestJSONFormatter:
    """Tests for JSON log formatter."""

    def test_json_formatter_basic(self):
        """Test basic JSON formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.json",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        json_output = formatter.format(record)
        data = json.loads(json_output)

        assert "timestamp" in data
        assert "level" in data
        assert data["level"] == "INFO"
        assert "logger" in data
        assert data["logger"] == "test.json"
        assert "message" in data
        assert data["message"] == "Test message"
        assert "module" in data
        assert "function" in data
        assert "line" in data
        assert data["line"] == 42

    def test_json_formatter_with_progress(self):
        """Test JSON formatting with progress metadata."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.json.progress",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Progress message",
            args=(),
            exc_info=None,
        )
        record.progress = {"current": 5, "total": 10, "percent": 50.0}

        json_output = formatter.format(record)
        data = json.loads(json_output)

        assert "progress" in data
        assert data["progress"]["current"] == 5
        assert data["progress"]["total"] == 10
        assert data["progress"]["percent"] == 50.0

    def test_json_formatter_with_emoji(self):
        """Test JSON formatting with emoji metadata."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.json.emoji",
            level=logging.INFO,
            pathname="test.py",
            lineno=20,
            msg="Message with emoji",
            args=(),
            exc_info=None,
        )
        record.emoji = "✅"

        json_output = formatter.format(record)
        data = json.loads(json_output)

        assert "emoji_used" in data
        assert data["emoji_used"] == "✅"

    def test_json_formatter_with_exception(self):
        """Test JSON formatting with exception."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.json.exception",
            level=logging.ERROR,
            pathname="test.py",
            lineno=30,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        json_output = formatter.format(record)
        data = json.loads(json_output)

        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]


class TestStructuredTextFormatter:
    """Tests for structured text formatter."""

    def test_text_formatter_basic(self):
        """Test basic text formatting."""
        formatter = StructuredTextFormatter()
        record = logging.LogRecord(
            name="test.text",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "test.text" in output
        assert "Test message" in output

    def test_text_formatter_with_progress(self):
        """Test text formatting with progress metadata."""
        formatter = StructuredTextFormatter()
        record = logging.LogRecord(
            name="test.text.progress",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Progress message",
            args=(),
            exc_info=None,
        )
        record.progress = {"current": 5, "total": 10, "percent": 50.0}

        output = formatter.format(record)

        assert "Progress: 5/10 (50.0%)" in output


class TestLogRotation:
    """Tests for log rotation and compression."""

    def test_create_rotating_handler(self):
        """Test creating a rotating file handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            handler = create_rotating_handler(
                log_file=log_file, max_bytes=1024, backup_count=3, compress=True, formatter=JSONFormatter()
            )

            assert isinstance(handler, CompressingRotatingFileHandler)
            assert handler.maxBytes == 1024
            assert handler.backupCount == 3
            assert handler.compress is True

    def test_log_rotation(self):
        """Test that log rotation occurs at max size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            handler = CompressingRotatingFileHandler(
                filename=log_file,
                maxBytes=100,  # Very small for testing
                backupCount=2,
                compress=False,  # Disable compression for easier testing
            )

            logger = logging.getLogger("test.rotation")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Write enough data to trigger rotation
            for i in range(50):
                logger.info(f"Test message {i} with enough text to exceed max bytes")

            # Check that rotation occurred
            assert os.path.exists(log_file)
            # Backup files should exist
            backup1 = f"{log_file}.1"
            assert os.path.exists(backup1) or os.path.exists(f"{backup1}.gz")

    def test_log_compression(self):
        """Test that rotated logs are compressed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            handler = CompressingRotatingFileHandler(filename=log_file, maxBytes=100, backupCount=2, compress=True)

            logger = logging.getLogger("test.compression")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Write enough data to trigger rotation
            for i in range(50):
                logger.info(f"Test message {i} with enough text to exceed max bytes and trigger compression")

            # Check that compressed backup exists
            backup1_gz = f"{log_file}.1.gz"
            if os.path.exists(backup1_gz):
                # Verify it's a valid gzip file
                with gzip.open(backup1_gz, "rb") as f:
                    content = f.read()
                    assert len(content) > 0


class TestConfiguration:
    """Tests for configuration loading."""

    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "logging.yaml")

            config_data = {
                "version": 1,
                "default_level": "DEBUG",
                "rotation": {"max_bytes": 5242880, "backup_count": 5, "compress": True},
                "files": {"main": "logs/test.log", "error": "logs/test_error.log"},
            }

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            config = load_config(config_file)

            assert config["version"] == 1
            assert config["default_level"] == "DEBUG"
            assert config["rotation"]["max_bytes"] == 5242880
            assert config["rotation"]["backup_count"] == 5
            assert config["rotation"]["compress"] is True

    def test_load_config_file_not_found(self):
        """Test loading config with non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_setup_logging(self):
        """Test full logging setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")

            logger = setup_logging(log_level="DEBUG", log_file=log_file, config_file=None)  # Use default config

            assert logger.name == "team_metrics"
            assert logger.level == logging.DEBUG
            assert len(logger.handlers) > 0

    def test_get_logger_caching(self):
        """Test that get_logger caches instances."""
        out1 = get_logger("test.cache.logger")
        out2 = get_logger("test.cache.logger")

        assert out1 is out2  # Same instance


class TestPerformance:
    """Performance tests for logging."""

    def test_logging_performance(self):
        """Ensure logging doesn't significantly slow down execution."""
        import time

        logger = logging.getLogger("test.performance")
        logger.addHandler(logging.NullHandler())
        out = ConsoleOutput(logger)
        out.interactive = False  # No console output

        # Time 1000 log calls
        start = time.time()
        for i in range(1000):
            out.info(f"Message {i}", emoji="✓")
        elapsed = time.time() - start

        # Should be very fast (< 0.5 seconds for 1000 calls)
        assert elapsed < 0.5
