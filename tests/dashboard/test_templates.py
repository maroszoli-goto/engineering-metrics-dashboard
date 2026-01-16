"""Tests for template rendering"""

from datetime import datetime

import pytest
from flask import render_template_string

from src.dashboard.app import app


@pytest.fixture
def app_context():
    """Flask application context for template rendering"""
    with app.app_context():
        with app.test_request_context():
            yield app


class TestBaseTemplate:
    """Test base.html master template"""

    def test_base_template_renders(self, app_context):
        """Test base template renders without errors"""
        template = """
        {% extends "base.html" %}
        {% block title %}Test{% endblock %}
        {% block content %}Test Content{% endblock %}
        """
        result = render_template_string(template)
        assert "Test Content" in result

    def test_base_template_has_hamburger_menu(self, app_context):
        """Test base template includes hamburger menu"""
        template = """{% extends "base.html" %}{% block content %}Test{% endblock %}"""
        result = render_template_string(template)
        assert "hamburger" in result.lower()

    def test_base_template_has_date_selector(self, app_context):
        """Test base template includes date range selector"""
        template = """{% extends "base.html" %}{% block content %}Test{% endblock %}"""
        result = render_template_string(template)
        assert "date-range-selector" in result or "range" in result.lower()


class TestAbstractTemplates:
    """Test abstract template inheritance"""

    def test_landing_page_template(self, app_context):
        """Test landing_page.html abstract template"""
        template = """
        {% extends "landing_page.html" %}
        {% block page_title %}Test Page{% endblock %}
        {% block hero_title %}Hero{% endblock %}
        {% block main_content %}Content{% endblock %}
        """
        result = render_template_string(template)
        assert "Hero" in result
        assert "Content" in result

    def test_detail_page_template(self, app_context):
        """Test detail_page.html abstract template"""
        template = """
        {% extends "detail_page.html" %}
        {% block page_title %}Detail{% endblock %}
        {% block header_title %}Header{% endblock %}
        {% block main_content %}Content{% endblock %}
        """
        result = render_template_string(template)
        assert "Header" in result
        assert "Content" in result


class TestTemplateVariables:
    """Test template variable injection"""

    def test_context_processor_variables(self, app_context):
        """Test global template variables from context processor"""
        # Test that context processor injects variables
        template = "{{ current_year }}"
        result = render_template_string(template)
        assert str(datetime.now().year) in result


class TestTemplateFiles:
    """Test that template files exist and are valid"""

    def test_base_template_exists(self):
        """Test base.html template file exists"""
        from pathlib import Path

        base_path = Path(__file__).parent.parent.parent / "src" / "dashboard" / "templates" / "base.html"
        assert base_path.exists()

    def test_teams_overview_template_exists(self):
        """Test teams_overview.html template file exists"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent.parent / "src" / "dashboard" / "templates" / "teams_overview.html"
        assert template_path.exists()

    def test_team_dashboard_template_exists(self):
        """Test team_dashboard.html template file exists"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent.parent / "src" / "dashboard" / "templates" / "team_dashboard.html"
        assert template_path.exists()

    def test_person_dashboard_template_exists(self):
        """Test person_dashboard.html template file exists"""
        from pathlib import Path

        template_path = (
            Path(__file__).parent.parent.parent / "src" / "dashboard" / "templates" / "person_dashboard.html"
        )
        assert template_path.exists()


class TestStaticFiles:
    """Test that static files exist"""

    def test_main_css_exists(self):
        """Test main.css exists"""
        from pathlib import Path

        css_path = Path(__file__).parent.parent.parent / "src" / "dashboard" / "static" / "css" / "main.css"
        assert css_path.exists()

    def test_charts_js_exists(self):
        """Test charts.js exists"""
        from pathlib import Path

        js_path = Path(__file__).parent.parent.parent / "src" / "dashboard" / "static" / "js" / "charts.js"
        assert js_path.exists()

    def test_theme_toggle_js_exists(self):
        """Test theme-toggle.js exists"""
        from pathlib import Path

        js_path = Path(__file__).parent.parent.parent / "src" / "dashboard" / "static" / "js" / "theme-toggle.js"
        assert js_path.exists()
