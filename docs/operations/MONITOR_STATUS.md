# Data Collection Monitoring Status

**Last Updated**: January 20, 2026 at 10:19 AM CET

---

## Current Collection Status

### Service Status
```
Service: com.team-metrics.collect
Status: RUNNING ✅
PID: 57757 (bash), 57760 (python)
Started: 10:00 AM today
Runtime: ~20 minutes
```

### Progress
- **Current Range**: 60-day data (2/6 completed)
- **Completed**: 30d
- **Remaining**: 60d, 90d, 180d, 365d, 2025

### Known Issues
⚠️ **Data Validation Failures**: GitHub data collection failing, causing validation errors
⚠️ **Jira 504 Timeouts**: Multiple Jira filters timing out (expected, non-critical)
⚠️ **Slow Performance**: Taking 20+ minutes (expected: 2-4 minutes)

---

## Real-Time Monitoring Commands

### 1. Watch Live Progress
```bash
# Follow the logs with live updates
tail -f logs/collect_data.log

# Watch for completion message
tail -f logs/collect_data.log | grep -E "(📊|✅ Collection complete)"
```

### 2. Check Process Status
```bash
# Check if collection is still running
ps -p 57760 -o pid,etime,command

# Check service status
launchctl list | grep team-metrics
```

### 3. View Recent Errors
```bash
# Check error log
tail -50 logs/team_metrics_error.log

# Count recent 504 timeouts
grep "504 Gateway Time-out" logs/team_metrics_error.log | tail -50 | wc -l
```

### 4. Monitor Cache File Updates
```bash
# Watch for cache file changes
watch -n 5 'ls -lht data/metrics_cache_*.pkl | head -6'
```

---

## Expected Behavior

### Normal Collection
- **Duration**: 2-4 minutes for all 6 ranges
- **Cache Files Updated**: All 6 files get today's timestamp
- **Exit Message**: "✅ Collection complete (6 ranges)"
- **Exit Code**: 0

### Current Abnormal Behavior
- **Duration**: 20+ minutes and counting
- **Validation Errors**: "❌ CRITICAL: No GitHub data collected at all!"
- **Cache Prevention**: "❌ Data validation failed - NOT caching to prevent data loss!"
- **Status**: Previous caches remain intact (good - prevents data loss)

---

## Investigation Needed

### Primary Issue: GitHub Data Collection Failure
The collection shows critical validation errors indicating no GitHub data is being collected. This could be due to:

1. **GitHub API Issues**
   - Rate limiting
   - Token expiration
   - Network connectivity

2. **GraphQL Query Problems**
   - Query syntax errors
   - Timeout issues
   - Response parsing failures

3. **Code Issues**
   - Recent code changes
   - Configuration problems

### Recommended Actions

1. **Check GitHub Token**
   ```bash
   # Test GitHub API connectivity
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/rate_limit
   ```

2. **Review Error Details**
   ```bash
   # Find GitHub-specific errors
   grep -i "github" logs/team_metrics_error.log | tail -50

   # Look for GraphQL errors
   grep -i "graphql" logs/collect_data.log | tail -20
   ```

3. **Consider Stopping Current Collection**
   ```bash
   # Stop the hung collection
   pkill -f "collect_data.py"

   # Or stop via launchctl
   launchctl stop com.team-metrics.collect
   ```

4. **Test Manual Collection**
   ```bash
   # Try collecting just 30d to debug
   source venv/bin/activate
   python collect_data.py --date-range 30d -v
   ```

---

## Dashboard Status

**Service**: `com.team-metrics.dashboard`
- **Status**: Running but with exit code 1 (warning)
- **PID**: 52955
- **URL**: http://localhost:5001
- **Cache**: Using yesterday's data (Jan 19)

**Impact**: Dashboard is functional but showing stale data until collection completes successfully.

---

## Cache File Status

```
Current cache files (as of Jan 20, 10:15 AM):

-rw-r--r--  1 zmaros  staff    93K Jan 20 09:15 data/metrics_cache_30d.pkl
-rw-r--r--  1 zmaros  staff   403K Jan 19 20:19 data/metrics_cache_90d.pkl
-rw-r--r--  1 zmaros  staff   536K Jan 19 11:41 data/metrics_cache_2025.pkl
-rw-r--r--  1 zmaros  staff   614K Jan 19 11:07 data/metrics_cache_365d.pkl
-rw-r--r--  1 zmaros  staff   633K Jan 19 10:33 data/metrics_cache_180d.pkl
-rw-r--r--  1 zmaros  staff   279K Jan 19 10:13 data/metrics_cache_60d.pkl
```

**Note**: Only `metrics_cache_30d.pkl` was updated today (09:15 AM), but that was from a previous collection attempt. Most caches are from Jan 19.

---

## Next Steps

### Option 1: Wait and Monitor (Recommended)
Continue monitoring to see if the collection eventually completes or fails cleanly.

```bash
# Monitor in real-time
tail -f logs/collect_data.log
```

### Option 2: Stop and Debug
Stop the current collection and investigate the GitHub data collection issue.

```bash
# Stop collection
launchctl stop com.team-metrics.collect

# Review logs
grep "CRITICAL" logs/collect_data.log

# Test GitHub connectivity
python -c "from src.collectors.github_graphql_collector import GitHubGraphQLCollector; print('Import OK')"
```

### Option 3: Manual Collection with Debugging
Run collection manually with verbose logging to identify the issue.

```bash
# Activate environment
source venv/bin/activate

# Run with verbose logging
python collect_data.py --date-range 30d -v 2>&1 | tee debug_collection.log
```

---

## Historical Context

### Previous Successful Collections
- **Last Full Success**: January 19, 2026 (multiple successful runs)
- **Success Indicators**: "✅ Collection complete (6 ranges)" message
- **Typical Duration**: 2-4 minutes for all ranges

### Known Issue: Jira 504 Timeouts
- **Status**: Expected and handled gracefully
- **Count**: 281 timeouts in error log (historical)
- **Impact**: Partial data returned, not critical
- **Filters Affected**: Native Team (80910, 81010, 84312) and WebTC Team (81024, 84313)

---

## Troubleshooting Reference

### If Collection Hangs
```bash
# Check process
ps -p 57760

# Check connections
lsof -p 57760 | grep ESTABLISHED

# Stop if needed
pkill -f collect_data.py
```

### If Validation Fails
```bash
# Check validation errors
grep "Data validation failed" logs/collect_data.log

# Review what data was collected
grep "members have no GitHub data" logs/collect_data.log
```

### If Cache Not Updating
```bash
# Verify collection completed
grep "Collection complete" logs/collect_data.log | tail -1

# Check for validation failures preventing caching
grep "NOT caching" logs/collect_data.log
```

---

## Configuration Reference

### Parallel Collection Settings
Location: `config/config.yaml`

```yaml
parallel_collection:
  enabled: true
  person_workers: 8
  team_workers: 3
  repo_workers: 5
  filter_workers: 4
```

**If issues persist**, consider reducing workers:
```yaml
parallel_collection:
  enabled: true
  person_workers: 4    # Reduced from 8
  team_workers: 2      # Reduced from 3
  repo_workers: 3      # Reduced from 5
  filter_workers: 2    # Reduced from 4
```

---

## Contact & Resources

- **Verification Tool**: `./tools/verify_collection.sh`
- **Analysis Tool**: `python tools/analyze_releases.py`
- **Main Docs**: `CLAUDE.md`
- **Collection Guide**: `docs/COLLECTION_CHANGES.md`
- **Pagination Fix**: `docs/JIRA_PAGINATION_FIX.md`
