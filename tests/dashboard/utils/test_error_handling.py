"""Tests for error handling utilities"""

import json
from unittest.mock import MagicMock

import pytest
from flask import Flask

from src.dashboard.utils.error_handling import handle_api_error, set_logger


class TestHandleApiError:
    """Test handle_api_error function"""

    def setup_method(self):
        """Set up test logger and Flask app"""
        self.mock_logger = MagicMock()
        set_logger(self.mock_logger)
        # Create Flask app for testing
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown_method(self):
        """Clean up Flask app context"""
        self.app_context.pop()

    def test_returns_500_status_code(self):
        """Should return HTTP 500 status code"""
        response, status_code = handle_api_error(ValueError("test error"), "test context")
        assert status_code == 500

    def test_returns_json_response(self):
        """Should return JSON response with error field"""
        response, _ = handle_api_error(ValueError("test error"), "test context")
        data = json.loads(response.get_data(as_text=True))
        assert "error" in data
        assert data["error"] == "An error occurred while processing your request"

    def test_logs_error_message(self):
        """Should log error message with context"""
        handle_api_error(ValueError("test error"), "API refresh")
        self.mock_logger.error.assert_any_call("API refresh failed: test error")

    def test_logs_traceback(self):
        """Should log full traceback"""
        handle_api_error(ValueError("test error"), "test context")
        # Check that error was called twice (once for message, once for traceback)
        assert self.mock_logger.error.call_count == 2

    def test_generic_error_message_prevents_information_leakage(self):
        """Should not expose internal error details to user"""
        response, _ = handle_api_error(ValueError("Internal database password is wrong"), "database operation")
        data = json.loads(response.get_data(as_text=True))
        # Should not contain internal details
        assert "password" not in data["error"]
        assert "database" not in data["error"]
        # Should be generic
        assert data["error"] == "An error occurred while processing your request"

    def test_handles_different_exception_types(self):
        """Should handle various exception types"""
        exceptions = [ValueError("test"), TypeError("test"), RuntimeError("test"), Exception("test")]

        for exc in exceptions:
            response, status_code = handle_api_error(exc, "test")
            assert status_code == 500
            data = json.loads(response.get_data(as_text=True))
            assert "error" in data

    def test_context_parameter_in_log_message(self):
        """Should include context in log message"""
        contexts = ["Metrics refresh", "Cache reload", "Data collection", "Export generation"]

        for context in contexts:
            handle_api_error(ValueError("test"), context)
            # Check that context was included in error log
            call_args = self.mock_logger.error.call_args_list
            assert any(context in str(call) for call in call_args)

    def test_works_without_logger(self):
        """Should not crash when logger is not set"""
        set_logger(None)
        response, status_code = handle_api_error(ValueError("test"), "test")
        assert status_code == 500

    def test_preserves_exception_chain(self):
        """Should log exception chain for chained exceptions"""
        try:
            try:
                raise ValueError("original error")
            except ValueError as e:
                raise RuntimeError("wrapped error") from e
        except RuntimeError as e:
            handle_api_error(e, "test")

        # Should have logged both error message and traceback
        assert self.mock_logger.error.call_count == 2
