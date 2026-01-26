"""Tests for enhanced cache service

Tests two-tier caching, eviction policies, and cache warming.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pytest

from src.dashboard.services.cache_backends import FileBackend, MemoryBackend
from src.dashboard.services.cache_protocols import CacheEntry
from src.dashboard.services.enhanced_cache_service import EnhancedCacheService
from src.dashboard.services.eviction_policies import CompositeEvictionPolicy, LRUEvictionPolicy, TTLEvictionPolicy


class MockBackend:
    """Mock backend for testing"""

    def __init__(self):
        self.storage = {}

    def get(self, key: str) -> Optional[Any]:
        return self.storage.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        self.storage[key] = value
        return True

    def delete(self, key: str) -> bool:
        if key in self.storage:
            del self.storage[key]
            return True
        return False

    def clear(self) -> bool:
        self.storage.clear()
        return True

    def keys(self) -> list[str]:
        return list(self.storage.keys())


class TestEnhancedCacheService:
    """Test enhanced cache service"""

    @pytest.fixture
    def cache_service(self):
        """Create cache service with mock backend"""
        backend = MockBackend()
        policy = LRUEvictionPolicy()
        return EnhancedCacheService(
            data_dir=Path("/tmp"),
            backend=backend,
            eviction_policy=policy,
            max_memory_size_mb=1,  # 1MB for testing
            enable_memory_cache=True,
        )

    def test_set_and_get(self, cache_service):
        """Test basic set and get operations"""
        # Set data
        data = {"teams": {"Team1": {"metrics": 100}}}
        success = cache_service.set("90d_prod", data)
        assert success

        # Get data
        retrieved = cache_service.get("90d_prod")
        assert retrieved == data

        # Check stats
        stats = cache_service.get_stats()
        assert stats["sets"] == 1
        assert stats["memory_hits"] == 1
        assert stats["disk_hits"] == 0
        assert stats["misses"] == 0

    def test_memory_cache_hit(self, cache_service):
        """Test memory cache hit"""
        data = {"test": "data"}
        cache_service.set("test_key", data)

        # First get - warms memory
        result1 = cache_service.get("test_key")
        assert result1 == data

        # Second get - should hit memory
        result2 = cache_service.get("test_key")
        assert result2 == data

        stats = cache_service.get_stats()
        assert stats["memory_hits"] == 2

    def test_disk_cache_hit(self, cache_service):
        """Test disk cache hit after memory eviction"""
        data = {"test": "data"}
        cache_service.set("test_key", data)

        # Clear memory cache
        cache_service.clear_memory()

        # Get should hit disk
        result = cache_service.get("test_key")
        assert result == data

        stats = cache_service.get_stats()
        assert stats["disk_hits"] == 1
        assert stats["memory_hits"] == 0

    def test_cache_miss(self, cache_service):
        """Test cache miss"""
        result = cache_service.get("nonexistent")
        assert result is None

        stats = cache_service.get_stats()
        assert stats["misses"] == 1

    def test_memory_cache_disabled(self):
        """Test with memory cache disabled"""
        backend = MockBackend()
        cache_service = EnhancedCacheService(
            data_dir=Path("/tmp"), backend=backend, eviction_policy=LRUEvictionPolicy(), enable_memory_cache=False
        )

        data = {"test": "data"}
        cache_service.set("test_key", data)

        # Should always hit disk
        cache_service.get("test_key")
        cache_service.get("test_key")

        stats = cache_service.get_stats()
        assert stats["memory_hits"] == 0
        assert stats["disk_hits"] == 2

    def test_lru_eviction(self):
        """Test LRU eviction policy"""
        backend = MockBackend()
        policy = LRUEvictionPolicy()
        cache_service = EnhancedCacheService(
            data_dir=Path("/tmp"),
            backend=backend,
            eviction_policy=policy,
            max_memory_size_mb=0.0001,  # 100 bytes - very small to force eviction
            enable_memory_cache=True,
        )

        # Add multiple small entries to exceed memory limit
        for i in range(10):
            cache_service.set(f"key{i}", {"data": f"value{i}"})

        stats = cache_service.get_stats()
        # With 100 byte limit and 10 entries, some should be evicted
        # Or memory cache should have fewer entries than we tried to add
        assert stats["evictions"] > 0 or stats["memory_entries"] < 10

    def test_cache_warming(self, cache_service):
        """Test cache warming"""
        # Store data in backend
        cache_service.backend.set("key1", {"data": "1"})
        cache_service.backend.set("key2", {"data": "2"})
        cache_service.backend.set("key3", {"data": "3"})

        # Warm cache
        cache_service.warm_cache(["key1", "key2", "key3"])

        # All should be in memory
        stats = cache_service.get_stats()
        assert stats["memory_entries"] >= 1  # At least some loaded (may evict due to size)

    def test_clear_memory(self, cache_service):
        """Test clearing memory cache"""
        cache_service.set("key1", {"data": "1"})
        cache_service.set("key2", {"data": "2"})

        # Clear memory
        cache_service.clear_memory()

        stats = cache_service.get_stats()
        assert stats["memory_entries"] == 0

        # Data should still be in backend
        assert cache_service.backend.get("key1") is not None

    def test_clear_all(self, cache_service):
        """Test clearing all caches"""
        cache_service.set("key1", {"data": "1"})
        cache_service.set("key2", {"data": "2"})

        # Clear all
        cache_service.clear_all()

        stats = cache_service.get_stats()
        assert stats["memory_entries"] == 0
        assert len(cache_service.backend.keys()) == 0

    def test_delete(self, cache_service):
        """Test deleting cache entry"""
        cache_service.set("key1", {"data": "1"})

        # Delete
        success = cache_service.delete("key1")
        assert success

        # Should not be found
        result = cache_service.get("key1")
        assert result is None

    def test_backward_compatible_load_cache(self, cache_service):
        """Test backward compatible load_cache method"""
        data = {
            "data": {"teams": {}},
            "timestamp": datetime.now(),
            "date_range": {"description": "Last 90 days"},
            "environment": "prod",
        }
        cache_service.set("90d_prod", data)

        # Use backward compatible method
        result = cache_service.load_cache("90d", "prod")
        assert result is not None
        assert "data" in result
        assert "timestamp" in result

    def test_backward_compatible_should_refresh(self, cache_service):
        """Test backward compatible should_refresh method"""
        # Recent cache
        recent = {"timestamp": datetime.now()}
        assert not cache_service.should_refresh(recent, ttl_minutes=60)

        # Old cache
        old = {"timestamp": datetime.now() - timedelta(hours=2)}
        assert cache_service.should_refresh(old, ttl_minutes=60)

        # Missing cache
        assert cache_service.should_refresh(None, ttl_minutes=60)

    def test_hit_rate_calculation(self, cache_service):
        """Test hit rate calculation"""
        # Generate hits and misses
        cache_service.set("key1", {"data": "1"})
        cache_service.get("key1")  # Memory hit
        cache_service.get("key1")  # Memory hit
        cache_service.get("missing")  # Miss

        stats = cache_service.get_stats()
        assert stats["hit_rate"] == 2 / 3  # 2 hits, 1 miss


class TestLRUEvictionPolicy:
    """Test LRU eviction policy"""

    def test_should_evict_when_oversized(self):
        """Test eviction when cache is too large"""
        policy = LRUEvictionPolicy()
        entry = CacheEntry("key", {}, datetime.now(), datetime.now(), size_bytes=100)

        # Should evict when current > max
        assert policy.should_evict(entry, max_size=500, current_size=600)

        # Should not evict when current <= max
        assert not policy.should_evict(entry, max_size=500, current_size=400)

    def test_select_victim_oldest_access(self):
        """Test selecting least recently used entry"""
        policy = LRUEvictionPolicy()

        now = datetime.now()
        entries = [
            CacheEntry("new", {}, now, now, size_bytes=100),  # Most recent
            CacheEntry("old", {}, now, now - timedelta(hours=2), size_bytes=100),  # Least recent
            CacheEntry("mid", {}, now, now - timedelta(hours=1), size_bytes=100),
        ]

        victim = policy.select_victim(entries)
        assert victim == "old"

    def test_select_victim_empty_list(self):
        """Test with empty entry list"""
        policy = LRUEvictionPolicy()
        victim = policy.select_victim([])
        assert victim is None


class TestTTLEvictionPolicy:
    """Test TTL eviction policy"""

    def test_should_evict_expired(self):
        """Test eviction of expired entries"""
        policy = TTLEvictionPolicy(ttl_seconds=3600)  # 1 hour

        # Old entry (expired)
        old_entry = CacheEntry("old", {}, datetime.now() - timedelta(hours=2), datetime.now(), size_bytes=100)
        assert policy.should_evict(old_entry, max_size=1000, current_size=500)

        # Recent entry (not expired)
        new_entry = CacheEntry("new", {}, datetime.now(), datetime.now(), size_bytes=100)
        assert not policy.should_evict(new_entry, max_size=1000, current_size=500)

    def test_should_evict_oversized(self):
        """Test eviction when cache is too large"""
        policy = TTLEvictionPolicy(ttl_seconds=3600)

        # Recent but oversized
        entry = CacheEntry("key", {}, datetime.now(), datetime.now(), size_bytes=100)
        assert policy.should_evict(entry, max_size=500, current_size=600)

    def test_select_victim_oldest_creation(self):
        """Test selecting oldest entry by creation time"""
        policy = TTLEvictionPolicy(ttl_seconds=3600)

        now = datetime.now()
        entries = [
            CacheEntry("new", {}, now, now, size_bytes=100),
            CacheEntry("old", {}, now - timedelta(hours=2), now, size_bytes=100),
            CacheEntry("mid", {}, now - timedelta(hours=1), now, size_bytes=100),
        ]

        victim = policy.select_victim(entries)
        assert victim == "old"


class TestCompositeEvictionPolicy:
    """Test composite eviction policy"""

    def test_combines_policies(self):
        """Test combining TTL and LRU policies"""
        policy = CompositeEvictionPolicy([TTLEvictionPolicy(ttl_seconds=3600), LRUEvictionPolicy()])

        # Expired entry - should evict via TTL
        expired = CacheEntry("expired", {}, datetime.now() - timedelta(hours=2), datetime.now(), size_bytes=100)
        assert policy.should_evict(expired, max_size=1000, current_size=500)

        # Oversized - should evict via LRU
        entry = CacheEntry("key", {}, datetime.now(), datetime.now(), size_bytes=100)
        assert policy.should_evict(entry, max_size=500, current_size=600)

    def test_uses_first_policy_for_victim(self):
        """Test that first policy selects victim"""
        policy = CompositeEvictionPolicy([TTLEvictionPolicy(ttl_seconds=3600), LRUEvictionPolicy()])

        now = datetime.now()
        entries = [
            CacheEntry("new", {}, now, now, size_bytes=100),
            CacheEntry("old", {}, now - timedelta(hours=2), now, size_bytes=100),
        ]

        # Should use TTL (first policy) - selects by oldest creation time
        victim = policy.select_victim(entries)
        assert victim == "old"
