"""Performance monitoring decorator for dashboard routes.

Presentation layer wrapper for Infrastructure performance monitoring.
This maintains Clean Architecture by keeping the decorator in the same
layer as the blueprints, while delegating to Infrastructure for actual timing.

This module is part of the Presentation layer (src/dashboard/) and provides
a clean interface for blueprints to use performance monitoring without
directly importing from Infrastructure (src/utils/).

Architecture:
    Presentation (blueprints) → Presentation (this decorator) → Infrastructure (performance utilities)

Usage:
    from src.dashboard.utils.performance_decorator import timed_route

    @bp.route('/my-route')
    @timed_route
    def my_route():
        return render_template('my_template.html')
"""

from functools import wraps
from typing import Callable

from flask import current_app

from src.utils.performance import timed_route as infrastructure_timed_route


def timed_route(func: Callable) -> Callable:
    """Decorator to time Flask route execution.

    Presentation layer decorator that wraps Infrastructure timing functionality.
    Use this instead of importing from src.utils.performance directly in blueprints.

    This maintains Clean Architecture by:
    1. Keeping performance monitoring in blueprints' layer (Presentation)
    2. Delegating actual timing to Infrastructure layer
    3. Using Flask's current_app.logger (Presentation concern)

    Args:
        func: Flask route function to time

    Returns:
        Wrapped function that logs timing information

    Example:
        @bp.route('/team/<team_name>')
        @timed_route
        def team_dashboard(team_name):
            return render_template('team.html')

    Note:
        The Infrastructure timed_route decorator handles the actual timing logic.
        This wrapper simply provides a Presentation-layer interface.
    """
    # Delegate to Infrastructure decorator
    # The Infrastructure decorator will use its own logger, which is fine
    # since logging is a cross-cutting concern handled by Infrastructure
    return infrastructure_timed_route(func)
