"""Performance metrics blueprint for dashboard monitoring.

Provides routes for:
- /metrics/performance - Performance dashboard
- /api/metrics/overview - Performance overview API
- /api/metrics/slow-routes - Slowest routes API
"""

from flask import Blueprint, current_app, jsonify, render_template, request

from src.dashboard.auth import require_auth
from src.dashboard.services.performance_metrics_service import PerformanceMetricsService

# Create blueprint
metrics_bp = Blueprint("metrics", __name__, url_prefix="/metrics")


def get_service() -> PerformanceMetricsService:
    """Get PerformanceMetricsService instance.

    Returns:
        PerformanceMetricsService instance
    """
    # Use shared tracker from app if available
    # The tracker is managed at the application layer, not imported here
    if hasattr(current_app, "performance_tracker"):
        tracker = current_app.performance_tracker
        return PerformanceMetricsService(tracker)
    else:
        # Service will create its own tracker
        return PerformanceMetricsService()


@metrics_bp.route("/performance")
@require_auth
def performance_dashboard():
    """Performance monitoring dashboard.

    Query params:
        days: Number of days to analyze (default: 7)

    Returns:
        Rendered performance dashboard template
    """
    days_back = int(request.args.get("days", 7))

    service = get_service()

    # Get data for dashboard
    overview = service.get_performance_overview(days_back)
    slow_routes = service.get_slow_routes(limit=10, days_back=days_back)
    cache_effectiveness = service.get_cache_effectiveness(days_back)
    health_score = service.get_performance_health_score(days_back)
    storage_info = service.get_storage_info()

    # Get trend data for chart
    trend_data = service.get_route_performance_trend(route=None, days_back=days_back)

    return render_template(
        "metrics/performance.html",
        overview=overview,
        slow_routes=slow_routes,
        cache_effectiveness=cache_effectiveness,
        health_score=health_score,
        storage_info=storage_info,
        trend_data=trend_data,
        days_back=days_back,
    )


@metrics_bp.route("/api/overview")
@require_auth
def api_overview():
    """API endpoint for performance overview.

    Query params:
        days: Number of days to analyze (default: 7)

    Returns:
        JSON with overview statistics
    """
    days_back = int(request.args.get("days", 7))

    service = get_service()
    overview = service.get_performance_overview(days_back)

    return jsonify(overview)


@metrics_bp.route("/api/slow-routes")
@require_auth
def api_slow_routes():
    """API endpoint for slowest routes.

    Query params:
        days: Number of days to analyze (default: 7)
        limit: Number of routes to return (default: 10)

    Returns:
        JSON with slowest routes
    """
    days_back = int(request.args.get("days", 7))
    limit = int(request.args.get("limit", 10))

    service = get_service()
    slow_routes = service.get_slow_routes(limit=limit, days_back=days_back)

    return jsonify(slow_routes)


@metrics_bp.route("/api/route-trend")
@require_auth
def api_route_trend():
    """API endpoint for route performance trend.

    Query params:
        route: Route path (optional, None = all routes)
        days: Number of days to analyze (default: 7)

    Returns:
        JSON with hourly trend data
    """
    route = request.args.get("route", None)
    days_back = int(request.args.get("days", 7))

    service = get_service()
    trend_data = service.get_route_performance_trend(route, days_back)

    return jsonify(trend_data)


@metrics_bp.route("/api/cache-effectiveness")
@require_auth
def api_cache_effectiveness():
    """API endpoint for cache effectiveness analysis.

    Query params:
        days: Number of days to analyze (default: 7)

    Returns:
        JSON with cache statistics
    """
    days_back = int(request.args.get("days", 7))

    service = get_service()
    cache_data = service.get_cache_effectiveness(days_back)

    return jsonify(cache_data)


@metrics_bp.route("/api/health-score")
@require_auth
def api_health_score():
    """API endpoint for performance health score.

    Query params:
        days: Number of days to analyze (default: 7)

    Returns:
        JSON with health score and breakdown
    """
    days_back = int(request.args.get("days", 7))

    service = get_service()
    health_score = service.get_performance_health_score(days_back)

    return jsonify(health_score)


@metrics_bp.route("/api/rotate")
@require_auth
def api_rotate_data():
    """API endpoint to rotate old performance data.

    Query params:
        days: Number of days to keep (default: 90)

    Returns:
        JSON with number of records deleted
    """
    days_to_keep = int(request.args.get("days", 90))

    service = get_service()
    deleted = service.rotate_old_data(days_to_keep)

    return jsonify({"deleted": deleted, "days_kept": days_to_keep})
