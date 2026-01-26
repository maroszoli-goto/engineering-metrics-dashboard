"""Event-driven cache service with automatic invalidation.

Extends CacheService to support event-driven cache invalidation:
- Subscribes to data collection events
- Subscribes to config change events
- Subscribes to manual refresh events
- Automatically invalidates affected cache entries
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from src.dashboard.events import get_event_bus
from src.dashboard.events.types import (
    CONFIG_CHANGED,
    DATA_COLLECTED,
    MANUAL_REFRESH,
    ConfigChangedEvent,
    DataCollectedEvent,
    ManualRefreshEvent,
)
from src.dashboard.services.cache_service import CacheService


class EventDrivenCacheService(CacheService):
    """Cache service with event-driven invalidation.

    Automatically invalidates cache entries when:
    - New data is collected
    - Configuration changes
    - Manual refresh is triggered

    Maintains an in-memory set of invalidated keys for tracking.
    """

    def __init__(self, data_dir: Path, logger=None, auto_subscribe: bool = True):
        """Initialize event-driven cache service.

        Args:
            data_dir: Directory containing cache files
            logger: Optional logger instance
            auto_subscribe: Whether to automatically subscribe to events
        """
        super().__init__(data_dir, logger)

        # Track invalidated cache keys
        self._invalidated_keys: Set[str] = set()

        # Event bus
        self._event_bus = get_event_bus()

        # Subscribe to events
        if auto_subscribe:
            self.subscribe_to_events()

    def subscribe_to_events(self):
        """Subscribe to cache invalidation events."""
        self._event_bus.subscribe(DATA_COLLECTED, self._handle_data_collected)
        self._event_bus.subscribe(CONFIG_CHANGED, self._handle_config_changed)
        self._event_bus.subscribe(MANUAL_REFRESH, self._handle_manual_refresh)

        if self.logger:
            self.logger.info("EventDrivenCacheService subscribed to invalidation events")

    def unsubscribe_from_events(self):
        """Unsubscribe from cache invalidation events."""
        self._event_bus.unsubscribe(DATA_COLLECTED, self._handle_data_collected)
        self._event_bus.unsubscribe(CONFIG_CHANGED, self._handle_config_changed)
        self._event_bus.unsubscribe(MANUAL_REFRESH, self._handle_manual_refresh)

        if self.logger:
            self.logger.info("EventDrivenCacheService unsubscribed from events")

    def _handle_data_collected(self, event: DataCollectedEvent):
        """Handle data collection event.

        Args:
            event: DataCollectedEvent instance
        """
        cache_key = event.get_cache_key()
        self._invalidate_key(cache_key)

        if self.logger:
            self.logger.info(
                f"Cache invalidated for {cache_key} "
                f"(collected {event.teams_count} teams, {event.persons_count} persons "
                f"in {event.collection_duration_seconds:.1f}s)"
                if event.collection_duration_seconds
                else f"Cache invalidated for {cache_key}"
            )

    def _handle_config_changed(self, event: ConfigChangedEvent):
        """Handle configuration change event.

        Args:
            event: ConfigChangedEvent instance
        """
        if event.requires_full_invalidation:
            self._invalidate_all()

            if self.logger:
                self.logger.warning(
                    f"Full cache invalidation triggered by config changes: " f"{', '.join(event.changed_sections)}"
                )
        else:
            # Partial invalidation based on changed sections
            # For now, we do full invalidation for safety
            self._invalidate_all()

    def _handle_manual_refresh(self, event: ManualRefreshEvent):
        """Handle manual refresh event.

        Args:
            event: ManualRefreshEvent instance
        """
        if event.scope == "all":
            self._invalidate_all()

            if self.logger:
                triggered_by = event.triggered_by or "system"
                self.logger.info(f"Full cache invalidation triggered by {triggered_by}")
        else:
            # Scope-specific invalidation
            cache_key = event.get_cache_key()
            if cache_key:
                self._invalidate_key(cache_key)

                if self.logger:
                    self.logger.info(f"Cache invalidated for {cache_key} (scope: {event.scope})")
            else:
                # No specific key, invalidate all
                self._invalidate_all()

    def _invalidate_key(self, cache_key: str):
        """Mark a cache key as invalidated.

        Args:
            cache_key: Cache key to invalidate (e.g., "90d_prod")
        """
        self._invalidated_keys.add(cache_key)

        if self.logger:
            self.logger.debug(f"Cache key invalidated: {cache_key}")

    def _invalidate_all(self):
        """Invalidate all cache entries."""
        # Get all available cache files
        available_ranges = self.get_available_ranges()

        for range_key, description, exists in available_ranges:
            # For now, assume 'prod' environment
            # TODO: Support multi-environment invalidation
            cache_key = f"{range_key}_prod"
            self._invalidated_keys.add(cache_key)

        if self.logger:
            self.logger.warning(f"All cache keys invalidated ({len(self._invalidated_keys)} keys)")

    def is_invalidated(self, range_key: str = "90d", environment: str = "prod") -> bool:
        """Check if a cache key is invalidated.

        Args:
            range_key: Date range key
            environment: Environment name

        Returns:
            True if invalidated, False otherwise
        """
        cache_key = f"{range_key}_{environment}"
        return cache_key in self._invalidated_keys

    def load_cache(
        self, range_key: str = "90d", environment: str = "prod", force_reload: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Load cached metrics with invalidation awareness.

        If cache is invalidated, returns None to trigger reload.

        Args:
            range_key: Date range key
            environment: Environment name
            force_reload: Force reload even if not invalidated

        Returns:
            Cached data or None if invalidated
        """
        cache_key = f"{range_key}_{environment}"

        # Check if invalidated
        if force_reload or self.is_invalidated(range_key, environment):
            if self.logger:
                self.logger.info(f"Cache invalidated for {cache_key}, returning None")

            # Clear invalidation flag after acknowledging
            if cache_key in self._invalidated_keys:
                self._invalidated_keys.remove(cache_key)

            return None

        # Load from parent class
        return super().load_cache(range_key, environment)

    def get_invalidated_keys(self) -> Set[str]:
        """Get set of invalidated cache keys.

        Returns:
            Set of invalidated cache keys
        """
        return self._invalidated_keys.copy()

    def clear_invalidated_keys(self):
        """Clear all invalidation flags."""
        self._invalidated_keys.clear()

        if self.logger:
            self.logger.debug("Cleared all invalidation flags")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        available_ranges = self.get_available_ranges()

        return {
            "available_ranges": len(available_ranges),
            "invalidated_keys": len(self._invalidated_keys),
            "invalidated_key_list": list(self._invalidated_keys),
            "event_subscribers": {
                DATA_COLLECTED: self._event_bus.get_subscriber_count(DATA_COLLECTED),
                CONFIG_CHANGED: self._event_bus.get_subscriber_count(CONFIG_CHANGED),
                MANUAL_REFRESH: self._event_bus.get_subscriber_count(MANUAL_REFRESH),
            },
        }
