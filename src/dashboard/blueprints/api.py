"""API blueprint for dashboard

Handles API endpoints for metrics, refresh, and cache operations.
"""

from typing import Any, Tuple, Union

from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request

from src.dashboard.auth import require_auth
from src.dashboard.utils.error_handling import handle_api_error
from src.dashboard.utils.performance import timed_route
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("team_metrics.dashboard.api")

# Create blueprint
api_bp = Blueprint("api", __name__)


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


def get_refresh_service():
    """Get refresh service from service container"""
    # Try container first (new pattern), fall back to extensions (legacy)
    if hasattr(current_app, "container"):
        return current_app.container.get("refresh_service")
    return current_app.extensions["refresh_service"]


def get_config():
    """Get config from service container"""
    # Try container first (new pattern), fall back to extensions (legacy)
    if hasattr(current_app, "container"):
        return current_app.container.get("config")
    return current_app.extensions["app_config"]


def refresh_metrics():
    """Refresh metrics using the refresh service"""
    refresh_service = get_refresh_service()
    metrics_cache = get_metrics_cache()

    # Call service to refresh metrics
    cache_data = refresh_service.refresh_metrics()

    if cache_data:
        # Update global cache
        metrics_cache["data"] = cache_data
        metrics_cache["timestamp"] = cache_data["timestamp"]

    return cache_data


@api_bp.route("/metrics")
@timed_route
@require_auth
def api_metrics() -> Union[Response, Tuple[Response, int]]:
    """API endpoint for metrics data

    Returns cached metrics data. If cache is expired, automatically
    refreshes before returning.

    Returns:
        JSON response with metrics data or error message
    """
    config = get_config()
    cache_service = get_cache_service()
    metrics_cache = get_metrics_cache()

    if cache_service.should_refresh(metrics_cache, config.dashboard_config.get("cache_duration_minutes", 60)):
        try:
            refresh_metrics()
        except Exception as e:
            logger.error(f"Metrics refresh failed: {str(e)}")
            return jsonify({"error": "Failed to refresh metrics"}), 500

    return jsonify(metrics_cache["data"])


@api_bp.route("/refresh")
@timed_route
@require_auth
def api_refresh() -> Union[Response, Tuple[Response, int]]:
    """Force refresh metrics

    Triggers immediate metrics collection from GitHub and Jira,
    bypassing cache TTL checks.

    Returns:
        JSON response with status and refreshed metrics data
    """
    try:
        metrics = refresh_metrics()
        return jsonify({"status": "success", "metrics": metrics})
    except Exception as e:
        return handle_api_error(e, "Metrics refresh")


@api_bp.route("/reload-cache", methods=["POST"])
@timed_route
@require_auth
def api_reload_cache() -> Union[Response, Tuple[Response, int]]:
    """Reload metrics cache from disk without restarting server

    Loads cached metrics from pickle file for specified date range
    and environment. Useful for switching between cached datasets.

    Query Parameters:
        range: Date range key (e.g., '90d', '30d'). Default: '90d'
        env: Environment name (e.g., 'prod', 'uat'). Default: 'prod'

    Returns:
        JSON response with status and reload timestamp
    """
    try:
        range_key = request.args.get("range", "90d")
        env = request.args.get("env", "prod")

        cache_service = get_cache_service()
        metrics_cache = get_metrics_cache()

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


@api_bp.route("/collect")
@timed_route
@require_auth
def collect() -> Any:
    """Trigger collection and redirect to dashboard

    Initiates metrics collection from GitHub and Jira, then redirects
    to the main dashboard page. This is the UI-friendly version of
    /api/refresh.

    Returns:
        Redirect to dashboard on success, error page on failure
    """
    try:
        refresh_metrics()
        return redirect("/")
    except Exception as e:
        logger.error(f"Collection failed: {str(e)}")
        return render_template("error.html", error="An error occurred during collection")


# Cache statistics endpoint
@api_bp.route("/cache/stats")
@timed_route
@require_auth
def cache_stats():
    """Get cache statistics

    Returns cache performance metrics including hit rates, memory usage,
    and eviction counts.

    Returns:
        JSON response with cache statistics

    Example response:
        {
            "memory_hits": 150,
            "disk_hits": 25,
            "misses": 5,
            "hit_rate": 0.972,
            "memory_hit_rate": 0.833,
            "evictions": 3,
            "sets": 180,
            "memory_entries": 5,
            "memory_size_mb": 45.2,
            "max_memory_mb": 500.0,
            "memory_utilization": 0.090
        }
    """
    try:
        cache_service = get_cache_service()

        # Check if cache service has get_stats method (enhanced cache)
        if hasattr(cache_service, "get_stats"):
            stats = cache_service.get_stats()
            return jsonify({"status": "ok", "stats": stats})
        else:
            # Legacy cache service - return basic info
            return jsonify(
                {
                    "status": "ok",
                    "stats": {
                        "message": "Cache statistics not available (using legacy cache service)",
                        "upgrade_to_enhanced": True,
                    },
                }
            )

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return handle_api_error(e, "Failed to retrieve cache statistics")


@api_bp.route("/cache/clear", methods=["POST"])
@timed_route
@require_auth
def cache_clear():
    """Clear cache (memory only or all)

    Query Parameters:
        type: 'memory' (clear memory only) or 'all' (clear memory + disk)

    Returns:
        JSON response with success status

    Example:
        POST /api/cache/clear?type=memory
        POST /api/cache/clear?type=all
    """
    try:
        cache_service = get_cache_service()
        clear_type = request.args.get("type", "memory")

        if not hasattr(cache_service, "clear_memory"):
            return jsonify({"status": "error", "message": "Cache clearing not supported (legacy cache service)"})

        if clear_type == "all":
            cache_service.clear_all()
            message = "Cleared all caches (memory + disk)"
        else:
            cache_service.clear_memory()
            message = "Cleared memory cache"

        logger.info(message)
        return jsonify({"status": "ok", "message": message})

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return handle_api_error(e, "Failed to clear cache")


@api_bp.route("/cache/warm", methods=["POST"])
@timed_route
@require_auth
def cache_warm():
    """Warm cache with specified keys

    Request Body:
        {
            "keys": ["90d_prod", "30d_prod", "180d_prod"]
        }

    Returns:
        JSON response with success status
    """
    try:
        cache_service = get_cache_service()

        if not hasattr(cache_service, "warm_cache"):
            return jsonify({"status": "error", "message": "Cache warming not supported (legacy cache service)"})

        # Get keys from request
        data = request.get_json() or {}
        keys = data.get("keys", [])

        if not keys:
            return jsonify({"status": "error", "message": "No keys provided"})

        # Warm cache
        cache_service.warm_cache(keys)

        logger.info(f"Cache warmed with {len(keys)} keys")
        return jsonify({"status": "ok", "message": f"Cache warmed with {len(keys)} keys"})

    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")
        return handle_api_error(e, "Failed to warm cache")


# Health check endpoint (for testing)
@api_bp.route("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "blueprint": "api"}
