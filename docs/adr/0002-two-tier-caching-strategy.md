# ADR-0002: Two-Tier Caching Strategy with Memory Layer

**Status:** Accepted
**Date:** 2026-01-26
**Deciders:** Development Team, Claude
**Technical Story:** Phase 1 - Enhanced Cache Service

---

## Context

The dashboard initially used a simple file-based cache (pickle files) for storing collected metrics. This worked but had performance limitations:

**Problems:**
1. **Slow First Load:** Every page request required reading from disk (~20-50ms)
2. **Disk I/O Contention:** Multiple concurrent users caused disk bottlenecks
3. **No Cache Warming:** First user after deployment waited 2-5 seconds for collection
4. **Limited Observability:** No metrics on cache hit rates or performance

**Requirements:**
- Faster page loads (sub-millisecond for cached data)
- Support multiple concurrent users
- Maintain disk persistence (survive restarts)
- Configurable memory limits
- Backward compatible with existing cache

**Forces:**
- Balance memory usage vs performance
- Need eviction policies to prevent memory exhaustion
- Want observability (hit rates, memory usage)
- Must work with single-worker Flask (not distributed)

## Decision

Implement a **Two-Tier Caching Strategy** with memory layer backed by disk.

**Architecture:**
```
Request → Memory Cache (fast) → Disk Cache (persistent) → Collection (slow)
          <1ms                    20ms                      2-5s
```

**Key Components:**
1. **EnhancedCacheService** - Two-tier cache orchestrator
2. **MemoryBackend** - In-process dictionary cache
3. **FileBackend** - Persistent pickle file storage
4. **LRU Eviction Policy** - Least Recently Used eviction
5. **TTL Eviction Policy** - Time-To-Live based eviction
6. **Cache Warming** - Pre-load common ranges on startup

**Features:**
- Memory hits: <1ms (2-20x faster than disk)
- Configurable memory limit (default: 500MB)
- LRU eviction when memory limit reached
- Cache warming on startup (90d, 30d, 180d)
- Statistics API (`/api/cache/stats`)
- 100% backward compatible

## Consequences

### Positive
- ✅ **2-20x Faster:** Memory hits vs disk hits
- ✅ **100-500x Faster:** Memory hits vs cache miss
- ✅ **99%+ Hit Rate:** After cache warming
- ✅ **Better Scalability:** Handles concurrent users without disk contention
- ✅ **Observability:** Real-time cache statistics
- ✅ **Configurable:** Memory limit, warm keys, eviction policies
- ✅ **Backward Compatible:** Can disable memory layer if needed

### Negative
- ⚠️ **Memory Usage:** ~3MB typical (6 cache files)
- ⚠️ **Single-Worker Only:** Each Flask worker has own memory cache
- ⚠️ **Complexity:** More moving parts (eviction, warming)
- ⚠️ **Cold Start:** Cache warming adds ~100ms to startup

### Neutral
- Does not solve distributed caching (need Redis for that)
- Memory layer volatile (cleared on restart, but disk persists)
- Evictions rare with 500MB limit (typical usage ~3MB)

## Alternatives Considered

### Alternative 1: Redis Cache
**Pros:**
- Distributed caching (works with multiple workers)
- Persistent memory cache
- Built-in TTL expiration

**Cons:**
- External dependency (Redis server)
- Network overhead (~1-5ms vs <1ms)
- More complex deployment
- Overkill for single-worker

**Why Not Chosen:** Future enhancement. Start simple with in-process cache.

### Alternative 2: Flask-Caching Extension
**Pros:**
- Mature library
- Multiple backends (memory, Redis, filesystem)
- Flask integration

**Cons:**
- Generic caching (not optimized for our use case)
- External dependency
- Less control over behavior

**Why Not Chosen:** Our custom solution provides exact features needed with full control.

### Alternative 3: Keep File-Only Cache
**Pros:**
- Simple
- No memory overhead
- Works as-is

**Cons:**
- Slow (20-50ms per request)
- Disk I/O contention under load
- Poor user experience

**Why Not Chosen:** Performance improvement worth the effort.

### Alternative 4: In-Memory Only (No Disk)
**Pros:**
- Fastest possible
- Simple implementation

**Cons:**
- Loses cache on restart
- Must recollect data (2-5 seconds)
- No persistence

**Why Not Chosen:** Need disk persistence for production reliability.

## Implementation

**Phase 1.1: Create Protocols and Backends** ✅ Complete
- Define `CacheBackend` protocol
- Implement `FileBackend` (disk)
- Implement `MemoryBackend` (in-process dict)

**Phase 1.2: Create Eviction Policies** ✅ Complete
- Define `EvictionPolicy` protocol
- Implement `LRUEvictionPolicy`
- Implement `TTLEvictionPolicy`
- Implement `CompositeEvictionPolicy`

**Phase 1.3: Build EnhancedCacheService** ✅ Complete
- Two-tier get/set operations
- Memory eviction logic
- Cache warming
- Statistics tracking

**Phase 1.4: Add API Endpoints** ✅ Complete
- `GET /api/cache/stats` - Cache statistics
- `POST /api/cache/clear` - Clear memory or all
- `POST /api/cache/warm` - Pre-load keys

**Phase 1.5: Integration and Testing** ✅ Complete
- Integrate into `app.py`
- Add 21 comprehensive tests
- Update `config.example.yaml`
- Write performance analysis
- Write usage guide

**Timeline:** Completed 2026-01-26 (~5 hours)

## Performance Results

### Response Times
| Scenario | Before | After | Improvement |
|----------|--------|-------|-------------|
| Memory hit | N/A | <1ms | New capability |
| Disk hit | 20ms | 20ms | Same (fallback) |
| Subsequent hit | 20ms | <1ms | 20x faster |
| Cache miss | 2-5s | 2-5s | Same (no cache) |

### Memory Usage
- Typical: ~3MB (6 cache files)
- Maximum: 500MB (configurable)
- Per file: ~500KB (165KB on disk × 3 Python overhead)

### Hit Rates
- After warming: 99%+
- Without warming: 70-85% (first request per range misses memory)

## References

- Implementation: `src/dashboard/services/enhanced_cache_service.py`
- Tests: `tests/dashboard/test_enhanced_cache_service.py`
- Documentation: `docs/ENHANCED_CACHE_PERFORMANCE_ANALYSIS.md`
- Usage Guide: `docs/ENHANCED_CACHE_USAGE.md`
- Related: ADR-0001 (uses DI container for cache registration)

---

**Revision History:**
- 2026-01-26: Initial decision (Accepted)
