"""Export blueprint for dashboard

Handles CSV and JSON export endpoints for teams, persons, and comparisons.
"""

from datetime import datetime
from typing import Any

from flask import Blueprint, Response, current_app, make_response

from src.dashboard.auth import require_auth
from src.dashboard.input_validation import (
    validate_route_params,
    validate_team_name,
    validate_username,
)
from src.dashboard.utils.export import create_csv_response, create_json_response
from src.dashboard.utils.performance_decorator import timed_route
from src.dashboard.utils.validation import validate_identifier

# Create blueprint
export_bp = Blueprint("export", __name__)


def get_metrics_cache():
    """Get metrics cache from service container"""
    # Try container first (new pattern), fall back to extensions (legacy)
    if hasattr(current_app, "container"):
        return current_app.container.get("metrics_cache")
    return current_app.extensions["metrics_cache"]


@export_bp.route("/team/<team_name>/csv")
@timed_route
@require_auth
@validate_route_params(team_name=validate_team_name)
def export_team_csv(team_name: str) -> Response:
    """Export team metrics as CSV"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        current_app.logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        teams = data.get("teams", {})
        if team_name not in teams:
            return make_response("Team not found", 404)

        team_data = teams[team_name].copy()

        # Add metadata
        date_range_info = metrics_cache.get("date_range", {})
        team_data["export_timestamp"] = datetime.now()
        team_data["date_range_start"] = date_range_info.get("start_date", "")
        team_data["date_range_end"] = date_range_info.get("end_date", "")
        team_data["date_range_label"] = date_range_info.get("label", "")

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"team_{team_name.replace(' ', '_').lower()}_metrics_{date_suffix}.csv"
        return create_csv_response(team_data, filename)

    except Exception as e:
        current_app.logger.error(f"CSV export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


@export_bp.route("/team/<team_name>/json")
@timed_route
@require_auth
@validate_route_params(team_name=validate_team_name)
def export_team_json(team_name: str) -> Response:
    """Export team metrics as JSON"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        current_app.logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        teams = data.get("teams", {})
        if team_name not in teams:
            return make_response("Team not found", 404)

        team_data = teams[team_name].copy()

        # Add metadata
        date_range_info = metrics_cache.get("date_range", {})
        export_data = {
            "team": team_data,
            "metadata": {"export_timestamp": datetime.now(), "date_range": date_range_info},
        }

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"team_{team_name.replace(' ', '_').lower()}_metrics_{date_suffix}.json"
        return create_json_response(export_data, filename)

    except Exception as e:
        current_app.logger.error(f"JSON export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


@export_bp.route("/person/<username>/csv")
@timed_route
@require_auth
@validate_route_params(username=validate_username)
def export_person_csv(username: str) -> Response:
    """Export person metrics as CSV"""
    # Security: Validate username to prevent XSS
    try:
        username = validate_identifier(username, "username")
    except ValueError:
        current_app.logger.warning(f"Invalid username in export URL")
        return make_response("Invalid username", 400)

    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        persons = data.get("persons", {})
        if username not in persons:
            return make_response("Person not found", 404)

        person_data = persons[username].copy()

        # Add metadata
        date_range_info = metrics_cache.get("date_range", {})
        person_data["export_timestamp"] = datetime.now()
        person_data["date_range_start"] = date_range_info.get("start_date", "")
        person_data["date_range_end"] = date_range_info.get("end_date", "")
        person_data["date_range_label"] = date_range_info.get("label", "")

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"person_{username.replace(' ', '_').lower()}_metrics_{date_suffix}.csv"
        return create_csv_response(person_data, filename)

    except Exception as e:
        current_app.logger.error(f"CSV export failed for person {username}: {str(e)}")
        return make_response("Error exporting data", 500)


@export_bp.route("/person/<username>/json")
@timed_route
@require_auth
@validate_route_params(username=validate_username)
def export_person_json(username: str) -> Response:
    """Export person metrics as JSON"""
    # Security: Validate username to prevent XSS
    try:
        username = validate_identifier(username, "username")
    except ValueError:
        current_app.logger.warning(f"Invalid username in export URL")
        return make_response("Invalid username", 400)

    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        persons = data.get("persons", {})
        if username not in persons:
            return make_response("Person not found", 404)

        person_data = persons[username].copy()

        # Add metadata
        date_range_info = metrics_cache.get("date_range", {})
        export_data = {
            "person": person_data,
            "metadata": {"export_timestamp": datetime.now(), "date_range": date_range_info},
        }

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"person_{username.replace(' ', '_').lower()}_metrics_{date_suffix}.json"
        return create_json_response(export_data, filename)

    except Exception as e:
        current_app.logger.error(f"JSON export failed for person {username}: {str(e)}")
        return make_response("Error exporting data", 500)


@export_bp.route("/comparison/csv")
@timed_route
@require_auth
def export_comparison_csv() -> Response:
    """Export team comparison as CSV"""
    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        comparison = data.get("comparison", {})
        if not comparison:
            return make_response("No comparison data available", 404)

        # Get performance scores and prepare data
        teams_data = []
        for team_name, team_metrics in comparison.items():
            team_row = {"team_name": team_name}
            team_row.update(team_metrics)
            teams_data.append(team_row)

        # Add metadata to first row
        date_range_info = metrics_cache.get("date_range", {})
        if teams_data:
            teams_data[0]["export_timestamp"] = datetime.now()
            teams_data[0]["date_range_start"] = date_range_info.get("start_date", "")
            teams_data[0]["date_range_end"] = date_range_info.get("end_date", "")
            teams_data[0]["date_range_label"] = date_range_info.get("label", "")

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"team_comparison_metrics_{date_suffix}.csv"
        return create_csv_response(teams_data, filename)

    except Exception as e:
        current_app.logger.error(f"CSV comparison export failed: {str(e)}")
        return make_response("Error exporting data", 500)


@export_bp.route("/comparison/json")
@timed_route
@require_auth
def export_comparison_json() -> Response:
    """Export team comparison as JSON"""
    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        comparison = data.get("comparison", {})
        if not comparison:
            return make_response("No comparison data available", 404)

        # Add metadata
        date_range_info = metrics_cache.get("date_range", {})
        export_data = {
            "comparison": comparison,
            "metadata": {"export_timestamp": datetime.now(), "date_range": date_range_info},
        }

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"team_comparison_metrics_{date_suffix}.json"
        return create_json_response(export_data, filename)

    except Exception as e:
        current_app.logger.error(f"JSON comparison export failed: {str(e)}")
        return make_response("Error exporting data", 500)


@export_bp.route("/team-members/<team_name>/csv")
@timed_route
@require_auth
@validate_route_params(team_name=validate_team_name)
def export_team_members_csv(team_name: str) -> Response:
    """Export team member comparison as CSV"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        current_app.logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        teams = data.get("teams", {})
        if team_name not in teams:
            return make_response("Team not found", 404)

        team_data = teams[team_name]
        members_breakdown = team_data.get("members_breakdown", {})

        if not members_breakdown:
            return make_response("No member data available for this team", 404)

        # Prepare member rows
        members_data = []
        for member_name, member_metrics in members_breakdown.items():
            member_row = {"member_name": member_name}
            member_row.update(member_metrics)
            members_data.append(member_row)

        # Add metadata to first row
        date_range_info = metrics_cache.get("date_range", {})
        if members_data:
            members_data[0]["team_name"] = team_name
            members_data[0]["export_timestamp"] = datetime.now()
            members_data[0]["date_range_start"] = date_range_info.get("start_date", "")
            members_data[0]["date_range_end"] = date_range_info.get("end_date", "")
            members_data[0]["date_range_label"] = date_range_info.get("label", "")

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"team_{team_name.replace(' ', '_').lower()}_members_comparison_{date_suffix}.csv"
        return create_csv_response(members_data, filename)

    except Exception as e:
        current_app.logger.error(f"CSV member export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


@export_bp.route("/team-members/<team_name>/json")
@timed_route
@require_auth
@validate_route_params(team_name=validate_team_name)
def export_team_members_json(team_name: str) -> Response:
    """Export team member comparison as JSON"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        current_app.logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
        metrics_cache = get_metrics_cache()
        data = metrics_cache.get("data")
        if not data:
            return make_response("No metrics data available. Please collect data first.", 404)

        teams = data.get("teams", {})
        if team_name not in teams:
            return make_response("Team not found", 404)

        team_data = teams[team_name]
        members_breakdown = team_data.get("members_breakdown", {})

        if not members_breakdown:
            return make_response("No member data available for this team", 404)

        # Add metadata
        date_range_info = metrics_cache.get("date_range", {})
        export_data = {
            "team_name": team_name,
            "members": members_breakdown,
            "metadata": {"export_timestamp": datetime.now(), "date_range": date_range_info},
        }

        date_suffix = datetime.now().strftime("%Y-%m-%d")
        filename = f"team_{team_name.replace(' ', '_').lower()}_members_comparison_{date_suffix}.json"
        return create_json_response(export_data, filename)

    except Exception as e:
        current_app.logger.error(f"JSON member export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


# Health check endpoint (for testing)
@export_bp.route("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "blueprint": "export"}
