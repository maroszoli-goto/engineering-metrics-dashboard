import csv
import io
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from flask import Flask, Response, jsonify, make_response, redirect, render_template, request

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd

from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector
from src.config import Config
from src.dashboard.auth import init_auth, require_auth
from src.dashboard.services.cache_service import CacheService
from src.dashboard.services.metrics_refresh_service import MetricsRefreshService
from src.dashboard.utils.data import flatten_dict
from src.dashboard.utils.data_filtering import filter_github_data_by_date, filter_jira_data_by_date
from src.dashboard.utils.error_handling import handle_api_error, set_logger
from src.dashboard.utils.export import create_csv_response, create_json_response
from src.dashboard.utils.formatting import format_time_ago, format_value_for_csv
from src.dashboard.utils.performance import timed_route
from src.dashboard.utils.validation import validate_identifier
from src.models.metrics import MetricsCalculator
from src.utils.date_ranges import get_cache_filename, get_preset_ranges
from src.utils.logging import get_logger

# Initialize logger
dashboard_logger = get_logger("team_metrics.dashboard")

# Set logger for error handling utility
set_logger(dashboard_logger)

# Initialize cache service
data_dir = Path(__file__).parent.parent.parent / "data"
cache_service = CacheService(data_dir, dashboard_logger)

# Initialize metrics refresh service (will be initialized on first use to avoid loading config at import time)
refresh_service = None

app = Flask(__name__)


# Context processor to inject current year and date range info into all templates
@app.context_processor
def inject_template_globals() -> Dict[str, Any]:
    """Inject global template variables"""
    range_key = request.args.get("range", "90d")
    date_range_info: Dict[str, Any] = metrics_cache.get("date_range", {})

    # Get team list from cache or config
    teams = []
    cache_data = metrics_cache.get("data")
    if cache_data and "teams" in cache_data:
        teams = sorted(cache_data["teams"].keys())
    else:
        # Fallback to config
        config = get_config()
        teams = [team["name"] for team in config.teams]

    # Extract environment metadata from cache
    environment = metrics_cache.get("environment", "prod")
    time_offset_days = metrics_cache.get("time_offset_days", 0)
    jira_server = metrics_cache.get("jira_server", "")

    return {
        "current_year": datetime.now().year,
        "current_range": range_key,
        "available_ranges": cache_service.get_available_ranges(),
        "date_range_info": date_range_info,
        "team_list": teams,
        # NEW: Environment context
        "environment": environment,
        "time_offset_days": time_offset_days,
        "jira_server": jira_server,
    }


# Register format_time_ago as Jinja filter (imported from utils.formatting)
app.jinja_env.filters["time_ago"] = format_time_ago

# Global cache
metrics_cache: Dict[str, Any] = {"data": None, "timestamp": None}

# load_cache_from_file, get_available_ranges, should_refresh_cache
# moved to CacheService

# Try to load default cache on startup (90d, prod environment)
loaded_cache = cache_service.load_cache("90d", "prod")
if loaded_cache:
    metrics_cache.update(loaded_cache)


def get_config() -> Config:
    """Load configuration"""
    return Config()


def get_display_name(username: str, member_names: Optional[Dict[str, str]] = None) -> str:
    """Get display name for a GitHub username, fallback to username."""
    if member_names and username in member_names:
        return member_names[username]
    return username


# validate_identifier, handle_api_error, filter_github_data_by_date, filter_jira_data_by_date
# moved to src.dashboard.utils modules


# should_refresh_cache moved to CacheService.should_refresh()
# refresh_metrics moved to MetricsRefreshService


def refresh_metrics() -> Optional[Dict]:
    """Collect and calculate metrics using GraphQL API (wrapper for service)"""
    global refresh_service

    # Initialize refresh service on first use
    if refresh_service is None:
        config = get_config()
        refresh_service = MetricsRefreshService(config, dashboard_logger)

    # Call service to refresh metrics
    cache_data = refresh_service.refresh_metrics()

    if cache_data:
        # Update global cache
        metrics_cache["data"] = cache_data
        metrics_cache["timestamp"] = cache_data["timestamp"]

    return cache_data


@app.route("/")
@timed_route
@require_auth
def index() -> str:
    """Main dashboard page - shows team overview"""
    config = get_config()

    # Get requested date range and environment from query parameters
    range_key = request.args.get("range", "90d")
    env = request.args.get("env", "prod")

    # Load cache for requested range and environment (if not already loaded)
    cache_id = f"{range_key}_{env}"
    current_cache_id = f"{metrics_cache.get('range_key')}_{metrics_cache.get('environment', 'prod')}"
    if current_cache_id != cache_id:
        loaded_cache = cache_service.load_cache(range_key, env)
        if loaded_cache:
            metrics_cache.update(loaded_cache)

    # If no cache exists, show loading page
    if metrics_cache["data"] is None:
        available_ranges = cache_service.get_available_ranges()
        return render_template("loading.html", available_ranges=available_ranges, selected_range=range_key)

    cache = metrics_cache["data"]

    # Get available ranges for selector
    available_ranges = cache_service.get_available_ranges()
    date_range_info = metrics_cache.get("date_range", {})

    # Check if we have the new team-based structure
    if "teams" in cache:
        # New structure - show team overview
        teams = config.teams
        team_list = []

        for team in teams:
            team_name = team.get("name")
            team_data = cache["teams"].get(team_name, {})
            github_metrics = team_data.get("github", {})
            jira_metrics = team_data.get("jira", {})

            dora_metrics = team_data.get("dora", {})

            team_list.append(
                {
                    "name": team_name,
                    "display_name": team.get("display_name", team_name),
                    "pr_count": github_metrics.get("pr_count", 0),
                    "review_count": github_metrics.get("review_count", 0),
                    "commit_count": github_metrics.get("commit_count", 0),
                    "avg_cycle_time": github_metrics.get("avg_cycle_time", 0),
                    "throughput": (
                        jira_metrics.get("throughput", {}).get("weekly_avg", 0) if jira_metrics.get("throughput") else 0
                    ),
                    "wip_count": jira_metrics.get("wip", {}).get("count", 0) if jira_metrics.get("wip") else 0,
                    "dora": dora_metrics,
                }
            )

        return render_template(
            "teams_overview.html",
            teams=team_list,
            cache=cache,
            config=config,
            updated_at=metrics_cache["timestamp"],
            available_ranges=available_ranges,
            selected_range=range_key,
            date_range_info=date_range_info,
        )
    else:
        # Legacy structure - use old dashboard
        return render_template(
            "dashboard.html",
            metrics=cache,
            updated_at=metrics_cache["timestamp"],
            available_ranges=available_ranges,
            selected_range=range_key,
            date_range_info=date_range_info,
        )


@app.route("/api/metrics")
@timed_route
@require_auth
def api_metrics() -> Union[Response, Tuple[Response, int]]:
    """API endpoint for metrics data"""
    config = get_config()

    if cache_service.should_refresh(metrics_cache, config.dashboard_config.get("cache_duration_minutes", 60)):
        try:
            refresh_metrics()
        except Exception as e:
            dashboard_logger.error(f"Metrics refresh failed: {str(e)}")
            return jsonify({"error": "Failed to refresh metrics"}), 500

    return jsonify(metrics_cache["data"])


@app.route("/api/refresh")
@timed_route
@require_auth
def api_refresh() -> Union[Response, Tuple[Response, int]]:
    """Force refresh metrics"""
    try:
        metrics = refresh_metrics()
        return jsonify({"status": "success", "metrics": metrics})
    except Exception as e:
        return handle_api_error(e, "Metrics refresh")


@app.route("/api/reload-cache", methods=["POST"])
@timed_route
@require_auth
def api_reload_cache() -> Union[Response, Tuple[Response, int]]:
    """Reload metrics cache from disk without restarting server"""
    try:
        range_key = request.args.get("range", "90d")
        env = request.args.get("env", "prod")
        loaded_cache = cache_service.load_cache(range_key, env)
        if loaded_cache:
            metrics_cache.update(loaded_cache)
            return jsonify(
                {
                    "status": "success",
                    "message": "Cache reloaded successfully",
                    "timestamp": str(metrics_cache["timestamp"]),
                }
            )
        else:
            return (
                jsonify({"status": "error", "message": "Failed to reload cache - file may not exist or be corrupted"}),
                500,
            )
    except Exception as e:
        return handle_api_error(e, "Cache reload")


@app.route("/collect")
@timed_route
@require_auth
def collect() -> Any:
    """Trigger collection and redirect to dashboard"""
    try:
        refresh_metrics()
        return redirect("/")
    except Exception as e:
        dashboard_logger.error(f"Collection failed: {str(e)}")
        return render_template("error.html", error="An error occurred during collection")


@app.route("/team/<team_name>")
@timed_route
@require_auth
def team_dashboard(team_name: str) -> Union[str, Tuple[str, int]]:
    """Team-specific dashboard"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError as e:
        dashboard_logger.warning(f"Invalid team name in URL: {e}")
        return render_template("error.html", error="Invalid team name"), 400

    config = get_config()

    # Get requested date range from query parameter (default: 90d)
    range_key = request.args.get("range", "90d")
    env = request.args.get("env", "prod")

    # Load cache for requested range (if not already loaded)
    cache_id = f"{range_key}_{env}"
    current_cache_id = f"{metrics_cache.get('range_key')}_{metrics_cache.get('environment', 'prod')}"
    if current_cache_id != cache_id:
        loaded_cache = cache_service.load_cache(range_key, env)
        if loaded_cache:
            metrics_cache.update(loaded_cache)

    if metrics_cache["data"] is None:
        return render_template("loading.html")

    # Check if this is new team-based cache structure
    cache = metrics_cache["data"]

    if "teams" in cache:
        # New structure
        team_data = cache["teams"].get(team_name)

        if not team_data:
            return render_template("error.html", error=f"Team '{team_name}' not found")

        team_config = config.get_team_by_name(team_name)

        # Calculate date range for GitHub search links
        start_date = (datetime.now() - timedelta(days=config.days_back)).strftime("%Y-%m-%d")

        # Get member names mapping
        member_names = cache.get("member_names", {})

        # Add Jira data and update GitHub metrics from persons cache
        # (person data is more accurate as it includes cross-team contributions)
        if "persons" in cache and "github" in team_data and "member_trends" in team_data["github"]:
            member_trends = team_data["github"]["member_trends"]
            for member in member_trends:
                if member in cache["persons"]:
                    person_data = cache["persons"][member]

                    # Update GitHub metrics with person-level data (more comprehensive)
                    if "github" in person_data:
                        github_data = person_data["github"]
                        member_trends[member]["prs"] = github_data.get("prs_created", member_trends[member]["prs"])
                        member_trends[member]["reviews"] = github_data.get(
                            "reviews_given", member_trends[member]["reviews"]
                        )
                        member_trends[member]["commits"] = github_data.get("commits", member_trends[member]["commits"])
                        member_trends[member]["lines_added"] = github_data.get(
                            "lines_added", member_trends[member]["lines_added"]
                        )
                        member_trends[member]["lines_deleted"] = github_data.get(
                            "lines_deleted", member_trends[member]["lines_deleted"]
                        )

                    # Add Jira metrics
                    if "jira" in person_data:
                        member_trends[member]["jira"] = {
                            "completed": person_data["jira"].get("completed", 0),
                            "in_progress": person_data["jira"].get("in_progress", 0),
                            "avg_cycle_time": person_data["jira"].get("avg_cycle_time", 0),
                        }

        return render_template(
            "team_dashboard.html",
            team_name=team_name,
            team_display_name=team_config.get("display_name", team_name) if team_config else team_name,
            team_data=team_data,
            team_config=team_config,
            member_names=member_names,
            config=config,
            days_back=config.days_back,
            start_date=start_date,
            jira_server=config.jira_config.get("server", "https://jira.ops.expertcity.com"),
            github_org=config.github_organization,
            github_base_url=config.github_base_url,
            updated_at=metrics_cache["timestamp"],
        )
    else:
        # Legacy structure - show error
        return render_template(
            "error.html",
            error="Team dashboards require team configuration. Please update config.yaml and re-run data collection.",
        )


@app.route("/person/<username>")
@timed_route
@require_auth
def person_dashboard(username: str) -> Union[str, Tuple[str, int]]:
    """Person-specific dashboard"""
    # Security: Validate username to prevent XSS
    try:
        username = validate_identifier(username, "username")
    except ValueError as e:
        dashboard_logger.warning(f"Invalid username in URL: {e}")
        return render_template("error.html", error="Invalid username"), 400

    config = get_config()

    # Get requested date range from query parameter (default: 90d)
    range_key = request.args.get("range", "90d")
    env = request.args.get("env", "prod")

    # Load cache for requested range (if not already loaded)
    cache_id = f"{range_key}_{env}"
    current_cache_id = f"{metrics_cache.get('range_key')}_{metrics_cache.get('environment', 'prod')}"
    if current_cache_id != cache_id:
        loaded_cache = cache_service.load_cache(range_key, env)
        if loaded_cache:
            metrics_cache.update(loaded_cache)

    if metrics_cache["data"] is None:
        return render_template("loading.html")

    cache = metrics_cache["data"]

    if "persons" not in cache:
        return render_template(
            "error.html",
            error="Person dashboards require team configuration. Please update config.yaml and re-run data collection.",
        )

    # Get cached person data (already contains 90-day metrics)
    person_data = cache["persons"].get(username)
    if not person_data:
        return render_template("error.html", error=f"No metrics found for user '{username}'")

    # Calculate trends from raw data if available
    if "raw_github_data" in person_data and person_data.get("raw_github_data"):
        person_dfs = {
            "pull_requests": pd.DataFrame(person_data["raw_github_data"].get("pull_requests", [])),
            "reviews": pd.DataFrame(person_data["raw_github_data"].get("reviews", [])),
            "commits": pd.DataFrame(person_data["raw_github_data"].get("commits", [])),
        }

        calculator = MetricsCalculator(person_dfs)
        person_data["trends"] = calculator.calculate_person_trends(person_data["raw_github_data"], period="weekly")
    else:
        # No raw data available, set empty trends
        person_data["trends"] = {"pr_trend": [], "review_trend": [], "commit_trend": [], "lines_changed_trend": []}

    # Get display name from cache
    member_names = cache.get("member_names", {})
    display_name = get_display_name(username, member_names)

    # Find which team this person belongs to
    team_name = None
    for team in config.teams:
        # Check new format: members list with github/jira keys
        if "members" in team:
            for member in team.get("members", []):
                if isinstance(member, dict) and member.get("github") == username:
                    team_name = team.get("name")
                    break
        # Check old format: github.members
        elif username in team.get("github", {}).get("members", []):
            team_name = team.get("name")
            break
        if team_name:
            break

    return render_template(
        "person_dashboard.html",
        username=username,
        display_name=display_name,
        person_data=person_data,
        team_name=team_name,
        github_org=config.github_organization,
        github_base_url=config.github_base_url,
        updated_at=metrics_cache["timestamp"],
    )


@app.route("/team/<team_name>/compare")
@timed_route
@require_auth
def team_members_comparison(team_name: str) -> Union[str, Tuple[str, int]]:
    """Compare all team members side-by-side"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError as e:
        dashboard_logger.warning(f"Invalid team name in URL: {e}")
        return render_template("error.html", error="Invalid team name"), 400

    config = get_config()

    # Get requested date range from query parameter (default: 90d)
    range_key = request.args.get("range", "90d")
    env = request.args.get("env", "prod")

    # Load cache for requested range (if not already loaded)
    cache_id = f"{range_key}_{env}"
    current_cache_id = f"{metrics_cache.get('range_key')}_{metrics_cache.get('environment', 'prod')}"
    if current_cache_id != cache_id:
        loaded_cache = cache_service.load_cache(range_key, env)
        if loaded_cache:
            metrics_cache.update(loaded_cache)

    if metrics_cache["data"] is None:
        return render_template("loading.html")

    cache = metrics_cache["data"]
    team_data = cache.get("teams", {}).get(team_name)
    team_config = config.get_team_by_name(team_name)

    if not team_data:
        return render_template("error.html", error=f"Team '{team_name}' not found")

    if not team_config:
        return render_template("error.html", error=f"Team configuration for '{team_name}' not found")

    # Get all members from team config - support both formats
    members = []
    if "members" in team_config and isinstance(team_config.get("members"), list):
        # New format: unified members list
        members = [m.get("github") for m in team_config["members"] if isinstance(m, dict) and m.get("github")]
    else:
        # Old format: github.members
        members = team_config.get("github", {}).get("members", [])

    # Get member names mapping
    member_names = cache.get("member_names", {})

    # Build comparison data
    comparison_data = []
    for username in members:
        person_data = cache.get("persons", {}).get(username, {})
        github_data = person_data.get("github", {})
        jira_data = person_data.get("jira", {})

        comparison_data.append(
            {
                "username": username,
                "display_name": get_display_name(str(username), member_names),
                "prs": github_data.get("prs_created", 0),
                "prs_merged": github_data.get("prs_merged", 0),
                "merge_rate": github_data.get("merge_rate", 0) * 100,
                "reviews": github_data.get("reviews_given", 0),
                "commits": github_data.get("commits", 0),
                "lines_added": github_data.get("lines_added", 0),
                "lines_deleted": github_data.get("lines_deleted", 0),
                "cycle_time": github_data.get("avg_pr_cycle_time", 0),
                # Jira metrics
                "jira_completed": jira_data.get("completed", 0),
                "jira_wip": jira_data.get("in_progress", 0),
                "jira_cycle_time": jira_data.get("avg_cycle_time", 0),
            }
        )

    # Calculate performance scores for each member
    for member in comparison_data:
        member["score"] = MetricsCalculator.calculate_performance_score(member, comparison_data)

    # Sort by score descending
    comparison_data.sort(key=lambda x: x["score"], reverse=True)

    # Add rank and badges
    for i, member in enumerate(comparison_data, 1):
        member["rank"] = i
        if i == 1:
            member["badge"] = "🥇"
        elif i == 2:
            member["badge"] = "🥈"
        elif i == 3:
            member["badge"] = "🥉"
        else:
            member["badge"] = ""

    # Get date range info for display
    date_range_info = metrics_cache.get("date_range", {})

    return render_template(
        "team_members_comparison.html",
        team_name=team_name,
        team_display_name=team_config.get("display_name", team_name),
        comparison_data=comparison_data,
        config=config,
        github_org=config.github_organization,
        updated_at=metrics_cache["timestamp"],
        date_range_info=date_range_info,
    )


@app.route("/documentation")
@timed_route
@require_auth
def documentation() -> str:
    """Documentation and FAQ page"""
    return render_template("documentation.html")


@app.route("/comparison")
@timed_route
@require_auth
def team_comparison() -> str:
    """Side-by-side team comparison"""
    config = get_config()

    # Get requested date range from query parameter (default: 90d)
    range_key = request.args.get("range", "90d")
    env = request.args.get("env", "prod")

    # Load cache for requested range (if not already loaded)
    cache_id = f"{range_key}_{env}"
    current_cache_id = f"{metrics_cache.get('range_key')}_{metrics_cache.get('environment', 'prod')}"
    if current_cache_id != cache_id:
        loaded_cache = cache_service.load_cache(range_key, env)
        if loaded_cache:
            metrics_cache.update(loaded_cache)

    if metrics_cache["data"] is None:
        return render_template("loading.html")

    cache = metrics_cache["data"]

    if "comparison" not in cache:
        return render_template("error.html", error="Team comparison requires team configuration.")

    # Build team_configs dict for easy lookup in template
    team_configs = {team["name"]: team for team in config.teams}

    # Calculate date range for GitHub search links
    start_date = (datetime.now() - timedelta(days=config.days_back)).strftime("%Y-%m-%d")

    # Calculate performance scores for teams
    comparison_data = cache["comparison"]
    team_metrics_list = list(comparison_data.values())

    # Add team sizes and calculate scores with normalization
    for team_name, metrics in comparison_data.items():
        team_config = team_configs[team_name]
        # Get team size - support both formats
        if "members" in team_config and isinstance(team_config.get("members"), list):
            # New format: count members with github field
            team_size = len([m for m in team_config["members"] if isinstance(m, dict) and m.get("github")])
        else:
            # Old format: github.members
            team_size = len(team_config.get("github", {}).get("members", []))
        metrics["team_size"] = team_size

        # Prepare metrics for performance score - map DORA keys
        score_metrics = {
            "prs": metrics.get("prs", 0),
            "reviews": metrics.get("reviews", 0),
            "commits": metrics.get("commits", 0),
            "cycle_time": metrics.get("avg_cycle_time", 0),
            "jira_completed": metrics.get("jira_throughput", 0),
            "merge_rate": metrics.get("merge_rate", 0),
            "team_size": team_size,
            # Map DORA metrics from cache keys to performance score keys
            "deployment_frequency": metrics.get("dora_deployment_freq"),
            "lead_time": metrics.get("dora_lead_time"),
            "change_failure_rate": metrics.get("dora_cfr"),
            "mttr": metrics.get("dora_mttr"),
        }

        # Prepare all metrics list with same mapping
        all_metrics_mapped = []
        for tm in team_metrics_list:
            all_metrics_mapped.append(
                {
                    "prs": tm.get("prs", 0),
                    "reviews": tm.get("reviews", 0),
                    "commits": tm.get("commits", 0),
                    "cycle_time": tm.get("avg_cycle_time", 0),
                    "jira_completed": tm.get("jira_throughput", 0),
                    "merge_rate": tm.get("merge_rate", 0),
                    "team_size": tm.get("team_size", 1),
                    "deployment_frequency": tm.get("dora_deployment_freq"),
                    "lead_time": tm.get("dora_lead_time"),
                    "change_failure_rate": tm.get("dora_cfr"),
                    "mttr": tm.get("dora_mttr"),
                }
            )

        metrics["score"] = MetricsCalculator.calculate_performance_score(
            score_metrics, all_metrics_mapped, team_size=team_size  # Normalize by team size
        )

    # Count wins for each team (who has the highest value in each metric)
    team_wins: Dict[str, int] = {}
    # Higher is better metrics
    metrics_to_compare = ["prs", "reviews", "commits", "jira_throughput", "dora_deployment_freq"]

    for metric in metrics_to_compare:
        max_value = max([m.get(metric, 0) for m in comparison_data.values() if m.get(metric) is not None])
        if max_value > 0:
            for team_name, metrics in comparison_data.items():
                if metrics.get(metric, 0) == max_value:
                    team_wins[team_name] = team_wins.get(team_name, 0) + 1

    # Lower is better metrics: cycle time, lead time, CFR, MTTR
    lower_is_better = {
        "avg_cycle_time": "avg_cycle_time",
        "dora_lead_time": "dora_lead_time",
        "dora_cfr": "dora_cfr",
        "dora_mttr": "dora_mttr",
    }

    for metric_key in lower_is_better.keys():
        metric_values = {
            team: m.get(metric_key, 0)
            for team, m in comparison_data.items()
            if m.get(metric_key) is not None and m.get(metric_key) > 0
        }
        if metric_values:
            min_value = min(metric_values.values())
            for team_name, value in metric_values.items():
                if value == min_value:
                    team_wins[team_name] = team_wins.get(team_name, 0) + 1

    # Get date range info for display
    date_range_info = metrics_cache.get("date_range", {})

    return render_template(
        "comparison.html",
        comparison=comparison_data,
        teams=cache.get("teams", {}),
        team_configs=team_configs,
        team_wins=team_wins,
        config=config,
        github_org=config.github_organization,
        jira_server=config.jira_config.get("server"),
        start_date=start_date,
        days_back=config.days_back,
        updated_at=metrics_cache["timestamp"],
        date_range_info=date_range_info,
    )


@app.route("/settings")
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


@app.route("/settings/save", methods=["POST"])
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
        dashboard_logger.error(f"Settings save failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to save settings"}), 500


@app.route("/settings/reset", methods=["POST"])
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
        dashboard_logger.error(f"Settings reset failed: {str(e)}")
        return jsonify({"success": False, "error": "Failed to reset settings"}), 500


# ============================================================================
# Export Helper Functions
# ============================================================================


# flatten_dict, format_value_for_csv, create_csv_response, create_json_response
# moved to src.dashboard.utils modules


# ============================================================================
# Export Routes
# ============================================================================


@app.route("/api/export/team/<team_name>/csv")
@timed_route
@require_auth
def export_team_csv(team_name: str) -> Response:
    """Export team metrics as CSV"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        dashboard_logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
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
        dashboard_logger.error(f"CSV export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


@app.route("/api/export/team/<team_name>/json")
@timed_route
@require_auth
def export_team_json(team_name: str) -> Response:
    """Export team metrics as JSON"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        dashboard_logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
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
        dashboard_logger.error(f"JSON export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


@app.route("/api/export/person/<username>/csv")
@timed_route
@require_auth
def export_person_csv(username: str) -> Response:
    """Export person metrics as CSV"""
    # Security: Validate username to prevent XSS
    try:
        username = validate_identifier(username, "username")
    except ValueError:
        dashboard_logger.warning(f"Invalid username in export URL")
        return make_response("Invalid username", 400)

    try:
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
        dashboard_logger.error(f"CSV export failed for person {username}: {str(e)}")
        return make_response("Error exporting data", 500)


@app.route("/api/export/person/<username>/json")
@timed_route
@require_auth
def export_person_json(username: str) -> Response:
    """Export person metrics as JSON"""
    # Security: Validate username to prevent XSS
    try:
        username = validate_identifier(username, "username")
    except ValueError:
        dashboard_logger.warning(f"Invalid username in export URL")
        return make_response("Invalid username", 400)

    try:
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
        dashboard_logger.error(f"JSON export failed for person {username}: {str(e)}")
        return make_response("Error exporting data", 500)


@app.route("/api/export/comparison/csv")
@timed_route
@require_auth
def export_comparison_csv() -> Response:
    """Export team comparison as CSV"""
    try:
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
        dashboard_logger.error(f"CSV comparison export failed: {str(e)}")
        return make_response("Error exporting data", 500)


@app.route("/api/export/comparison/json")
@timed_route
@require_auth
def export_comparison_json() -> Response:
    """Export team comparison as JSON"""
    try:
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
        dashboard_logger.error(f"JSON comparison export failed: {str(e)}")
        return make_response("Error exporting data", 500)


@app.route("/api/export/team-members/<team_name>/csv")
@timed_route
@require_auth
def export_team_members_csv(team_name: str) -> Response:
    """Export team member comparison as CSV"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        dashboard_logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
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
        dashboard_logger.error(f"CSV member export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


@app.route("/api/export/team-members/<team_name>/json")
@timed_route
@require_auth
def export_team_members_json(team_name: str) -> Response:
    """Export team member comparison as JSON"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError:
        dashboard_logger.warning(f"Invalid team name in export URL")
        return make_response("Invalid team name", 400)

    try:
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
        dashboard_logger.error(f"JSON member export failed for team {team_name}: {str(e)}")
        return make_response("Error exporting data", 500)


def main() -> None:
    config = get_config()
    dashboard_config = config.dashboard_config

    # Initialize authentication
    init_auth(app, config)

    app.run(debug=dashboard_config.get("debug", True), port=dashboard_config.get("port", 5001), host="0.0.0.0")


if __name__ == "__main__":
    main()
