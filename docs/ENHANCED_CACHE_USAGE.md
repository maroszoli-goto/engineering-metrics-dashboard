# Enhanced Cache Service - Usage Guide

## Quick Start

The enhanced cache service is **enabled by default** with sensible defaults. No configuration changes required!

### Default Behavior

```yaml
# These are the defaults (no config needed)
dashboard:
  cache:
    max_memory_mb: 500          # 500MB memory cache
    enable_memory_cache: true   # Memory layer enabled
    warm_on_startup: true       # Pre-load common ranges
    warm_keys:
      - "90d_prod"
      - "30d_prod"
      - "180d_prod"
```

**What This Means:**
- Dashboard starts in ~100ms (warms 3 cache files)
- First page load: **Instant** (pre-loaded in memory)
- All subsequent loads: **Instant** (memory cache)
- Memory usage: ~3MB typical

---

## Configuration

### Basic Configuration

Add to `config/config.yaml`:

```yaml
dashboard:
  cache:
    max_memory_mb: 500          # Maximum memory for cache
    enable_memory_cache: true   # Enable memory layer
    warm_on_startup: true       # Pre-load on start
```

### Advanced Configuration

```yaml
dashboard:
  cache:
    # Memory Settings
    max_memory_mb: 1000          # 1GB memory cache
    enable_memory_cache: true    # Enable memory layer

    # Startup Warming
    warm_on_startup: true        # Pre-load on start
    warm_keys:                   # Keys to pre-load
      - "90d_prod"
      - "30d_prod"
      - "60d_prod"
      - "180d_prod"
      - "365d_prod"
      - "90d_uat"                # Multi-environment support
```

### Disable Memory Cache

For low-memory environments:

```yaml
dashboard:
  cache:
    max_memory_mb: 0             # No memory limit (unused when disabled)
    enable_memory_cache: false   # Disable memory layer
    warm_on_startup: false       # Don't pre-load
```

**Effect:** Uses only disk cache (same as legacy behavior)

---

## API Endpoints

### Get Cache Statistics

```bash
GET /api/cache/stats
```

**Response:**
```json
{
  "status": "ok",
  "stats": {
    "memory_hits": 150,
    "disk_hits": 25,
    "misses": 5,
    "hit_rate": 0.972,           // 97.2% overall
    "memory_hit_rate": 0.833,    // 83.3% from memory
    "evictions": 3,
    "sets": 180,
    "memory_entries": 5,
    "memory_size_mb": 45.2,
    "max_memory_mb": 500.0,
    "memory_utilization": 0.090  // 9% of max
  }
}
```

**Metrics Explained:**
- `hit_rate`: Percentage of requests served from cache (memory + disk)
- `memory_hit_rate`: Percentage of requests served from memory only
- `evictions`: Number of entries removed from memory (due to size limit)
- `memory_utilization`: Percentage of max_memory_mb currently used

### Clear Cache

```bash
# Clear memory only (disk remains)
POST /api/cache/clear?type=memory

# Clear everything (memory + disk)
POST /api/cache/clear?type=all
```

**Use Cases:**
- `type=memory`: Force reload from disk (free up RAM)
- `type=all`: Force fresh collection on next request

### Warm Cache

```bash
POST /api/cache/warm
Content-Type: application/json

{
  "keys": ["90d_prod", "30d_prod", "180d_prod"]
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Cache warmed with 3 keys"
}
```

**Use Case:** Pre-load cache after collection completes

---

## Common Workflows

### Workflow 1: Daily Data Collection

```bash
# 1. Collect fresh data
python collect_data.py --date-range 90d --env prod

# 2. Warm cache (optional - dashboard does this on startup)
curl -X POST http://localhost:5001/api/cache/warm \
  -H "Content-Type: application/json" \
  -d '{"keys": ["90d_prod"]}'

# 3. Dashboard automatically uses new cache
```

**Note:** Dashboard automatically picks up new cache files on next request.

### Workflow 2: Multi-Environment Testing

```bash
# 1. Collect UAT data
python collect_data.py --date-range 90d --env uat

# 2. View UAT in dashboard
open http://localhost:5001/?env=uat&range=90d

# 3. Switch to production
open http://localhost:5001/?env=prod&range=90d
```

**Note:** Each environment uses separate cache files (`90d_uat` vs `90d_prod`).

### Workflow 3: Performance Monitoring

```bash
# 1. Check cache stats
curl http://localhost:5001/api/cache/stats

# 2. Monitor hit rate
watch -n 5 'curl -s http://localhost:5001/api/cache/stats | jq ".stats.hit_rate"'

# 3. If hit rate < 90%, investigate:
#    - Check warm_keys includes ranges you use
#    - Check max_memory_mb is sufficient
#    - Check for frequent cache clears
```

### Workflow 4: Troubleshooting Slow Pages

```bash
# 1. Check if cache is being used
curl http://localhost:5001/api/cache/stats

# 2. If misses are high, warm cache
curl -X POST http://localhost:5001/api/cache/warm \
  -d '{"keys": ["90d_prod", "30d_prod"]}'

# 3. If memory_utilization > 90%, increase limit
# Edit config.yaml:
#   max_memory_mb: 1000  # Increase from 500

# 4. Restart dashboard
```

---

## Monitoring

### Key Metrics to Track

| Metric | Target | Action if Outside Target |
|--------|--------|--------------------------|
| `hit_rate` | >90% | Enable cache warming |
| `memory_hit_rate` | >80% | Increase max_memory_mb |
| `memory_utilization` | 40-80% | Adjust max_memory_mb |
| `evictions` | <10/hour | Increase max_memory_mb |

### Dashboard Integration

Add cache monitoring to your dashboard:

```python
# In a dashboard route:
@dashboard_bp.route("/admin")
@require_auth
def admin():
    cache_service = get_cache_service()
    stats = cache_service.get_stats()

    return render_template("admin.html", cache_stats=stats)
```

```html
<!-- In admin.html template: -->
<div class="cache-stats">
  <h3>Cache Performance</h3>
  <p>Hit Rate: {{ "%.1f"|format(cache_stats.hit_rate * 100) }}%</p>
  <p>Memory: {{ "%.1f"|format(cache_stats.memory_size_mb) }} /
     {{ "%.0f"|format(cache_stats.max_memory_mb) }} MB</p>
  <p>Entries: {{ cache_stats.memory_entries }}</p>
</div>
```

---

## Best Practices

### 1. Cache Warming

**DO:** Pre-load ranges you actually use
```yaml
warm_keys:
  - "90d_prod"    # Default range
  - "30d_prod"    # Quick updates
```

**DON'T:** Pre-load every possible range
```yaml
warm_keys:
  - "30d_prod"
  - "60d_prod"
  - "90d_prod"
  - "180d_prod"
  - "365d_prod"
  - "Q1-2025"
  - "Q2-2025"    # Probably never used
  - "Q3-2025"
  - "Q4-2025"
```

### 2. Memory Sizing

**DO:** Size based on concurrent users
- 1-5 users: 100-200 MB
- 5-20 users: 500 MB (default)
- 20+ users: 1-2 GB

**DON'T:** Set unlimited memory
```yaml
max_memory_mb: 100000  # 100GB - BAD! Will consume all RAM
```

### 3. Environment Separation

**DO:** Use separate cache files per environment
```bash
python collect_data.py --env prod   # Creates *_prod.pkl
python collect_data.py --env uat    # Creates *_uat.pkl
```

**DON'T:** Mix environments in same cache
```bash
# This would overwrite prod with uat data - DON'T DO THIS
python collect_data.py --env uat > data/metrics_cache_90d_prod.pkl
```

### 4. Cache Invalidation

**DO:** Let automatic TTL handle refreshes
```yaml
dashboard:
  cache_duration_minutes: 60  # Auto-refresh after 1 hour
```

**DON'T:** Manually clear cache frequently
```bash
# This defeats the purpose of caching - DON'T DO THIS
while true; do
  curl -X POST http://localhost:5001/api/cache/clear?type=all
  sleep 60
done
```

---

## Troubleshooting

### Problem: High Memory Usage

**Symptoms:**
- Server using >2GB RAM
- Out of memory errors

**Solution 1: Check Cache Size**
```bash
curl http://localhost:5001/api/cache/stats
# Check: memory_size_mb, memory_entries
```

**Solution 2: Reduce max_memory_mb**
```yaml
dashboard:
  cache:
    max_memory_mb: 200  # Reduce from 500
```

**Solution 3: Clear Memory Cache**
```bash
curl -X POST http://localhost:5001/api/cache/clear?type=memory
```

### Problem: Slow Page Loads

**Symptoms:**
- Pages take 2-5 seconds to load
- Inconsistent response times

**Solution 1: Check Hit Rate**
```bash
curl http://localhost:5001/api/cache/stats | jq '.stats.hit_rate'
# Should be > 0.90 (90%)
```

**Solution 2: Enable Cache Warming**
```yaml
dashboard:
  cache:
    warm_on_startup: true
    warm_keys: ["90d_prod", "30d_prod"]
```

**Solution 3: Check Logs**
```bash
tail -f logs/team_metrics.log | grep cache
# Look for "Cache miss" messages
```

### Problem: Stale Data

**Symptoms:**
- Dashboard shows old metrics
- Recent changes not reflected

**Solution: Clear Cache**
```bash
# Clear all caches (force fresh load)
curl -X POST http://localhost:5001/api/cache/clear?type=all

# Or restart dashboard (reloads from disk)
# macOS launchd:
launchctl stop com.team-metrics.dashboard
launchctl start com.team-metrics.dashboard
```

### Problem: Cache Warming Slows Startup

**Symptoms:**
- Dashboard takes 5-10 seconds to start
- Timeout on first request

**Solution: Reduce Warm Keys**
```yaml
dashboard:
  cache:
    warm_on_startup: true
    warm_keys:
      - "90d_prod"  # Only the default range
```

---

## Migration from Legacy Cache

### Backward Compatibility

The enhanced cache service is **100% backward compatible**. No code changes needed!

**What Works:**
- Existing `cache_service.load_cache(range, env)` calls
- Existing `cache_service.should_refresh(cache, ttl)` calls
- Existing cache file format (pickle)
- All existing templates and routes

**What's New:**
- Memory layer (transparent to existing code)
- Cache warming on startup
- Statistics tracking
- New API endpoints

### Migration Steps

1. **Update config (optional):**
   ```yaml
   dashboard:
     cache:
       max_memory_mb: 500
       enable_memory_cache: true
   ```

2. **Restart dashboard:**
   ```bash
   # macOS:
   launchctl restart com.team-metrics.dashboard

   # Manual:
   python -m src.dashboard.app
   ```

3. **Verify:**
   ```bash
   curl http://localhost:5001/api/cache/stats
   # Should show enhanced cache stats
   ```

**Rollback (if needed):**
```yaml
dashboard:
  cache:
    enable_memory_cache: false  # Disable enhanced features
```

---

## Performance Expectations

### Expected Response Times

| Scenario | Response Time | Notes |
|----------|---------------|-------|
| Memory cache hit | <15ms | Memory lookup + template render |
| Disk cache hit | 30-50ms | File I/O + memory warm + render |
| Cache miss | 2-5s | Full GitHub/Jira collection |

### Expected Hit Rates

| Scenario | Hit Rate | Notes |
|----------|----------|-------|
| After warming | 95-99% | Most requests hit memory |
| No warming | 70-85% | First request per range misses memory |
| Infrequent use | 50-70% | Cache may be cold |

### Expected Memory Usage

| Configuration | Memory Used | Notes |
|---------------|-------------|-------|
| Minimal (1-2 ranges) | 1-2 MB | Development |
| Typical (3-4 ranges) | 2-4 MB | Small team |
| Large (6+ ranges) | 5-10 MB | Multi-environment |

---

## FAQ

### Q: Does cache warming slow down startup?

**A:** Slightly (~50-200ms), but first page load is instant instead of 2-5 seconds.

### Q: What happens if memory limit is exceeded?

**A:** LRU eviction policy removes least recently used entries automatically.

### Q: Can I use Redis instead of files?

**A:** Not yet. Redis backend is planned for Phase 2+ (see `ARCHITECTURE_ROADMAP.md`).

### Q: Will this work with multiple Flask workers?

**A:** Partially. Each worker has its own memory cache, but shares disk cache. For full multi-worker support, use Redis backend (future).

### Q: How do I monitor cache performance?

**A:** Use `GET /api/cache/stats` endpoint. Monitor `hit_rate` and `memory_utilization`.

### Q: Can I disable the memory cache?

**A:** Yes! Set `enable_memory_cache: false` in config. Falls back to disk-only (legacy behavior).

### Q: What's the performance improvement?

**A:** 2-20x faster page loads (memory vs disk), 100-500x faster than cache miss.

### Q: How much memory should I allocate?

**A:** Default 500MB is good for most installations. Increase if you have many concurrent users or many date ranges/environments.

---

## Related Documentation

- `ENHANCED_CACHE_PERFORMANCE_ANALYSIS.md` - Performance benchmarks
- `ARCHITECTURE_ROADMAP.md` - Future enhancements
- `config/config.example.yaml` - Configuration reference
- `CLAUDE.md` - Overall project documentation
