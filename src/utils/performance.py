"""Performance monitoring utilities for dashboard routes and API calls.

This module provides decorators and utilities for tracking execution time
of dashboard routes and collector API calls. Timing data is logged in
structured JSON format for analysis.

Usage:
    from src.dashboard.utils.performance import timed_route, timed_operation

    @app.route('/my-route')
    @timed_route
    def my_route():
        with timed_operation('database_query'):
            # ... perform query
            pass
        return response
"""

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def timed_route(func: Callable) -> Callable:
    """Decorator to time Flask route execution.

    Logs route name, duration, status code, and cache hit/miss status.
    Uses time.perf_counter() for high-precision timing.

    Args:
        func: Flask route function to time

    Returns:
        Wrapped function that logs timing information

    Example:
        @app.route('/team/<team_name>')
        @timed_route
        def team_dashboard(team_name):
            return render_template('team.html')
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        route_name = func.__name__

        try:
            # Execute the route
            response = func(*args, **kwargs)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Determine status code
            if hasattr(response, "status_code"):
                status_code = response.status_code
            elif isinstance(response, tuple) and len(response) >= 2:
                status_code = response[1]
            else:
                status_code = 200

            # Determine cache status (check if metrics_cache was accessed)
            cache_hit = _detect_cache_hit(kwargs)

            # Log performance data
            logger.info(
                "[PERF] Route timing",
                extra={
                    "type": "route",
                    "route": route_name,
                    "duration_ms": round(duration_ms, 2),
                    "status_code": status_code,
                    "cache_hit": cache_hit,
                    "route_args": str(args) if args else None,
                    "kwargs": {k: v for k, v in kwargs.items() if k not in ["request", "session"]},
                },
            )

            return response

        except Exception as e:
            # Log error with timing
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[PERF] Route error: {route_name}",
                extra={
                    "type": "route",
                    "route": route_name,
                    "duration_ms": round(duration_ms, 2),
                    "status_code": 500,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    return wrapper


def timed_api_call(operation: str) -> Callable:
    """Decorator to time API calls in collectors.

    Logs operation name, duration, and success/failure status.

    Args:
        operation: Name of the API operation (e.g., 'github_fetch_prs')

    Returns:
        Decorator function

    Example:
        @timed_api_call('github_fetch_prs')
        def fetch_pull_requests(self, repo):
            # ... fetch PRs
            return prs
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log success
                logger.info(
                    f"[PERF] API call: {operation}",
                    extra={
                        "type": "api_call",
                        "operation": operation,
                        "duration_ms": round(duration_ms, 2),
                        "success": True,
                    },
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log failure
                logger.warning(
                    f"[PERF] API call failed: {operation}",
                    extra={
                        "type": "api_call",
                        "operation": operation,
                        "duration_ms": round(duration_ms, 2),
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

        return wrapper

    return decorator


@contextmanager
def timed_operation(operation: str, metadata: Optional[Dict[str, Any]] = None):
    """Context manager for timing arbitrary operations.

    Args:
        operation: Name of the operation being timed
        metadata: Optional metadata to include in log entry

    Yields:
        None

    Example:
        with timed_operation('database_query', {'table': 'metrics'}):
            results = db.query(...)
    """
    start_time = time.perf_counter()

    try:
        yield
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_data = {"type": "operation", "operation": operation, "duration_ms": round(duration_ms, 2), "success": True}

        if metadata:
            log_data.update(metadata)

        logger.info(f"[PERF] Operation: {operation}", extra=log_data)

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_data = {
            "type": "operation",
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

        if metadata:
            log_data.update(metadata)

        logger.error(f"[PERF] Operation failed: {operation}", extra=log_data)
        raise


def _detect_cache_hit(kwargs: Dict[str, Any]) -> bool:
    """Detect if a route used cached data.

    This is a heuristic based on common patterns in the codebase.
    A more sophisticated implementation could track cache access explicitly.

    Args:
        kwargs: Route keyword arguments

    Returns:
        True if cache was likely used, False otherwise
    """
    # Simple heuristic: if 'env' or 'range' is in kwargs, it's using cache
    # More sophisticated detection would require explicit cache tracking
    return "env" in kwargs or "range" in kwargs or "team_name" in kwargs
