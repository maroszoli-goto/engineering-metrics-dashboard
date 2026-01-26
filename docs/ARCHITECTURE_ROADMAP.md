# Architecture Improvements Roadmap

## Overview

This document outlines architectural enhancements to improve maintainability, testability, and scalability of the Team Metrics Dashboard.

---

## Current State Analysis

### ✅ What's Good

1. **Clean Separation** (Week 7-8 Refactoring)
   - Blueprints: Routes organized by feature
   - Services: Business logic extracted (cache_service, metrics_refresh_service)
   - Utils: Reusable utilities (formatting, validation, etc.)
   - 86% reduction in app.py (1676 → 228 lines)

2. **Service Layer Exists**
   - `CacheService` - File-based cache management
   - `MetricsRefreshService` - Orchestrates refresh workflow
   - Located in `src/dashboard/services/`

3. **Testing**
   - 861 tests passing
   - 78.84% overall coverage
   - Unit + integration tests

### ⚠️ Areas for Improvement

1. **CacheService** (Week 8)
   - Basic file I/O only
   - No eviction policies
   - No cache warming
   - No distributed cache support

2. **Service Instantiation** (Week 11)
   - Manual instantiation in app.py
   - Tightly coupled dependencies
   - Hard to mock for testing
   - No dependency injection

3. **Architecture Documentation** (Week 12)
   - Good code organization
   - Missing: Formal layer definitions
   - Missing: Dependency rules
   - Missing: ADR (Architecture Decision Records)

---

## Improvement Plan

## Phase 1: CacheService Enhancement (Week 8)

### Goals
- Add eviction policies (LRU, TTL-based)
- Implement cache warming
- Add cache statistics/monitoring
- Prepare for distributed caching

### Current Implementation

```python
class CacheService:
    def __init__(self, data_dir: Path, logger=None):
        self.data_dir = data_dir
        self.logger = logger

    def load_cache(self, range_key: str, environment: str) -> Optional[Dict]:
        # Basic file-based loading
        pass

    def should_refresh(self, cache_data, ttl_minutes: int) -> bool:
        # Simple age-based check
        pass
```

**Limitations:**
- ❌ No memory caching (always hits disk)
- ❌ No size limits (can grow indefinitely)
- ❌ No warming strategy
- ❌ No cache statistics

### Proposed Enhancement

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Protocol
import threading

@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata"""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int

class CacheBackend(Protocol):
    """Protocol for cache backends (file, memory, redis, etc.)"""
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl_seconds: int = None) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def clear(self) -> bool: ...
    def keys(self) -> list[str]: ...

class EvictionPolicy(Protocol):
    """Protocol for eviction policies"""
    def should_evict(self, entry: CacheEntry, max_size: int, current_size: int) -> bool: ...
    def select_victim(self, entries: list[CacheEntry]) -> Optional[str]: ...

class LRUEvictionPolicy:
    """Least Recently Used eviction policy"""
    def should_evict(self, entry: CacheEntry, max_size: int, current_size: int) -> bool:
        return current_size > max_size

    def select_victim(self, entries: list[CacheEntry]) -> Optional[str]:
        if not entries:
            return None
        # Find entry with oldest last_accessed
        victim = min(entries, key=lambda e: e.last_accessed)
        return victim.key

class TTLEvictionPolicy:
    """Time-To-Live eviction policy"""
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds

    def should_evict(self, entry: CacheEntry, max_size: int, current_size: int) -> bool:
        age = (datetime.now() - entry.created_at).total_seconds()
        return age > self.ttl_seconds or current_size > max_size

    def select_victim(self, entries: list[CacheEntry]) -> Optional[str]:
        # Find oldest entry
        if not entries:
            return None
        victim = min(entries, key=lambda e: e.created_at)
        return victim.key

class EnhancedCacheService:
    """Enhanced cache service with memory layer and eviction policies

    Features:
    - Two-tier cache (memory + disk)
    - Configurable eviction policies (LRU, TTL)
    - Cache warming
    - Statistics tracking
    - Thread-safe operations
    """

    def __init__(
        self,
        data_dir: Path,
        backend: CacheBackend,
        eviction_policy: EvictionPolicy,
        max_memory_size_mb: int = 500,
        enable_memory_cache: bool = True,
        logger=None
    ):
        self.data_dir = data_dir
        self.backend = backend
        self.eviction_policy = eviction_policy
        self.max_memory_size = max_memory_size_mb * 1024 * 1024  # Convert to bytes
        self.enable_memory_cache = enable_memory_cache
        self.logger = logger

        # Memory cache (in-process)
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory → disk)"""
        with self._lock:
            # Try memory cache first
            if self.enable_memory_cache and key in self._memory_cache:
                entry = self._memory_cache[key]

                # Check if expired
                if self.eviction_policy.should_evict(entry, self.max_memory_size, self._current_size()):
                    del self._memory_cache[key]
                    self._stats.evictions += 1
                else:
                    # Update access metadata
                    entry.last_accessed = datetime.now()
                    entry.access_count += 1
                    self._stats.memory_hits += 1
                    return entry.data

            # Try disk cache
            disk_data = self.backend.get(key)
            if disk_data:
                self._stats.disk_hits += 1

                # Warm memory cache
                if self.enable_memory_cache:
                    self._add_to_memory(key, disk_data)

                return disk_data

            self._stats.misses += 1
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = None) -> bool:
        """Set value in cache (memory + disk)"""
        with self._lock:
            # Save to disk
            success = self.backend.set(key, value, ttl_seconds)
            if not success:
                return False

            # Add to memory cache
            if self.enable_memory_cache:
                self._add_to_memory(key, value)

            self._stats.sets += 1
            return True

    def _add_to_memory(self, key: str, data: Any):
        """Add entry to memory cache with eviction"""
        import sys

        entry = CacheEntry(
            key=key,
            data=data,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=0,
            size_bytes=sys.getsizeof(data)
        )

        # Evict if necessary
        current_size = self._current_size()
        while current_size + entry.size_bytes > self.max_memory_size and self._memory_cache:
            victim_key = self.eviction_policy.select_victim(list(self._memory_cache.values()))
            if victim_key:
                del self._memory_cache[victim_key]
                self._stats.evictions += 1
                current_size = self._current_size()
            else:
                break

        self._memory_cache[key] = entry

    def _current_size(self) -> int:
        """Calculate current memory cache size in bytes"""
        return sum(entry.size_bytes for entry in self._memory_cache.values())

    def warm_cache(self, keys: list[str]):
        """Pre-load cache entries into memory"""
        for key in keys:
            data = self.backend.get(key)
            if data and self.enable_memory_cache:
                self._add_to_memory(key, data)

        if self.logger:
            self.logger.info(f"Cache warmed with {len(keys)} entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_rate = 0.0
            total_requests = self._stats.memory_hits + self._stats.disk_hits + self._stats.misses
            if total_requests > 0:
                hit_rate = (self._stats.memory_hits + self._stats.disk_hits) / total_requests

            return {
                "memory_hits": self._stats.memory_hits,
                "disk_hits": self._stats.disk_hits,
                "misses": self._stats.misses,
                "hit_rate": hit_rate,
                "evictions": self._stats.evictions,
                "sets": self._stats.sets,
                "memory_entries": len(self._memory_cache),
                "memory_size_mb": self._current_size() / (1024 * 1024),
                "max_memory_mb": self.max_memory_size / (1024 * 1024),
            }

    def clear_memory(self):
        """Clear memory cache only (keep disk)"""
        with self._lock:
            self._memory_cache.clear()
            if self.logger:
                self.logger.info("Memory cache cleared")

@dataclass
class CacheStats:
    """Cache statistics tracking"""
    memory_hits: int = 0
    disk_hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0
```

### Implementation Steps

1. **Phase 1.1: Add Memory Layer** (~2-3 hours)
   - Implement two-tier caching (memory + disk)
   - Add thread-safe operations
   - Add basic statistics

2. **Phase 1.2: Add Eviction Policies** (~2 hours)
   - Implement LRU policy
   - Implement TTL policy
   - Make policies pluggable

3. **Phase 1.3: Add Cache Warming** (~1 hour)
   - Pre-load common date ranges
   - Warm on app startup
   - Background warming for scheduled refreshes

4. **Phase 1.4: Add Monitoring** (~1 hour)
   - Expose `/api/cache/stats` endpoint
   - Log cache hit/miss rates
   - Add cache size monitoring

5. **Phase 1.5: Testing** (~2 hours)
   - Unit tests for eviction policies
   - Integration tests for two-tier caching
   - Performance benchmarks

**Total Effort: ~8-10 hours**

### Benefits
- ✅ Faster response times (memory cache)
- ✅ Controlled memory usage (eviction policies)
- ✅ Better observability (statistics)
- ✅ Ready for distributed caching (protocol-based design)

---

## Phase 2: Application Factory Pattern (Week 11)

### Goals
- Implement dependency injection
- Improve testability
- Centralize configuration
- Support multiple Flask instances (testing, production)

### Current Implementation

```python
# app.py (simplified)
def create_app():
    app = Flask(__name__)

    # Manual service instantiation
    cache_service = CacheService(data_dir=Path("data"))
    metrics_service = MetricsRefreshService(config, cache_service)

    # Register blueprints
    register_blueprints(app, config, cache_service, metrics_service)

    return app
```

**Limitations:**
- ❌ Services created globally (hard to test)
- ❌ Dependencies passed manually
- ❌ No configuration flexibility
- ❌ Can't create multiple app instances easily

### Proposed Enhancement

```python
from typing import Protocol
from dataclasses import dataclass

class ServiceContainer:
    """Dependency injection container for services"""

    def __init__(self):
        self._services = {}
        self._factories = {}

    def register(self, name: str, factory: callable, singleton: bool = True):
        """Register a service factory"""
        self._factories[name] = {"factory": factory, "singleton": singleton}

    def get(self, name: str):
        """Get a service instance"""
        if name in self._services:
            return self._services[name]

        if name not in self._factories:
            raise KeyError(f"Service '{name}' not registered")

        factory_info = self._factories[name]
        instance = factory_info["factory"](self)

        if factory_info["singleton"]:
            self._services[name] = instance

        return instance

def create_app(config_path: str = "config/config.yaml", env: str = "prod"):
    """Application factory with dependency injection

    Args:
        config_path: Path to configuration file
        env: Environment name (prod, uat, dev, test)

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Create service container
    container = ServiceContainer()

    # Register services (with dependencies resolved automatically)
    container.register("config", lambda c: load_config(config_path))
    container.register("logger", lambda c: setup_logger(c.get("config")))
    container.register("cache_backend", lambda c: FileBackend(data_dir=Path("data")))
    container.register("eviction_policy", lambda c: LRUEvictionPolicy())
    container.register(
        "cache_service",
        lambda c: EnhancedCacheService(
            data_dir=Path("data"),
            backend=c.get("cache_backend"),
            eviction_policy=c.get("eviction_policy"),
            logger=c.get("logger")
        )
    )
    container.register(
        "metrics_service",
        lambda c: MetricsRefreshService(
            config=c.get("config"),
            cache_service=c.get("cache_service"),
            logger=c.get("logger")
        )
    )

    # Store container in app for access in blueprints
    app.container = container

    # Register blueprints (they use container to get dependencies)
    register_blueprints(app, container)

    return app

# In blueprints:
@dashboard_bp.route("/")
def index():
    # Get services from container
    cache_service = current_app.container.get("cache_service")
    config = current_app.container.get("config")

    # Use services
    cache_data = cache_service.get("metrics_90d_prod")
    return render_template("index.html", data=cache_data)
```

### Implementation Steps

1. **Phase 2.1: Create ServiceContainer** (~2 hours)
   - Implement container class
   - Add factory registration
   - Add singleton support

2. **Phase 2.2: Refactor app.py** (~2 hours)
   - Move to factory pattern
   - Register all services
   - Update blueprints to use container

3. **Phase 2.3: Update Tests** (~3 hours)
   - Create mock container for tests
   - Update all test fixtures
   - Verify isolation

4. **Phase 2.4: Documentation** (~1 hour)
   - Document DI pattern
   - Add examples for adding new services
   - Update developer guide

**Total Effort: ~8 hours**

### Benefits
- ✅ Better testability (easy mocking)
- ✅ Clear dependencies
- ✅ Easier to add new services
- ✅ Multiple app instances (dev/test/prod)

---

## Phase 3: Clean Architecture Foundation (Week 12)

### Goals
- Formalize layer definitions
- Document dependency rules
- Create ADR (Architecture Decision Records)
- Establish patterns for future development

### Proposed Layer Structure

```
┌─────────────────────────────────────────────┐
│         Presentation Layer                  │
│  (Blueprints, Templates, Static Assets)     │
│  - dashboard.py, api.py, export.py          │
│  - Depends on: Application Layer            │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Application Layer                   │
│  (Services, Use Cases, Orchestration)       │
│  - cache_service.py, metrics_refresh.py     │
│  - Depends on: Domain Layer                 │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Domain Layer                        │
│  (Models, Business Logic, Metrics)          │
│  - metrics.py, dora_metrics.py              │
│  - Depends on: Nothing (pure logic)         │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Infrastructure Layer                │
│  (Collectors, Utils, External APIs)         │
│  - github_graphql_collector.py, jira.py     │
│  - Depends on: Domain Layer (models only)   │
└─────────────────────────────────────────────┘
```

### Dependency Rules

1. **Presentation** → Application → Domain ✅
2. **Application** → Domain ✅
3. **Domain** → Nothing ✅
4. **Infrastructure** → Domain (models only) ✅

**Violations to Fix:**
- ❌ Dashboard directly importing collectors
- ❌ Models importing from utils (should be injected)

### Architecture Decision Records

Create `docs/adr/` with:

1. **ADR-001: Application Factory Pattern**
   - Why: Better testability, configuration flexibility
   - When: Week 11 (2026-02)
   - Impact: All blueprints updated

2. **ADR-002: Two-Tier Caching Strategy**
   - Why: Performance (memory) + persistence (disk)
   - When: Week 8 (2026-01)
   - Impact: CacheService enhanced

3. **ADR-003: Clean Architecture Layers**
   - Why: Long-term maintainability
   - When: Week 12 (2026-02)
   - Impact: All new code follows layers

4. **ADR-004: Time Offset Applied to Both Collectors**
   - Why: DORA metrics alignment in UAT
   - When: 2026-01-26
   - Impact: Both collectors query same time window

### Implementation Steps

1. **Phase 3.1: Document Architecture** (~2 hours)
   - Create architecture diagram
   - Document layers and rules
   - Create ADR template

2. **Phase 3.2: Create ADRs** (~2 hours)
   - Write ADR-001 through ADR-004
   - Document existing decisions
   - Establish ADR process

3. **Phase 3.3: Fix Violations** (~4 hours)
   - Remove presentation→infrastructure imports
   - Inject utilities into domain models
   - Update imports throughout codebase

4. **Phase 3.4: Add Linting** (~2 hours)
   - Add import linter (e.g., `import-linter`)
   - Configure layer rules
   - Add to CI pipeline

**Total Effort: ~10 hours**

### Benefits
- ✅ Clear boundaries
- ✅ Easier onboarding
- ✅ Documented decisions
- ✅ Enforced via linting

---

## Summary

### Total Effort Estimate

| Phase | Description | Effort | Priority |
|-------|-------------|--------|----------|
| Phase 1 | CacheService Enhancement | 8-10 hours | High |
| Phase 2 | Application Factory Pattern | 8 hours | Medium |
| Phase 3 | Clean Architecture Foundation | 10 hours | Low |

**Total: ~26-28 hours (~3-4 full days)**

### Order of Implementation

**Recommended:**
1. Phase 1 (CacheService) - Immediate performance benefit
2. Phase 2 (Factory Pattern) - Enables better testing
3. Phase 3 (Architecture) - Long-term maintainability

**Alternative (Architecture-First):**
1. Phase 3 (Architecture) - Establish foundation
2. Phase 2 (Factory Pattern) - Fits into architecture
3. Phase 1 (CacheService) - Implements within pattern

### Quick Wins (Can Be Done Separately)

1. **Add `/api/cache/stats` endpoint** (~30 min)
   - Show current cache statistics
   - Useful for monitoring

2. **Add cache warming on startup** (~1 hour)
   - Pre-load 90d prod cache
   - Faster first page load

3. **Create ADR-004 for time offset** (~30 min)
   - Document recent decision
   - Start ADR practice

---

## Next Steps

**Immediate:**
1. ✅ Validation added (time_offset_days)
2. ✅ UAT collection started in background
3. 🔲 Choose phase to start with

**Recommended Starting Point:**
Start with **Phase 1 (CacheService)** because:
- Immediate performance benefit
- Self-contained (no major refactoring)
- Provides foundation for Phase 2

**Question for Discussion:**
Which phase would you like to start with, or should we continue with quick wins first?
