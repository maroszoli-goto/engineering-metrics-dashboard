"""Event type definitions for cache invalidation.

Defines the structure and types of events that trigger cache invalidation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# Event type constants
DATA_COLLECTED = "data_collected"
CONFIG_CHANGED = "config_changed"
MANUAL_REFRESH = "manual_refresh"
CACHE_CLEARED = "cache_cleared"


@dataclass
class DataCollectedEvent:
    """Event published when new metrics data is collected.

    This event triggers cache invalidation for the collected date range
    and environment.
    """

    date_range: str  # e.g., "90d", "30d", "Q1-2025"
    environment: str  # e.g., "prod", "uat"
    timestamp: datetime
    teams_count: int
    persons_count: int
    collection_duration_seconds: Optional[float] = None

    def get_cache_key(self) -> str:
        """Get cache key for this data collection.

        Returns:
            Cache key string (e.g., "90d_prod")
        """
        return f"{self.date_range}_{self.environment}"


@dataclass
class ConfigChangedEvent:
    """Event published when application configuration changes.

    This event triggers full cache invalidation since config changes
    may affect how metrics are calculated.
    """

    timestamp: datetime
    changed_sections: List[str]  # e.g., ["teams", "performance_weights"]
    requires_full_invalidation: bool = True


@dataclass
class ManualRefreshEvent:
    """Event published when user manually triggers a refresh.

    This event triggers cache invalidation for the specified scope.
    """

    timestamp: datetime
    scope: str  # "all", "team:<name>", "person:<username>"
    date_range: Optional[str] = None
    environment: Optional[str] = None
    triggered_by: Optional[str] = None  # Username or system component

    def get_cache_key(self) -> Optional[str]:
        """Get cache key if scope is specific.

        Returns:
            Cache key string or None for full invalidation
        """
        if self.date_range and self.environment:
            return f"{self.date_range}_{self.environment}"
        return None


@dataclass
class CacheClearedEvent:
    """Event published when cache is manually cleared.

    This is an informational event for logging/monitoring.
    """

    timestamp: datetime
    cache_keys_cleared: List[str]
    triggered_by: Optional[str] = None


def create_data_collected_event(
    date_range: str,
    environment: str,
    teams_count: int,
    persons_count: int,
    collection_duration_seconds: Optional[float] = None,
) -> DataCollectedEvent:
    """Factory function to create DataCollectedEvent.

    Args:
        date_range: Date range collected (e.g., "90d")
        environment: Environment collected (e.g., "prod")
        teams_count: Number of teams collected
        persons_count: Number of persons collected
        collection_duration_seconds: Time taken to collect

    Returns:
        DataCollectedEvent instance
    """
    return DataCollectedEvent(
        date_range=date_range,
        environment=environment,
        timestamp=datetime.now(),
        teams_count=teams_count,
        persons_count=persons_count,
        collection_duration_seconds=collection_duration_seconds,
    )


def create_config_changed_event(changed_sections: List[str]) -> ConfigChangedEvent:
    """Factory function to create ConfigChangedEvent.

    Args:
        changed_sections: List of config sections that changed

    Returns:
        ConfigChangedEvent instance
    """
    return ConfigChangedEvent(
        timestamp=datetime.now(),
        changed_sections=changed_sections,
        requires_full_invalidation=True,
    )


def create_manual_refresh_event(
    scope: str = "all",
    date_range: Optional[str] = None,
    environment: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> ManualRefreshEvent:
    """Factory function to create ManualRefreshEvent.

    Args:
        scope: Scope of refresh ("all", "team:<name>", "person:<username>")
        date_range: Optional date range
        environment: Optional environment
        triggered_by: Username or component that triggered refresh

    Returns:
        ManualRefreshEvent instance
    """
    return ManualRefreshEvent(
        timestamp=datetime.now(),
        scope=scope,
        date_range=date_range,
        environment=environment,
        triggered_by=triggered_by,
    )


def create_cache_cleared_event(
    cache_keys_cleared: List[str],
    triggered_by: Optional[str] = None,
) -> CacheClearedEvent:
    """Factory function to create CacheClearedEvent.

    Args:
        cache_keys_cleared: List of cache keys that were cleared
        triggered_by: Username or component that triggered clear

    Returns:
        CacheClearedEvent instance
    """
    return CacheClearedEvent(
        timestamp=datetime.now(),
        cache_keys_cleared=cache_keys_cleared,
        triggered_by=triggered_by,
    )
