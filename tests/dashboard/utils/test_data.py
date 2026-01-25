"""Tests for data transformation utilities"""

import pytest

from src.dashboard.utils.data import flatten_dict


class TestFlattenDict:
    """Test flatten_dict function"""

    def test_flat_dict_unchanged(self):
        """Should return flat dictionary unchanged"""
        d = {"a": 1, "b": 2, "c": 3}
        assert flatten_dict(d) == d

    def test_nested_dict_flattened(self):
        """Should flatten nested dictionary with dot notation"""
        d = {"a": 1, "b": {"c": 2, "d": 3}}
        expected = {"a": 1, "b.c": 2, "b.d": 3}
        assert flatten_dict(d) == expected

    def test_deeply_nested_dict(self):
        """Should flatten deeply nested dictionaries"""
        d = {"a": {"b": {"c": {"d": 1}}}}
        expected = {"a.b.c.d": 1}
        assert flatten_dict(d) == expected

    def test_mixed_nested_and_flat(self):
        """Should handle mix of nested and flat keys"""
        d = {
            "flat1": 1,
            "nested": {"inner1": 2, "inner2": {"deep": 3}},
            "flat2": 4,
        }
        expected = {
            "flat1": 1,
            "nested.inner1": 2,
            "nested.inner2.deep": 3,
            "flat2": 4,
        }
        assert flatten_dict(d) == expected

    def test_list_to_comma_separated_string(self):
        """Should convert lists to comma-separated strings"""
        d = {"numbers": [1, 2, 3], "strings": ["a", "b", "c"]}
        expected = {"numbers": "1, 2, 3", "strings": "a, b, c"}
        assert flatten_dict(d) == expected

    def test_nested_with_lists(self):
        """Should handle nested dicts containing lists"""
        d = {"outer": {"inner": [1, 2, 3]}}
        expected = {"outer.inner": "1, 2, 3"}
        assert flatten_dict(d) == expected

    def test_empty_dict(self):
        """Should return empty dict for empty input"""
        assert flatten_dict({}) == {}

    def test_empty_list(self):
        """Should convert empty list to empty string"""
        d = {"empty": []}
        expected = {"empty": ""}
        assert flatten_dict(d) == expected

    def test_custom_separator(self):
        """Should support custom separator"""
        d = {"a": {"b": 1}}
        expected = {"a_b": 1}
        assert flatten_dict(d, sep="_") == expected

    def test_parent_key_parameter(self):
        """Should support parent_key parameter for prefixing"""
        d = {"a": 1, "b": 2}
        expected = {"prefix.a": 1, "prefix.b": 2}
        assert flatten_dict(d, parent_key="prefix") == expected

    def test_none_values(self):
        """Should preserve None values"""
        d = {"a": None, "b": {"c": None}}
        expected = {"a": None, "b.c": None}
        assert flatten_dict(d) == expected

    def test_numeric_values(self):
        """Should preserve numeric types"""
        d = {"int": 42, "float": 3.14, "nested": {"num": 100}}
        expected = {"int": 42, "float": 3.14, "nested.num": 100}
        assert flatten_dict(d) == expected

    def test_string_values(self):
        """Should preserve string values"""
        d = {"str": "text", "nested": {"inner": "value"}}
        expected = {"str": "text", "nested.inner": "value"}
        assert flatten_dict(d) == expected

    def test_boolean_values(self):
        """Should preserve boolean values"""
        d = {"flag": True, "nested": {"active": False}}
        expected = {"flag": True, "nested.active": False}
        assert flatten_dict(d) == expected

    def test_real_metrics_structure(self):
        """Should handle real metrics data structure"""
        d = {
            "github": {"prs": 10, "reviews": 15},
            "jira": {"completed": 5, "wip": 3},
            "dora": {"deployment_freq": 2.5},
        }
        expected = {
            "github.prs": 10,
            "github.reviews": 15,
            "jira.completed": 5,
            "jira.wip": 3,
            "dora.deployment_freq": 2.5,
        }
        assert flatten_dict(d) == expected
