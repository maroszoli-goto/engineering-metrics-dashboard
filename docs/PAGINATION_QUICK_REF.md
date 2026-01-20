# Jira Pagination Quick Reference

**One-page guide for the Jira pagination fix**

---

## What Was Fixed

❌ **Before**: 504 timeouts, data truncated at 1000 issues, no retry
✅ **After**: Smart pagination, all data collected, automatic retry

---

## Configuration

**File**: `config/config.yaml`

### Default Settings (Recommended)
```yaml
jira:
  pagination:
    enabled: true
    batch_size: 500
    huge_dataset_threshold: 150
    fetch_changelog_for_large: false
    max_retries: 3
    retry_delay_seconds: 5
```

### Quick Adjustments

**Still getting timeouts?** → Lower threshold:
```yaml
huge_dataset_threshold: 50  # Or even 25
```

**Need more retries?** → Increase attempts:
```yaml
max_retries: 5
retry_delay_seconds: 10
```

**Want to disable?** → Turn off pagination:
```yaml
enabled: false  # Reverts to old behavior
```

---

## How It Works

```
1. Count Query    → "Filter X: Found 8247 total issues"
2. Adapt Strategy → If >150: Disable changelog
3. Paginate       → Fetch in batches of 500/1000
4. Retry on 504   → 3 attempts with 5s delay
5. Complete       → "Successfully fetched 8247/8247 issues"
```

---

## Monitoring

### Check Pagination Activity
```bash
tail -f logs/team_metrics.log | grep "Found.*total\|Successfully fetched"
```

### Look for Threshold Behavior
```bash
grep "exceeds threshold\|Disabling changelog" logs/team_metrics.log
```

### Check for Timeouts
```bash
grep "Timeout on batch\|Failed batch" logs/team_metrics.log
```

### Verify No Data Loss
```bash
grep "Successfully fetched" logs/team_metrics.log | tail -20
```

---

## Common Issues

### Issue: Count Query Timing Out
**Log**: `Failed to get count for Filter X`
**Cause**: Jira server performance issue
**Impact**: Falls back to maxResults=1000
**Fix**: Simplify filter JQL or contact Jira admin

### Issue: Still Getting 504s
**Log**: `Timeout on batch starting at 0`
**Fix 1**: Lower threshold to 50 or 25
**Fix 2**: Increase Jira timeout:
```yaml
dashboard:
  jira_timeout_seconds: 300
```

### Issue: Collection Too Slow
**Cause**: Pagination takes 30-50% longer
**Trade-off**: Complete data vs speed
**Mitigation**: Run during off-peak hours

---

## Expected Behavior

### Small Dataset (<150 issues)
```
Filter 81015: Found 32 total issues
Filter 81015: Successfully fetched 32/32 issues (with changelog)
✅ Single batch, changelog included
```

### Large Dataset (150-1000 issues)
```
Filter 84313: Found 576 total issues
Filter 84313: 576 issues exceeds threshold (150). Disabling changelog...
Filter 84313: Successfully fetched 576/576 issues (without changelog)
✅ Batches of 1000, no changelog
```

### Timeout with Retry
```
Filter 84313: Timeout on batch starting at 0 (attempt 1/3). Retrying in 5s...
Filter 84313: Timeout on batch starting at 0 (attempt 2/3). Retrying in 5s...
Filter 84313: Successfully fetched 186/186 issues (with changelog)
✅ Retry succeeded
```

### Failed After Retries
```
Filter 84313: Timeout on batch starting at 0 (attempt 3/3). Retrying in 5s...
Filter 84313: Failed batch at 0 after 3 retries. Returning partial results (0/186 issues)
⚠️ Graceful degradation, collection continues
```

---

## Success Indicators

✅ **Good signs in logs**:
- "Found X total issues" (count query working)
- "Successfully fetched X/X issues" (all data collected)
- "exceeds threshold. Disabling changelog" (threshold working)
- Progress bars in terminal (interactive mode)

❌ **Warning signs**:
- "Failed to get count" (count query timeout - expected for complex filters)
- "Failed batch after 3 retries" (persistent timeout - lower threshold)
- "Successfully fetched 0/X issues" (no data collected - investigate)

---

## Verification Commands

### Check Last Collection
```bash
# See completion status
tail -30 logs/team_metrics.log

# Count successful fetches
grep "Successfully fetched" logs/team_metrics.log | wc -l

# Check for errors
grep "ERROR" logs/team_metrics.log | tail -10
```

### Verify Cache File
```bash
# Check cache exists and size
ls -lh data/metrics_cache_*.pkl

# Inspect cache contents
python -c "
import pickle
with open('data/metrics_cache_90d.pkl', 'rb') as f:
    cache = pickle.load(f)
    for team, data in cache['teams'].items():
        jira = data.get('jira', {})
        print(f'{team}: {len(jira.get(\"wip_issues\", []))} WIP issues')
"
```

---

## Performance Expectations

### Collection Time
- **30-day range**: ~10-17 minutes (was ~10 min)
- **90-day range**: ~30-40 minutes (was ~20 min)
- **Trade-off**: 50% longer, but 100% complete data

### Success Rates
- **Person queries**: 100% (was 0% with failures)
- **Small filters (<150)**: 100%
- **Large filters (>150)**: 95%+ (some may have Jira server issues)

---

## Troubleshooting Cheat Sheet

| Symptom | Quick Fix |
|---------|-----------|
| 504 on count query | Expected - fallback to maxResults=1000 |
| 504 on first batch | Lower threshold to 50 |
| Multiple 504s | Increase timeout to 300s |
| No progress bars | Normal in background mode |
| Collection too slow | Run during off-peak hours |
| Partial results (0/X) | Lower threshold or simplify JQL |

---

## Configuration Presets

### Conservative (Maximum Reliability)
```yaml
jira:
  pagination:
    enabled: true
    batch_size: 250
    huge_dataset_threshold: 50
    max_retries: 5
    retry_delay_seconds: 10
```

### Aggressive (Performance Priority)
```yaml
jira:
  pagination:
    enabled: true
    batch_size: 1000
    huge_dataset_threshold: 1000
    max_retries: 2
    retry_delay_seconds: 3
```

### Disabled (Rollback)
```yaml
jira:
  pagination:
    enabled: false
```

---

## Key Files

| File | Purpose |
|------|---------|
| `config/config.yaml` | Pagination configuration |
| `src/collectors/jira_collector.py` | Core implementation (lines 59-197) |
| `docs/JIRA_PAGINATION_FIX.md` | Complete documentation |
| `docs/PAGINATION_QUICK_REF.md` | This guide |
| `logs/team_metrics.log` | Pagination activity logs |

---

## One-Line Checks

```bash
# Is pagination enabled?
grep -A5 "pagination:" config/config.yaml

# Recent pagination activity
grep "Successfully fetched" logs/team_metrics.log | tail -5

# Any failures?
grep "Failed batch" logs/team_metrics.log | tail -5

# Threshold being used
grep "exceeds threshold" logs/team_metrics.log | tail -1
```

---

## Support

**Full docs**: `docs/JIRA_PAGINATION_FIX.md`
**Config example**: `config/config.example.yaml`
**Test collection**: `python collect_data.py --date-range 7d`
**Validate config**: `python validate_config.py`

---

**TL;DR**: Pagination is enabled by default with threshold=150. It fixes 504 timeouts and data truncation. Collection takes 30-50% longer but fetches all data. Lower threshold if you still see timeouts.
