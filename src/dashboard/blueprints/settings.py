"""Settings blueprint for configuration management

Handles settings page and configuration updates.
"""

from typing import Tuple, Union

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from src.dashboard.auth import require_auth
from src.utils.performance import timed_route

# Create blueprint
settings_bp = Blueprint("settings", __name__)


def get_config():
    """Get config from service container"""
    # Try container first (new pattern), fall back to extensions (legacy)
    if hasattr(current_app, "container"):
        return current_app.container.get("config")
    return current_app.extensions["app_config"]


@settings_bp.route("/")
@timed_route
@require_auth
def settings() -> str:
    """Render performance score settings page"""
    config = get_config()
    current_weights = config.performance_weights

    # Convert to percentages for display
    weights_pct = {k: v * 100 for k, v in current_weights.items()}

    metric_descriptions = {
        "prs": "Pull requests created",
        "reviews": "Code reviews given",
        "commits": "Commits made",
        "cycle_time": "PR cycle time (lower is better)",
        "jira_completed": "Jira issues completed",
        "merge_rate": "PR merge rate",
    }

    metric_labels = {
        "prs": "Pull Requests",
        "reviews": "Code Reviews",
        "commits": "Commits",
        "cycle_time": "Cycle Time",
        "jira_completed": "Jira Completed",
        "merge_rate": "Merge Rate",
    }

    return render_template(
        "settings.html",
        weights=weights_pct,
        metric_descriptions=metric_descriptions,
        metric_labels=metric_labels,
        config=config,
    )


@settings_bp.route("/save", methods=["POST"])
@timed_route
@require_auth
def save_settings() -> Union[Response, Tuple[Response, int]]:
    """Save updated performance weights"""
    try:
        # Parse JSON data
        data = request.get_json()

        # Extract weights (in percentages)
        weights_pct = {
            "prs": float(data.get("prs", 20)),
            "reviews": float(data.get("reviews", 20)),
            "commits": float(data.get("commits", 15)),
            "cycle_time": float(data.get("cycle_time", 15)),
            "jira_completed": float(data.get("jira_completed", 20)),
            "merge_rate": float(data.get("merge_rate", 10)),
            "deployment_frequency": float(data.get("deployment_frequency", 10)),
            "lead_time": float(data.get("lead_time", 10)),
            "change_failure_rate": float(data.get("change_failure_rate", 5)),
            "mttr": float(data.get("mttr", 5)),
        }

        # Validate sum
        total = sum(weights_pct.values())
        if not (99.9 <= total <= 100.1):
            return jsonify({"success": False, "error": f"Weights must sum to 100%, got {total:.1f}%"}), 400

        # Convert to decimals
        weights = {k: v / 100 for k, v in weights_pct.items()}

        # Save to config
        config = get_config()
        config.update_performance_weights(weights)

        return jsonify({"success": True, "message": "Settings saved successfully"})

    except Exception as e:
        current_app.logger.error(f"Settings save failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to save settings"}), 500


@settings_bp.route("/reset", methods=["POST"])
@timed_route
@require_auth
def reset_settings() -> Union[Response, Tuple[Response, int]]:
    """Reset weights to defaults"""
    try:
        default_weights = {
            "prs": 0.15,
            "reviews": 0.15,
            "commits": 0.10,
            "cycle_time": 0.10,
            "jira_completed": 0.15,
            "merge_rate": 0.05,
            "deployment_frequency": 0.10,
            "lead_time": 0.10,
            "change_failure_rate": 0.05,
            "mttr": 0.05,
        }

        config = get_config()
        config.update_performance_weights(default_weights)

        return jsonify({"success": True, "message": "Settings reset to defaults"})

    except Exception as e:
        current_app.logger.error(f"Settings reset failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to reset settings"}), 500


# Health check endpoint (for testing)
@settings_bp.route("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "blueprint": "settings"}
