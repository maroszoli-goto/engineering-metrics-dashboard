"""Tests for performance monitoring utilities."""

import logging
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.utils.performance import _detect_cache_hit, timed_api_call, timed_operation, timed_route


class TestTimedRoute:
    """Tests for timed_route decorator."""

    def test_basic_timing(self, caplog):
        """Test basic route timing functionality."""

        @timed_route
        def sample_route():
            time.sleep(0.01)  # 10ms
            return "response"

        with caplog.at_level(logging.INFO):
            result = sample_route()

        assert result == "response"
        assert len(caplog.records) == 1
        assert "[PERF] Route timing" in caplog.records[0].message
        assert caplog.records[0].type == "route"
        assert caplog.records[0].route == "sample_route"
        assert caplog.records[0].duration_ms >= 10.0
        assert caplog.records[0].status_code == 200

    def test_timing_with_response_object(self, caplog):
        """Test timing with Flask response object."""
        mock_response = Mock()
        mock_response.status_code = 201

        @timed_route
        def sample_route():
            return mock_response

        with caplog.at_level(logging.INFO):
            result = sample_route()

        assert result == mock_response
        assert caplog.records[0].status_code == 201

    def test_timing_with_tuple_response(self, caplog):
        """Test timing with tuple response (body, status_code)."""

        @timed_route
        def sample_route():
            return "response", 404

        with caplog.at_level(logging.INFO):
            result = sample_route()

        assert result == ("response", 404)
        assert caplog.records[0].status_code == 404

    def test_timing_with_args_and_kwargs(self, caplog):
        """Test timing captures route arguments."""

        @timed_route
        def sample_route(arg1, kwarg1=None):
            return f"{arg1}-{kwarg1}"

        with caplog.at_level(logging.INFO):
            result = sample_route("test", kwarg1="value")

        assert result == "test-value"
        assert "'test'" in caplog.records[0].route_args
        assert caplog.records[0].kwargs == {"kwarg1": "value"}

    def test_timing_with_error(self, caplog):
        """Test timing logs errors correctly."""

        @timed_route
        def sample_route():
            raise ValueError("test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError, match="test error"):
                sample_route()

        assert len(caplog.records) == 1
        assert "[PERF] Route error" in caplog.records[0].message
        assert caplog.records[0].status_code == 500
        assert caplog.records[0].error == "test error"
        assert caplog.records[0].error_type == "ValueError"

    def test_cache_hit_detection(self, caplog):
        """Test cache hit detection in route timing."""

        @timed_route
        def sample_route(team_name=None):
            return "response"

        with caplog.at_level(logging.INFO):
            sample_route(team_name="TestTeam")

        assert caplog.records[0].cache_hit is True

    def test_cache_miss_detection(self, caplog):
        """Test cache miss detection in route timing."""

        @timed_route
        def sample_route(other_param=None):
            return "response"

        with caplog.at_level(logging.INFO):
            sample_route(other_param="value")

        assert caplog.records[0].cache_hit is False


class TestTimedApiCall:
    """Tests for timed_api_call decorator."""

    def test_basic_api_timing(self, caplog):
        """Test basic API call timing."""

        @timed_api_call("test_operation")
        def sample_api_call():
            time.sleep(0.01)
            return {"data": "result"}

        with caplog.at_level(logging.INFO):
            result = sample_api_call()

        assert result == {"data": "result"}
        assert len(caplog.records) == 1
        assert "[PERF] API call: test_operation" in caplog.records[0].message
        assert caplog.records[0].type == "api_call"
        assert caplog.records[0].operation == "test_operation"
        assert caplog.records[0].duration_ms >= 10.0
        assert caplog.records[0].success is True

    def test_api_call_with_error(self, caplog):
        """Test API call timing with error."""

        @timed_api_call("test_operation")
        def sample_api_call():
            raise ConnectionError("API error")

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ConnectionError, match="API error"):
                sample_api_call()

        assert len(caplog.records) == 1
        assert "[PERF] API call failed" in caplog.records[0].message
        assert caplog.records[0].success is False
        assert caplog.records[0].error == "API error"
        assert caplog.records[0].error_type == "ConnectionError"

    def test_api_call_preserves_return_value(self):
        """Test API call decorator preserves return values."""

        @timed_api_call("test_operation")
        def sample_api_call(x, y):
            return x + y

        result = sample_api_call(3, 4)
        assert result == 7


class TestTimedOperation:
    """Tests for timed_operation context manager."""

    def test_basic_operation_timing(self, caplog):
        """Test basic operation timing."""
        with caplog.at_level(logging.INFO):
            with timed_operation("test_operation"):
                time.sleep(0.01)

        assert len(caplog.records) == 1
        assert "[PERF] Operation: test_operation" in caplog.records[0].message
        assert caplog.records[0].type == "operation"
        assert caplog.records[0].operation == "test_operation"
        assert caplog.records[0].duration_ms >= 10.0
        assert caplog.records[0].success is True

    def test_operation_with_metadata(self, caplog):
        """Test operation timing with metadata."""
        with caplog.at_level(logging.INFO):
            with timed_operation("database_query", {"table": "metrics", "rows": 100}):
                time.sleep(0.01)

        assert caplog.records[0].table == "metrics"
        assert caplog.records[0].rows == 100

    def test_operation_with_error(self, caplog):
        """Test operation timing with error."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError, match="test error"):
                with timed_operation("test_operation"):
                    raise RuntimeError("test error")

        assert len(caplog.records) == 1
        assert "[PERF] Operation failed" in caplog.records[0].message
        assert caplog.records[0].success is False
        assert caplog.records[0].error == "test error"
        assert caplog.records[0].error_type == "RuntimeError"

    def test_operation_with_error_and_metadata(self, caplog):
        """Test operation error includes metadata."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                with timed_operation("test_operation", {"param": "value"}):
                    raise ValueError("error")

        assert caplog.records[0].param == "value"
        assert caplog.records[0].error_type == "ValueError"


class TestDetectCacheHit:
    """Tests for _detect_cache_hit helper."""

    def test_cache_hit_with_env(self):
        """Test cache hit detection with env parameter."""
        assert _detect_cache_hit({"env": "prod"}) is True

    def test_cache_hit_with_range(self):
        """Test cache hit detection with range parameter."""
        assert _detect_cache_hit({"range": "90d"}) is True

    def test_cache_hit_with_team_name(self):
        """Test cache hit detection with team_name parameter."""
        assert _detect_cache_hit({"team_name": "Backend"}) is True

    def test_cache_miss(self):
        """Test cache miss detection."""
        assert _detect_cache_hit({"other": "value"}) is False

    def test_cache_miss_empty(self):
        """Test cache miss with empty kwargs."""
        assert _detect_cache_hit({}) is False


class TestPerformanceIntegration:
    """Integration tests for performance monitoring."""

    def test_nested_timing(self, caplog):
        """Test nested timing operations."""

        @timed_route
        def outer_route():
            with timed_operation("inner_operation"):
                time.sleep(0.01)
            return "done"

        with caplog.at_level(logging.INFO):
            result = outer_route()

        assert result == "done"
        assert len(caplog.records) == 2
        assert caplog.records[0].operation == "inner_operation"
        assert caplog.records[1].route == "outer_route"

    def test_multiple_api_calls_in_route(self, caplog):
        """Test multiple API calls within a route."""

        @timed_api_call("api_call_1")
        def api_call_1():
            return "result1"

        @timed_api_call("api_call_2")
        def api_call_2():
            return "result2"

        @timed_route
        def route_with_api_calls():
            r1 = api_call_1()
            r2 = api_call_2()
            return f"{r1}-{r2}"

        with caplog.at_level(logging.INFO):
            result = route_with_api_calls()

        assert result == "result1-result2"
        assert len(caplog.records) == 3
        assert caplog.records[0].operation == "api_call_1"
        assert caplog.records[1].operation == "api_call_2"
        assert caplog.records[2].route == "route_with_api_calls"
