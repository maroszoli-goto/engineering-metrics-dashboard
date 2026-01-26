"""Dashboard blueprint for main views

Handles team, person, and comparison dashboard pages.
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, Union

import pandas as pd
from flask import Blueprint, current_app, render_template, request

from src.dashboard.auth import require_auth
from src.dashboard.utils.validation import validate_identifier
from src.models.metrics import MetricsCalculator
from src.utils.logging import get_logger
from src.utils.performance import timed_route

# Initialize logger
logger = get_logger("team_metrics.dashboard.views")

# Create blueprint
dashboard_bp = Blueprint("dashboard", __name__)


def get_metrics_cache():
    """Get metrics cache from service container"""
    # Try container first (new pattern), fall back to extensions (legacy)
    if hasattr(current_app, "container"):
        return current_app.container.get("metrics_cache")
    return current_app.extensions["metrics_cache"]


def get_cache_service():
    """Get cache service from service container"""
    # Try container first (new pattern), fall back to extensions (legacy)
    if hasattr(current_app, "container"):
        return current_app.container.get("cache_service")
    return current_app.extensions["cache_service"]


def get_config():
    """Get config from service container"""
    # Try container first (new pattern), fall back to extensions (legacy)
    if hasattr(current_app, "container"):
        return current_app.container.get("config")
    return current_app.extensions["app_config"]


def get_display_name(username: str, member_names: Dict[str, str]) -> str:
    """Get display name for a username from member_names mapping"""
    return member_names.get(username, username)


@dashboard_bp.route("/")
@timed_route
@require_auth
def index() -> str:
    """Main dashboard page - shows team overview"""
    config = get_config()
    metrics_cache = get_metrics_cache()
    cache_service = get_cache_service()

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


@dashboard_bp.route("/team/<team_name>")
@timed_route
@require_auth
def team_dashboard(team_name: str) -> Union[str, Tuple[str, int]]:
    """Team-specific dashboard"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError as e:
        logger.warning(f"Invalid team name in URL: {e}")
        return render_template("error.html", error="Invalid team name"), 400

    config = get_config()
    metrics_cache = get_metrics_cache()
    cache_service = get_cache_service()

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


@dashboard_bp.route("/person/<username>")
@timed_route
@require_auth
def person_dashboard(username: str) -> Union[str, Tuple[str, int]]:
    """Person-specific dashboard"""
    # Security: Validate username to prevent XSS
    try:
        username = validate_identifier(username, "username")
    except ValueError as e:
        logger.warning(f"Invalid username in URL: {e}")
        return render_template("error.html", error="Invalid username"), 400

    config = get_config()
    metrics_cache = get_metrics_cache()
    cache_service = get_cache_service()

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


@dashboard_bp.route("/team/<team_name>/compare")
@timed_route
@require_auth
def team_members_comparison(team_name: str) -> Union[str, Tuple[str, int]]:
    """Compare all team members side-by-side"""
    # Security: Validate team_name to prevent XSS
    try:
        team_name = validate_identifier(team_name, "team name")
    except ValueError as e:
        logger.warning(f"Invalid team name in URL: {e}")
        return render_template("error.html", error="Invalid team name"), 400

    config = get_config()
    metrics_cache = get_metrics_cache()
    cache_service = get_cache_service()

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


@dashboard_bp.route("/documentation")
@timed_route
@require_auth
def documentation() -> str:
    """Documentation and FAQ page"""
    return render_template("documentation.html")


@dashboard_bp.route("/comparison")
@timed_route
@require_auth
def team_comparison() -> str:
    """Side-by-side team comparison"""
    config = get_config()
    metrics_cache = get_metrics_cache()
    cache_service = get_cache_service()

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


# Health check endpoint (for testing)
@dashboard_bp.route("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "blueprint": "dashboard"}
