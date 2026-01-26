"""Cache eviction policies

Implements different strategies for evicting cache entries when memory is full.
"""

from datetime import datetime, timedelta
from typing import Optional

from .cache_protocols import CacheEntry, EvictionPolicy


class LRUEvictionPolicy:
    """Least Recently Used (LRU) eviction policy

    Evicts the entry that was accessed least recently.
    Good for general-purpose caching.

    Example:
        >>> policy = LRUEvictionPolicy()
        >>> entries = [
        ...     CacheEntry("old", {}, datetime(2024, 1, 1), datetime(2024, 1, 1)),
        ...     CacheEntry("new", {}, datetime(2024, 1, 2), datetime(2024, 1, 2))
        ... ]
        >>> policy.select_victim(entries)
        'old'
    """

    def should_evict(self, entry: CacheEntry, max_size: int, current_size: int) -> bool:
        """Evict when cache exceeds max size

        Args:
            entry: Cache entry to check
            max_size: Maximum cache size in bytes
            current_size: Current cache size in bytes

        Returns:
            True if current size exceeds max size
        """
        return current_size > max_size

    def select_victim(self, entries: list[CacheEntry]) -> Optional[str]:
        """Select entry with oldest last_accessed time

        Args:
            entries: List of cache entries

        Returns:
            Key of least recently used entry, or None if list is empty
        """
        if not entries:
            return None

        # Find entry with oldest last_accessed timestamp
        victim = min(entries, key=lambda e: e.last_accessed)
        return victim.key


class TTLEvictionPolicy:
    """Time-To-Live (TTL) eviction policy

    Evicts entries that have exceeded their time-to-live.
    Good for time-sensitive data that becomes stale.

    Example:
        >>> from datetime import datetime, timedelta
        >>> policy = TTLEvictionPolicy(ttl_seconds=3600)  # 1 hour
        >>> old_entry = CacheEntry(
        ...     "old", {},
        ...     datetime.now() - timedelta(hours=2),
        ...     datetime.now()
        ... )
        >>> policy.should_evict(old_entry, 1000, 500)
        True
    """

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize TTL policy

        Args:
            ttl_seconds: Time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.ttl_seconds = ttl_seconds

    def should_evict(self, entry: CacheEntry, max_size: int, current_size: int) -> bool:
        """Evict if entry is expired OR cache is too large

        Args:
            entry: Cache entry to check
            max_size: Maximum cache size in bytes
            current_size: Current cache size in bytes

        Returns:
            True if entry is expired or cache is too large
        """
        # Check TTL expiration
        age = (datetime.now() - entry.created_at).total_seconds()
        is_expired = age > self.ttl_seconds

        # Check size limit
        is_oversized = current_size > max_size

        return is_expired or is_oversized

    def select_victim(self, entries: list[CacheEntry]) -> Optional[str]:
        """Select oldest entry (by creation time)

        Args:
            entries: List of cache entries

        Returns:
            Key of oldest entry, or None if list is empty
        """
        if not entries:
            return None

        # Find entry with oldest created_at timestamp
        victim = min(entries, key=lambda e: e.created_at)
        return victim.key


class CompositeEvictionPolicy:
    """Composite eviction policy that combines multiple strategies

    Applies multiple policies in sequence. Useful for combining
    TTL with LRU for example.

    Example:
        >>> policy = CompositeEvictionPolicy([
        ...     TTLEvictionPolicy(ttl_seconds=3600),
        ...     LRUEvictionPolicy()
        ... ])
    """

    def __init__(self, policies: list[EvictionPolicy]):
        """Initialize composite policy

        Args:
            policies: List of eviction policies to apply
        """
        self.policies = policies

    def should_evict(self, entry: CacheEntry, max_size: int, current_size: int) -> bool:
        """Check if ANY policy says to evict

        Args:
            entry: Cache entry to check
            max_size: Maximum cache size in bytes
            current_size: Current cache size in bytes

        Returns:
            True if any policy says to evict
        """
        return any(policy.should_evict(entry, max_size, current_size) for policy in self.policies)

    def select_victim(self, entries: list[CacheEntry]) -> Optional[str]:
        """Use first policy's victim selection

        Args:
            entries: List of cache entries

        Returns:
            Key selected by first policy, or None
        """
        if not self.policies or not entries:
            return None

        return self.policies[0].select_victim(entries)
