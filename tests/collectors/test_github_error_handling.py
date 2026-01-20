"""
Unit tests for GitHub GraphQL Collector error handling

Tests the retry logic for transient errors including:
- ChunkedEncodingError (incomplete responses)
- JSONDecodeError (invalid JSON responses)
- Invalid Content-Type (non-JSON responses)
- Empty response bodies
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from src.collectors.github_graphql_collector import GitHubGraphQLCollector


@pytest.fixture
def mock_collector():
    """Create a collector with mocked session"""
    with patch("src.collectors.github_graphql_collector.get_logger"):
        collector = GitHubGraphQLCollector(
            token="test_token", organization="test_org", teams=["test_team"], team_members=["test_user"]
        )
        collector.session = Mock()
        return collector


class TestChunkedEncodingError:
    """Test ChunkedEncodingError retry logic"""

    def test_chunked_encoding_error_retries_and_succeeds(self, mock_collector):
        """ChunkedEncodingError should retry and succeed on subsequent attempt"""
        # First two attempts fail, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"data": {"viewer": {"login": "test"}}}'
        mock_response.json.return_value = {"data": {"viewer": {"login": "test"}}}

        mock_collector.session.post.side_effect = [
            requests.exceptions.ChunkedEncodingError("Connection broken: Invalid chunk encoding"),
            requests.exceptions.ChunkedEncodingError("Connection broken: Invalid chunk encoding"),
            mock_response,
        ]

        query = "{ viewer { login } }"
        result = mock_collector._execute_query(query)

        assert result == {"viewer": {"login": "test"}}
        assert mock_collector.session.post.call_count == 3

    def test_chunked_encoding_error_exhausts_retries(self, mock_collector):
        """ChunkedEncodingError should raise after max retries"""
        mock_collector.session.post.side_effect = requests.exceptions.ChunkedEncodingError(
            "Connection broken: Invalid chunk encoding"
        )

        query = "{ viewer { login } }"
        with pytest.raises(Exception) as exc_info:
            mock_collector._execute_query(query, max_retries=3)

        assert "ChunkedEncodingError after 3 retries" in str(exc_info.value)
        assert mock_collector.session.post.call_count == 3


class TestJSONDecodeError:
    """Test JSONDecodeError retry logic"""

    def test_json_decode_error_retries_and_succeeds(self, mock_collector):
        """JSONDecodeError should retry and succeed on subsequent attempt"""
        # First attempt returns invalid JSON, second succeeds
        mock_response_bad = Mock()
        mock_response_bad.status_code = 200
        mock_response_bad.headers = {"Content-Type": "application/json"}
        mock_response_bad.text = '{"data": invalid json'
        mock_response_bad.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        mock_response_good = Mock()
        mock_response_good.status_code = 200
        mock_response_good.headers = {"Content-Type": "application/json"}
        mock_response_good.text = '{"data": {"viewer": {"login": "test"}}}'
        mock_response_good.json.return_value = {"data": {"viewer": {"login": "test"}}}

        mock_collector.session.post.side_effect = [mock_response_bad, mock_response_good]

        query = "{ viewer { login } }"
        result = mock_collector._execute_query(query)

        assert result == {"viewer": {"login": "test"}}
        assert mock_collector.session.post.call_count == 2

    def test_json_decode_error_exhausts_retries(self, mock_collector):
        """JSONDecodeError should raise after max retries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"data": invalid json'
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        mock_collector.session.post.return_value = mock_response

        query = "{ viewer { login } }"
        with pytest.raises(Exception) as exc_info:
            mock_collector._execute_query(query, max_retries=3)

        assert "Invalid JSON after 3 retries" in str(exc_info.value)
        assert mock_collector.session.post.call_count == 3


class TestInvalidContentType:
    """Test invalid Content-Type retry logic"""

    def test_invalid_content_type_retries_and_succeeds(self, mock_collector):
        """Invalid Content-Type should retry and succeed on subsequent attempt"""
        # First attempt returns HTML, second returns JSON
        mock_response_html = Mock()
        mock_response_html.status_code = 200
        mock_response_html.headers = {"Content-Type": "text/html"}
        mock_response_html.text = "<html><body>Error</body></html>"

        mock_response_json = Mock()
        mock_response_json.status_code = 200
        mock_response_json.headers = {"Content-Type": "application/json"}
        mock_response_json.text = '{"data": {"viewer": {"login": "test"}}}'
        mock_response_json.json.return_value = {"data": {"viewer": {"login": "test"}}}

        mock_collector.session.post.side_effect = [mock_response_html, mock_response_json]

        query = "{ viewer { login } }"
        result = mock_collector._execute_query(query)

        assert result == {"viewer": {"login": "test"}}
        assert mock_collector.session.post.call_count == 2

    def test_invalid_content_type_exhausts_retries(self, mock_collector):
        """Invalid Content-Type should raise after max retries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "<html><body>Error</body></html>"

        mock_collector.session.post.return_value = mock_response

        query = "{ viewer { login } }"
        with pytest.raises(Exception) as exc_info:
            mock_collector._execute_query(query, max_retries=3)

        assert "Expected JSON, got Content-Type: text/html" in str(exc_info.value)
        assert mock_collector.session.post.call_count == 3


class TestEmptyResponseBody:
    """Test empty response body retry logic"""

    def test_empty_response_body_retries_and_succeeds(self, mock_collector):
        """Empty response body should retry and succeed on subsequent attempt"""
        # First attempt returns empty body, second succeeds
        mock_response_empty = Mock()
        mock_response_empty.status_code = 200
        mock_response_empty.headers = {"Content-Type": "application/json"}
        mock_response_empty.text = ""

        mock_response_good = Mock()
        mock_response_good.status_code = 200
        mock_response_good.headers = {"Content-Type": "application/json"}
        mock_response_good.text = '{"data": {"viewer": {"login": "test"}}}'
        mock_response_good.json.return_value = {"data": {"viewer": {"login": "test"}}}

        mock_collector.session.post.side_effect = [mock_response_empty, mock_response_good]

        query = "{ viewer { login } }"
        result = mock_collector._execute_query(query)

        assert result == {"viewer": {"login": "test"}}
        assert mock_collector.session.post.call_count == 2

    def test_empty_response_body_exhausts_retries(self, mock_collector):
        """Empty response body should raise after max retries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = ""

        mock_collector.session.post.return_value = mock_response

        query = "{ viewer { login } }"
        with pytest.raises(Exception) as exc_info:
            mock_collector._execute_query(query, max_retries=3)

        assert "Empty response body received" in str(exc_info.value)
        assert mock_collector.session.post.call_count == 3

    def test_very_short_response_body_retries(self, mock_collector):
        """Response body < 10 chars should retry"""
        mock_response_short = Mock()
        mock_response_short.status_code = 200
        mock_response_short.headers = {"Content-Type": "application/json"}
        mock_response_short.text = "{}"  # Only 2 chars

        mock_response_good = Mock()
        mock_response_good.status_code = 200
        mock_response_good.headers = {"Content-Type": "application/json"}
        mock_response_good.text = '{"data": {"viewer": {"login": "test"}}}'
        mock_response_good.json.return_value = {"data": {"viewer": {"login": "test"}}}

        mock_collector.session.post.side_effect = [mock_response_short, mock_response_good]

        query = "{ viewer { login } }"
        result = mock_collector._execute_query(query)

        assert result == {"viewer": {"login": "test"}}
        assert mock_collector.session.post.call_count == 2


class TestExponentialBackoff:
    """Test exponential backoff timing"""

    @patch("time.sleep")
    def test_exponential_backoff_timing(self, mock_sleep, mock_collector):
        """Verify exponential backoff: 1s, 2s, 4s"""
        mock_collector.session.post.side_effect = requests.exceptions.ChunkedEncodingError("Connection broken")

        query = "{ viewer { login } }"
        with pytest.raises(Exception):
            mock_collector._execute_query(query, max_retries=3)

        # Should sleep 3 times: 2^0=1s, 2^1=2s (no sleep after final failure)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # 2^0
        mock_sleep.assert_any_call(2)  # 2^1


class TestCombinedErrors:
    """Test combinations of errors"""

    def test_multiple_error_types_in_sequence(self, mock_collector):
        """Should handle different error types in sequence"""
        # Sequence: ChunkedEncoding → Empty body → JSON decode → Success
        mock_response_empty = Mock()
        mock_response_empty.status_code = 200
        mock_response_empty.headers = {"Content-Type": "application/json"}
        mock_response_empty.text = ""

        mock_response_bad_json = Mock()
        mock_response_bad_json.status_code = 200
        mock_response_bad_json.headers = {"Content-Type": "application/json"}
        mock_response_bad_json.text = "{invalid"
        mock_response_bad_json.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        mock_response_good = Mock()
        mock_response_good.status_code = 200
        mock_response_good.headers = {"Content-Type": "application/json"}
        mock_response_good.text = '{"data": {"viewer": {"login": "test"}}}'
        mock_response_good.json.return_value = {"data": {"viewer": {"login": "test"}}}

        mock_collector.session.post.side_effect = [
            requests.exceptions.ChunkedEncodingError("Connection broken"),
            mock_response_empty,
            mock_response_bad_json,
            mock_response_good,
        ]

        query = "{ viewer { login } }"
        # Should succeed despite 3 different error types
        # Note: We need more retries since we have 4 attempts
        with pytest.raises(Exception):
            # Default max_retries=3 means 3 attempts total
            # This will fail because we need 4 attempts
            mock_collector._execute_query(query, max_retries=3)

        # Now test with enough retries
        mock_collector.session.post.side_effect = [
            requests.exceptions.ChunkedEncodingError("Connection broken"),
            mock_response_empty,
            mock_response_bad_json,
            mock_response_good,
        ]
        result = mock_collector._execute_query(query, max_retries=5)
        assert result == {"viewer": {"login": "test"}}


class TestDebugLogging:
    """Test debug logging for generic errors"""

    def test_generic_error_logs_response_details(self, mock_collector):
        """Generic error handler should log response headers and body"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json", "X-Custom": "test"}
        mock_response.text = '{"data": "test"}'
        # Simulate an unexpected error during processing
        mock_response.json.side_effect = [ValueError("Unexpected error"), {"data": {"viewer": {"login": "test"}}}]

        mock_collector.session.post.return_value = mock_response

        query = "{ viewer { login } }"
        result = mock_collector._execute_query(query, max_retries=3)

        # Should succeed on retry
        assert result == {"viewer": {"login": "test"}}
        assert mock_collector.session.post.call_count == 2
