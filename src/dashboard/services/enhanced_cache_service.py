"""Enhanced cache service with memory layer and eviction policies

Provides two-tier caching (memory + disk) with configurable eviction strategies.
"""

import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .cache_backends import FileBackend
from .cache_protocols import CacheBackend, CacheEntry, CacheStats, EvictionPolicy
from .eviction_policies import LRUEvictionPolicy


class EnhancedCacheService:
    """Enhanced cache service with memory layer and eviction policies

    Features:
    - Two-tier cache (memory + disk)
    - Configurable eviction policies (LRU, TTL)
    - Cache warming
    - Statistics tracking
    - Thread-safe operations

    Example:
        >>> from pathlib import Path
        >>> from .cache_backends import FileBackend
        >>> from .eviction_policies import LRUEvictionPolicy
        >>>
        >>> backend = FileBackend(Path("data"))
        >>> policy = LRUEvictionPolicy()
        >>> cache = EnhancedCacheService(
        ...     data_dir=Path("data"),
        ...     backend=backend,
        ...     eviction_policy=policy,
        ...     max_memory_size_mb=100
        ... )
        >>>
        >>> # Store data
        >>> cache.set("90d_prod", {"teams": {...}})
        >>>
        >>> # Retrieve data (fast from memory if cached)
        >>> data = cache.get("90d_prod")
    """

    def __init__(
        self,
        data_dir: Path,
        backend: Optional[CacheBackend] = None,
        eviction_policy: Optional[EvictionPolicy] = None,
        max_memory_size_mb: int = 500,
        enable_memory_cache: bool = True,
        logger=None,
    ):
        """Initialize enhanced cache service

        Args:
            data_dir: Directory containing cache files
            backend: Cache backend (defaults to FileBackend)
            eviction_policy: Eviction policy (defaults to LRUEvictionPolicy)
            max_memory_size_mb: Maximum memory cache size in MB (default: 500)
            enable_memory_cache: Whether to enable memory caching (default: True)
            logger: Optional logger instance
        """
        self.data_dir = data_dir
        self.backend = backend or FileBackend(data_dir, logger)
        self.eviction_policy = eviction_policy or LRUEvictionPolicy()
        self.max_memory_size = max_memory_size_mb * 1024 * 1024  # Convert to bytes
        self.enable_memory_cache = enable_memory_cache
        self.logger = logger

        # Memory cache (in-process)
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory → disk)

        Checks memory cache first (fast), then falls back to disk.
        Updates access statistics and warms memory cache on disk hits.

        Args:
            key: Cache key (e.g., "90d_prod")

        Returns:
            Cached data or None if not found

        Example:
            >>> cache = EnhancedCacheService(Path("data"))
            >>> data = cache.get("90d_prod")
            >>> if data:
            ...     print(f"Teams: {len(data['teams'])}")
        """
        with self._lock:
            # Try memory cache first
            if self.enable_memory_cache and key in self._memory_cache:
                entry = self._memory_cache[key]

                # Check if expired
                if self.eviction_policy.should_evict(entry, self.max_memory_size, self._current_size()):
                    del self._memory_cache[key]
                    self._stats.evictions += 1
                    if self.logger:
                        self.logger.debug(f"Evicted expired entry from memory: {key}")
                else:
                    # Update access metadata
                    entry.update_access()
                    self._stats.memory_hits += 1
                    if self.logger:
                        self.logger.debug(f"Memory cache hit: {key}")
                    return entry.data

            # Try disk cache
            disk_data = self.backend.get(key)
            if disk_data:
                self._stats.disk_hits += 1
                if self.logger:
                    self.logger.debug(f"Disk cache hit: {key}")

                # Warm memory cache
                if self.enable_memory_cache:
                    self._add_to_memory(key, disk_data)

                return disk_data

            # Cache miss
            self._stats.misses += 1
            if self.logger:
                self.logger.debug(f"Cache miss: {key}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in cache (memory + disk)

        Stores value in both memory and disk caches.
        Applies eviction policy if memory is full.

        Args:
            key: Cache key (e.g., "90d_prod")
            value: Data to cache
            ttl_seconds: Optional time-to-live in seconds

        Returns:
            True if successful, False otherwise

        Example:
            >>> cache = EnhancedCacheService(Path("data"))
            >>> success = cache.set("90d_prod", {"teams": {...}})
            >>> print(f"Cached: {success}")
        """
        with self._lock:
            # Save to disk
            success = self.backend.set(key, value, ttl_seconds)
            if not success:
                if self.logger:
                    self.logger.error(f"Failed to save to disk: {key}")
                return False

            # Add to memory cache
            if self.enable_memory_cache:
                self._add_to_memory(key, value)

            self._stats.sets += 1
            if self.logger:
                self.logger.debug(f"Cache set: {key}")
            return True

    def delete(self, key: str) -> bool:
        """Delete value from cache (memory + disk)

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            # Delete from memory
            if key in self._memory_cache:
                del self._memory_cache[key]

            # Delete from disk
            return self.backend.delete(key)

    def clear_memory(self):
        """Clear memory cache only (keep disk)

        Useful for forcing reload from disk or reducing memory usage.
        """
        with self._lock:
            count = len(self._memory_cache)
            self._memory_cache.clear()
            if self.logger:
                self.logger.info(f"Cleared {count} entries from memory cache")

    def clear_all(self):
        """Clear both memory and disk caches

        Warning: This deletes all cached data!
        """
        with self._lock:
            self._memory_cache.clear()
            self.backend.clear()
            if self.logger:
                self.logger.info("Cleared all caches (memory + disk)")

    def warm_cache(self, keys: list[str]):
        """Pre-load cache entries into memory

        Useful for warming the cache on application startup.

        Args:
            keys: List of cache keys to warm (e.g., ["90d_prod", "30d_prod"])

        Example:
            >>> cache = EnhancedCacheService(Path("data"))
            >>> cache.warm_cache(["90d_prod", "30d_prod", "180d_prod"])
            >>> # Now these entries are in memory for fast access
        """
        warmed = 0
        for key in keys:
            data = self.backend.get(key)
            if data and self.enable_memory_cache:
                self._add_to_memory(key, data)
                warmed += 1

        if self.logger:
            self.logger.info(f"Cache warmed with {warmed}/{len(keys)} entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Dictionary with cache performance metrics

        Example:
            >>> cache = EnhancedCacheService(Path("data"))
            >>> stats = cache.get_stats()
            >>> print(f"Hit rate: {stats['hit_rate']:.1%}")
            >>> print(f"Memory entries: {stats['memory_entries']}")
        """
        with self._lock:
            return {
                "memory_hits": self._stats.memory_hits,
                "disk_hits": self._stats.disk_hits,
                "misses": self._stats.misses,
                "hit_rate": self._stats.hit_rate(),
                "memory_hit_rate": self._stats.memory_hit_rate(),
                "evictions": self._stats.evictions,
                "sets": self._stats.sets,
                "memory_entries": len(self._memory_cache),
                "memory_size_mb": self._current_size() / (1024 * 1024),
                "max_memory_mb": self.max_memory_size / (1024 * 1024),
                "memory_utilization": (
                    self._current_size() / self.max_memory_size if self.max_memory_size > 0 else 0.0
                ),
            }

    def _add_to_memory(self, key: str, data: Any):
        """Add entry to memory cache with eviction

        Internal method that handles memory cache population and eviction.

        Args:
            key: Cache key
            data: Data to cache
        """
        entry = CacheEntry(
            key=key,
            data=data,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=0,
            size_bytes=sys.getsizeof(data),
        )

        # Evict if necessary
        current_size = self._current_size()
        attempts = 0
        max_attempts = len(self._memory_cache) + 1  # Prevent infinite loop

        while current_size + entry.size_bytes > self.max_memory_size and self._memory_cache and attempts < max_attempts:
            victim_key = self.eviction_policy.select_victim(list(self._memory_cache.values()))
            if victim_key and victim_key in self._memory_cache:
                del self._memory_cache[victim_key]
                self._stats.evictions += 1
                current_size = self._current_size()
                if self.logger:
                    self.logger.debug(f"Evicted victim from memory: {victim_key}")
            else:
                break  # No victim found or already deleted
            attempts += 1

        # Only add if there's space (or cache is empty)
        if current_size + entry.size_bytes <= self.max_memory_size or not self._memory_cache:
            self._memory_cache[key] = entry
            if self.logger:
                self.logger.debug(f"Added to memory cache: {key} ({entry.size_bytes / 1024:.1f} KB)")

    def _current_size(self) -> int:
        """Calculate current memory cache size in bytes

        Returns:
            Total size of all cached entries in bytes
        """
        return sum(entry.size_bytes for entry in self._memory_cache.values())

    # Backward compatibility methods (delegate to existing CacheService interface)

    def load_cache(self, range_key: str = "90d", environment: str = "prod") -> Optional[Dict[str, Any]]:
        """Load cached metrics (backward compatible with CacheService)

        Delegates to get() with key format "range_environment".

        Args:
            range_key: Date range key (e.g., '90d', 'Q1-2025')
            environment: Environment name (e.g., 'prod', 'uat')

        Returns:
            Dictionary containing cached metrics data, or None
        """
        key = f"{range_key}_{environment}"
        cache_data = self.get(key)

        if cache_data is None:
            return None

        # Build result dictionary with metadata (compatible format)
        result = {
            "data": cache_data.get("data") or cache_data,
            "timestamp": cache_data.get("timestamp"),
            "range_key": range_key,
            "date_range": cache_data.get("date_range", {}),
            "environment": cache_data.get("environment", environment),
            "time_offset_days": cache_data.get("time_offset_days", 0),
            "jira_server": cache_data.get("jira_server", ""),
        }

        return result

    def should_refresh(self, cache_data: Optional[Dict], ttl_minutes: int = 60) -> bool:
        """Check if cache should be refreshed (backward compatible)

        Args:
            cache_data: Current cache data dictionary
            ttl_minutes: Time-to-live in minutes

        Returns:
            True if cache should be refreshed
        """
        if cache_data is None or cache_data.get("timestamp") is None:
            return True

        elapsed = (datetime.now() - cache_data["timestamp"]).total_seconds() / 60
        return bool(elapsed > ttl_minutes)

    def get_available_ranges(self) -> List[Tuple[str, str, bool]]:
        """Get list of available cached date ranges (backward compatible)

        Scans the data directory for cached metrics files and returns
        information about available date ranges.

        Returns:
            List of (range_key, description, file_exists) tuples
            Example: [('90d', 'Last 90 days', True), ('Q1-2025', 'Q1 2025', True)]
        """
        import pickle

        from src.utils.date_ranges import get_cache_filename, get_preset_ranges

        available = []

        # Check preset ranges
        for range_spec, description in get_preset_ranges():
            try:
                cache_filename = get_cache_filename(range_spec)
                cache_file = Path(self.backend.data_dir) / cache_filename
                if cache_file.exists():
                    # Try to load date range info from cache
                    try:
                        with open(cache_file, "rb") as f:
                            cache_data = pickle.load(f)
                            if "date_range" in cache_data:
                                description = cache_data["date_range"].get("description", description)
                    except Exception:
                        pass
                    available.append((range_spec, description, True))
            except ValueError:
                # Invalid range_spec, skip it
                if self.logger:
                    self.logger.warning(f"Skipping invalid preset range: {range_spec}")
                continue

        # Check for other cached files (quarters, years, custom)
        data_dir = Path(self.backend.data_dir)
        if data_dir.exists():
            for cache_file in data_dir.glob("metrics_cache_*.pkl"):
                range_key = cache_file.stem.replace("metrics_cache_", "")
                # Remove environment suffix if present
                if "_" in range_key:
                    range_key = range_key.rsplit("_", 1)[0]

                if range_key not in [r[0] for r in available]:
                    # Validate range_key before using it
                    try:
                        # This will raise ValueError if invalid
                        _ = get_cache_filename(range_key)
                        # Try to get description from cache
                        try:
                            with open(cache_file, "rb") as f:
                                cache_data = pickle.load(f)
                                if "date_range" in cache_data:
                                    description = cache_data["date_range"].get("description", range_key)
                                else:
                                    description = range_key
                                available.append((range_key, description, True))
                        except Exception:
                            available.append((range_key, range_key, True))
                    except ValueError:
                        # Invalid range_key in filename, skip it
                        if self.logger:
                            self.logger.warning(f"Skipping invalid cache file: {cache_file}")
                        continue

        return available
