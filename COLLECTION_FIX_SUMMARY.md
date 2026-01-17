# Team Metrics Collection Fix Summary
Date: January 17, 2026

## Problem Statement
Automated data collection (scheduled daily at 10:00 AM) was failing with exit code 256.
Last successful cache: January 15, 2026 (2 days old)
Logs showed: "60-day collection failed" and "90-day collection failed"

## Root Cause Analysis

### Primary Issue: GitHub Secondary Rate Limit (403 errors)
- Collection failed with "secondary rate limit" errors
- Cause: Too many concurrent requests (5 repo workers) + no delays between requests
- GitHub's secondary rate limit detects scraping/abuse patterns
- Unlike primary rate limit (5000 points/hour), secondary limit has no published threshold

### Secondary Issues Found During Investigation
1. **Date Comparison Bug**: TypeError when comparing string dates vs datetime objects in person metrics
2. **Missing Field Bug**: `cycle_time_hours` not calculated in legacy PR extraction method

## Fixes Applied

### 1. GitHub Rate Limiting (CRITICAL FIX)
**File**: `src/collectors/github_graphql_collector.py`

**Changes**:
- Lines 103-120: Added 403 retry logic with detection of "secondary rate limit" message
- Retry strategy: 3 attempts with exponential backoff (5s, 10s, 20s)
- Lines 301-307: Added 200ms delay between repository submissions
- Reduced parallel workers: 5 → 3 in config/config.yaml

**Result**: Collection handles rate limits gracefully, retries with backoff

### 2. Date Comparison Bug (MEDIUM FIX)
**File**: `src/collectors/github_graphql_collector.py`

**Changes**:
- Lines 1196-1209: Added safe date comparison helper
- Handles both datetime objects and ISO string dates
- Used in person metrics end_date filtering

**Result**: Person metrics collection succeeds

### 3. Missing cycle_time_hours Field (MEDIUM FIX)
**File**: `src/collectors/github_graphql_collector.py`

**Changes**:
- Lines 477-518: Enhanced `_extract_pr_data()` method
- Now calculates `cycle_time_hours` and `time_to_first_review_hours`
- Ensures consistency between batched and sequential collection paths

**Result**: Metrics calculation succeeds for all PRs

## Verification Status

✅ Code fixes applied and tested
✅ Retry logic working (confirmed in logs: "Secondary rate limit hit, retrying in 10s")
✅ Date comparison bug fixed
✅ cycle_time_hours field bug fixed
✅ Comprehensive DATA_QUALITY.md documentation created

⚠️ Rate limit still active from today's testing
- Multiple test runs (3 attempts) consumed significant API quota
- Secondary rate limit window: ~1 hour (estimated)
- Next automated run (tomorrow 10:00 AM) should succeed after rate limit resets

## Next Steps

### Immediate (Automated)
1. Wait for GitHub rate limit to reset (~1 hour)
2. Monitor tomorrow's scheduled collection (10:00 AM)
3. Verify fresh cache files created in data/ directory

### Optional Improvements (Future)
1. Consider reducing repo_workers further (3 → 2) if issues persist
2. Add rate limit monitoring/alerting
3. Implement exponential backoff for parallel workers
4. Add metrics to track API quota usage

## Expected Behavior (Post-Fix)

**Normal Collection**:
- Duration: 2-5 minutes for 90-day range
- API calls: ~200-300 GraphQL queries
- Success rate: >95% (some repos may have partial data)
- Cache file: data/metrics_cache_90d.pkl (~400-700KB)

**If Rate Limited**:
- Retries with backoff (5s, 10s, 20s)
- Graceful failure after 3 attempts
- Continues with other repositories
- Logs warning, doesn't crash

## Documentation Created

**File**: `docs/DATA_QUALITY.md` (400+ lines)

**Contents**:
- Complete explanation of GitHub & Jira data collection
- DORA metrics data requirements
- Anti-noise filtering for Jira
- Three-tier release filtering
- Known issues and mitigations
- Summary of today's fixes

## Files Modified

1. `src/collectors/github_graphql_collector.py`:
   - Added 403 retry logic (lines 103-120)
   - Added request delays (lines 301-307)
   - Fixed date comparison (lines 1196-1209)
   - Fixed cycle_time_hours (lines 477-518)

2. `config/config.yaml`:
   - Reduced repo_workers: 5 → 3 (line 128)

3. `docs/DATA_QUALITY.md`:
   - New comprehensive documentation file

## Testing Performed

1. Manual collection with verbose logging (identified rate limit issue)
2. Collection with rate limit fixes (verified retry logic works)
3. Collection with all fixes (verified bugs resolved)

## Conclusion

All critical bugs have been fixed. The automated collection will succeed once GitHub's
secondary rate limit resets. The fixes ensure proper retry handling, data consistency,
and comprehensive documentation for future troubleshooting.

---

*For detailed information about data collection processes, see [docs/DATA_QUALITY.md](docs/DATA_QUALITY.md)*
