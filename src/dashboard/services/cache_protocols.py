"""Cache protocols and data structures

Defines interfaces and data classes for the enhanced cache service.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata

    Tracks creation time, access patterns, and size for eviction decisions.
    """

    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0

    def update_access(self):
        """Update access metadata"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics tracking

    Tracks hit rates, evictions, and cache performance metrics.
    """

    memory_hits: int = 0
    disk_hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0

    def hit_rate(self) -> float:
        """Calculate overall cache hit rate"""
        total = self.memory_hits + self.disk_hits + self.misses
        if total == 0:
            return 0.0
        return (self.memory_hits + self.disk_hits) / total

    def memory_hit_rate(self) -> float:
        """Calculate memory-only hit rate"""
        total = self.memory_hits + self.disk_hits + self.misses
        if total == 0:
            return 0.0
        return self.memory_hits / total


class CacheBackend(Protocol):
    """Protocol for cache backends (file, memory, redis, etc.)

    Defines the interface that all cache backends must implement.
    Allows swapping between file-based, Redis, or other storage.
    """

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from backend

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        ...

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store value in backend

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        ...

    def delete(self, key: str) -> bool:
        """Delete value from backend

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        ...

    def clear(self) -> bool:
        """Clear all values from backend

        Returns:
            True if successful
        """
        ...

    def keys(self) -> list[str]:
        """Get all keys in backend

        Returns:
            List of cache keys
        """
        ...


class EvictionPolicy(Protocol):
    """Protocol for eviction policies

    Defines the interface for cache eviction strategies (LRU, TTL, etc.).
    """

    def should_evict(self, entry: CacheEntry, max_size: int, current_size: int) -> bool:
        """Check if an entry should be evicted

        Args:
            entry: Cache entry to check
            max_size: Maximum cache size in bytes
            current_size: Current cache size in bytes

        Returns:
            True if entry should be evicted
        """
        ...

    def select_victim(self, entries: list[CacheEntry]) -> Optional[str]:
        """Select which entry to evict

        Args:
            entries: List of cache entries to choose from

        Returns:
            Key of entry to evict, or None if no victim found
        """
        ...
