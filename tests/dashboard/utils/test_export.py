"""Tests for export utilities"""

import json
from datetime import datetime

import pytest
from flask import Flask

from src.dashboard.utils.export import create_csv_response, create_json_response


class TestCreateCsvResponse:
    """Test create_csv_response function"""

    def setup_method(self):
        """Set up Flask app context"""
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown_method(self):
        """Clean up Flask app context"""
        self.app_context.pop()

    def test_creates_csv_from_list_of_dicts(self):
        """Should create CSV from list of flat dictionaries"""
        data = [{"name": "John", "score": 95}, {"name": "Jane", "score": 87}]
        response = create_csv_response(data, "test.csv")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert 'filename="test.csv"' in response.headers["Content-Disposition"]

        # Check CSV content
        csv_content = response.get_data(as_text=True)
        assert "name,score" in csv_content or "score,name" in csv_content
        assert "John" in csv_content
        assert "Jane" in csv_content

    def test_creates_csv_from_single_dict(self):
        """Should convert single dict to list automatically"""
        data = {"name": "John", "score": 95}
        response = create_csv_response(data, "test.csv")

        assert response.status_code == 200
        csv_content = response.get_data(as_text=True)
        assert "John" in csv_content

    def test_flattens_nested_dictionaries(self):
        """Should flatten nested dictionaries with dot notation"""
        data = [{"name": "John", "stats": {"score": 95, "rank": 1}}]
        response = create_csv_response(data, "test.csv")

        csv_content = response.get_data(as_text=True)
        assert "stats.score" in csv_content
        assert "stats.rank" in csv_content

    def test_handles_empty_data(self):
        """Should return 404 for empty data"""
        response = create_csv_response([], "test.csv")
        assert response.status_code == 404
        assert b"No data to export" in response.get_data()

    def test_formats_values_for_csv(self):
        """Should format values using format_value_for_csv"""
        data = [{"name": "John", "score": 95.567, "active": True}]
        response = create_csv_response(data, "test.csv")

        csv_content = response.get_data(as_text=True)
        assert "95.57" in csv_content  # Float rounded to 2 decimals
        assert "True" in csv_content  # Boolean as string

    def test_handles_datetime_values(self):
        """Should format datetime values"""
        data = [{"name": "John", "timestamp": datetime(2025, 1, 25, 14, 30, 0)}]
        response = create_csv_response(data, "test.csv")

        csv_content = response.get_data(as_text=True)
        assert "2025-01-25 14:30:00" in csv_content

    def test_handles_none_values(self):
        """Should handle None values as empty strings"""
        data = [{"name": "John", "score": None}]
        response = create_csv_response(data, "test.csv")

        csv_content = response.get_data(as_text=True)
        lines = csv_content.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row

    def test_consistent_column_order(self):
        """Should sort columns alphabetically for consistency"""
        data = [{"z": 1, "a": 2, "m": 3}]
        response = create_csv_response(data, "test.csv")

        csv_content = response.get_data(as_text=True)
        header = csv_content.split("\n")[0].strip()
        assert header == "a,m,z"

    def test_handles_missing_keys_across_rows(self):
        """Should handle rows with different keys"""
        data = [{"name": "John", "score": 95}, {"name": "Jane", "rank": 1}]
        response = create_csv_response(data, "test.csv")

        csv_content = response.get_data(as_text=True)
        # Should have all keys: name, rank, score
        assert "name" in csv_content
        assert "score" in csv_content
        assert "rank" in csv_content

    def test_utf8_encoding(self):
        """Should handle UTF-8 characters"""
        data = [{"name": "José", "city": "São Paulo"}]
        response = create_csv_response(data, "test.csv")

        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        csv_content = response.get_data(as_text=True)
        assert "José" in csv_content
        assert "São Paulo" in csv_content

    def test_filename_in_headers(self):
        """Should include filename in Content-Disposition header"""
        data = [{"name": "John"}]
        response = create_csv_response(data, "my_metrics_2025-01-25.csv")

        assert "my_metrics_2025-01-25.csv" in response.headers["Content-Disposition"]
        assert "attachment" in response.headers["Content-Disposition"]


class TestCreateJsonResponse:
    """Test create_json_response function"""

    def setup_method(self):
        """Set up Flask app context"""
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown_method(self):
        """Clean up Flask app context"""
        self.app_context.pop()

    def test_creates_json_from_dict(self):
        """Should create JSON response from dictionary"""
        data = {"name": "John", "score": 95}
        response = create_json_response(data, "test.json")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert 'filename="test.json"' in response.headers["Content-Disposition"]

        # Check JSON content
        json_content = json.loads(response.get_data(as_text=True))
        assert json_content["name"] == "John"
        assert json_content["score"] == 95

    def test_creates_json_from_list(self):
        """Should create JSON response from list"""
        data = [{"name": "John"}, {"name": "Jane"}]
        response = create_json_response(data, "test.json")

        assert response.status_code == 200
        json_content = json.loads(response.get_data(as_text=True))
        assert len(json_content) == 2

    def test_handles_nested_structures(self):
        """Should preserve nested structures"""
        data = {"person": {"name": "John", "address": {"city": "NYC"}}}
        response = create_json_response(data, "test.json")

        json_content = json.loads(response.get_data(as_text=True))
        assert json_content["person"]["address"]["city"] == "NYC"

    def test_formats_datetime_as_iso(self):
        """Should format datetime objects as ISO strings"""
        data = {"timestamp": datetime(2025, 1, 25, 14, 30, 0)}
        response = create_json_response(data, "test.json")

        json_content = json.loads(response.get_data(as_text=True))
        assert "2025-01-25T14:30:00" in json_content["timestamp"]

    def test_pretty_prints_json(self):
        """Should format JSON with indentation"""
        data = {"a": 1, "b": 2}
        response = create_json_response(data, "test.json")

        json_str = response.get_data(as_text=True)
        assert "\n" in json_str  # Has newlines (pretty printed)
        assert "  " in json_str  # Has indentation

    def test_ensures_ascii_for_security(self):
        """Should escape non-ASCII characters for XSS protection"""
        data = {"name": "José"}
        response = create_json_response(data, "test.json")

        json_str = response.get_data(as_text=True)
        # ensure_ascii=True should escape non-ASCII
        # José becomes Jos\u00e9
        assert "\\u00e9" in json_str

    def test_sanitizes_filename_header_injection(self):
        """Should sanitize filename to prevent header injection"""
        data = {"name": "John"}
        malicious_filename = 'test"\r\nX-Evil-Header: malicious\r\n.json'
        response = create_json_response(data, malicious_filename)

        disposition = response.headers["Content-Disposition"]
        # Should escape quotes and strip newlines
        assert '\\"' in disposition or '"' not in disposition
        assert "\r" not in disposition
        assert "\n" not in disposition

    def test_includes_nosniff_header(self):
        """Should include X-Content-Type-Options: nosniff"""
        data = {"name": "John"}
        response = create_json_response(data, "test.json")

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_utf8_encoding(self):
        """Should declare UTF-8 encoding"""
        data = {"name": "John"}
        response = create_json_response(data, "test.json")

        assert "charset=utf-8" in response.headers["Content-Type"]

    def test_filename_in_headers(self):
        """Should include filename in Content-Disposition header"""
        data = {"name": "John"}
        response = create_json_response(data, "my_metrics_2025-01-25.json")

        assert "my_metrics_2025-01-25.json" in response.headers["Content-Disposition"]
        assert "attachment" in response.headers["Content-Disposition"]

    def test_handles_complex_nested_data(self):
        """Should handle real-world metrics structure"""
        data = {
            "team": "Native",
            "github": {"prs": 50, "reviews": 75},
            "jira": {"throughput": 30},
            "dora": {"deployment_freq": 2.5, "lead_time": 48},
        }
        response = create_json_response(data, "metrics.json")

        json_content = json.loads(response.get_data(as_text=True))
        assert json_content["team"] == "Native"
        assert json_content["github"]["prs"] == 50
        assert json_content["dora"]["deployment_freq"] == 2.5

    def test_raises_error_for_non_serializable(self):
        """Should raise TypeError for non-serializable objects"""

        class CustomObject:
            pass

        data = {"obj": CustomObject()}

        with pytest.raises(TypeError, match="not JSON serializable"):
            create_json_response(data, "test.json")
