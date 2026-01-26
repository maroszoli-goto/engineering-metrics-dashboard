"""Event bus system for event-driven cache invalidation.

Provides a simple, lightweight event bus for decoupling components:
- Publishers emit events when data changes
- Subscribers react to events by invalidating caches

No external dependencies - pure Python implementation.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


class EventBus:
    """Simple event bus for publish-subscribe pattern.

    Allows components to subscribe to events and publish events
    without tight coupling. Thread-safe for single-threaded applications.
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._logger = logging.getLogger("team_metrics.events")

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to (e.g., "data_collected")
            callback: Function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)
        self._logger.debug(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]):
        """Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            callback: Callback function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                self._logger.debug(f"Unsubscribed from event: {event_type}")
            except ValueError:
                pass  # Callback not in list

    def publish(self, event_type: str, event_data: Any = None):
        """Publish an event to all subscribers.

        Args:
            event_type: Type of event being published
            event_data: Optional data associated with the event
        """
        if event_type not in self._subscribers:
            self._logger.debug(f"No subscribers for event: {event_type}")
            return

        subscribers = self._subscribers[event_type]
        self._logger.info(f"Publishing event: {event_type} to {len(subscribers)} subscribers")

        for callback in subscribers:
            try:
                callback(event_data)
            except Exception as e:
                self._logger.error(f"Error in subscriber callback for {event_type}: {e}")

    def clear_subscribers(self, event_type: Optional[str] = None):
        """Clear subscribers for an event type or all events.

        Args:
            event_type: Event type to clear, or None to clear all
        """
        if event_type:
            if event_type in self._subscribers:
                del self._subscribers[event_type]
                self._logger.debug(f"Cleared subscribers for: {event_type}")
        else:
            self._subscribers.clear()
            self._logger.debug("Cleared all subscribers")

    def get_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for an event type.

        Args:
            event_type: Event type to check

        Returns:
            Number of subscribers
        """
        return len(self._subscribers.get(event_type, []))


# Global event bus instance (singleton)
_global_event_bus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance.

    Returns:
        Shared EventBus instance
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus():
    """Reset the global event bus (for testing)."""
    global _global_event_bus
    _global_event_bus = None
