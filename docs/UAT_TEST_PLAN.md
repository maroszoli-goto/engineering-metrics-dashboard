# UAT Environment Test Plan

## Current Configuration Status

**Default Environment**: UAT (configured in `config.yaml`)
- Server: `https://jirauat.ops.expertcity.com`
- Time Offset: 180 days (6 months behind production)
- Pagination: Optimized for UAT (changelog disabled, threshold: 0)

## Test Checklist

### 1. Configuration Validation ✓

```bash
# Verify config is valid
python validate_config.py

# Should show:
# - UAT environment configuration
# - Both Native and WebTC teams with UAT filter IDs
# - No validation errors
```

### 2. Jira Connection Test

```bash
# Test UAT Jira connectivity
curl -H "Authorization: Bearer YOUR_UAT_BEARER_TOKEN" -k \
  https://jirauat.ops.expertcity.com/rest/api/2/serverInfo

# Should return: serverTitle, version, buildNumber
```

### 3. Filter Availability Test

```bash
# List available filters in UAT
python list_jira_filters.py

# Verify Native team filters exist:
# - 80510 (bugs)
# - 80511 (bugs_created)
# - 80512 (bugs_resolved)
# - 80513 (completed)
# - 80514 (flagged_blocked)
# - 80515 (incidents)
# - 80516 (scope)
# - 80517 (wip)

# Verify WebTC team filters exist:
# - 80518 (bugs)
# - 80519 (bugs_created)
# - 80520 (bugs_resolved)
# - 80521 (completed)
# - 80522 (flagged_blocked)
# - 80523 (incidents)
# - 80524 (scope)
# - 80525 (wip)
```

### 4. Small Data Collection Test

```bash
# Test with 30-day range (minimal data)
python collect_data.py --date-range 30d --env uat -v

# Expected output:
# - Environment: UAT
# - Jira Server: https://jirauat.ops.expertcity.com
# - Time offset: 180 days (data shifted 6 months back)
# - Successful GitHub collection
# - Successful Jira collection for both teams
# - Cache file created: data/metrics_cache_30d_uat.pkl
```

### 5. Dashboard Verification

```bash
# Start dashboard
python -m src.dashboard.app

# Access: http://localhost:5001
# Verify:
# 1. Main page loads with date range selector
# 2. Select "30d" from dropdown
# 3. Both Native and WebTC teams appear
# 4. Team dashboards load (/team/Native, /team/WebTC)
# 5. DORA metrics display correctly
# 6. Jira filter data appears (WIP, bugs, completed)
# 7. Person dashboards work (/person/dbarsony)
```

### 6. Environment Switching Test

```bash
# Test explicit environment override
python collect_data.py --date-range 30d --env prod -v

# Should fail with:
# "Environment 'prod' not found" OR
# "No filter IDs for environment 'prod'"

# This is expected - prod filters are configured but prod Jira may be inaccessible
```

### 7. Time Offset Verification

The UAT environment has a **180-day time offset** (6 months behind production).

**What this means:**
- Today's date (2026-01-24) in UAT = 2025-07-28 in production
- When collecting 90d range: UAT queries 2025-05-03 to 2025-07-28 (production equivalent)
- Fix version dates and Jira timestamps are automatically adjusted

**Verification:**
```bash
# Collect data and check logs
python collect_data.py --date-range 90d --env uat -v | grep "Time offset"

# Should show: "Time offset: 180 days (UAT is 6 months behind production)"

# Check a fix version date in Jira UAT
# If Fix Version shows: 2025-07-15 in UAT
# Dashboard should display: 2026-01-15 (shifted forward 180 days)
```

### 8. Full Collection Test (All Ranges)

```bash
# Run automated collection for all ranges
./scripts/collect_data.sh

# Expected:
# - Collects: 30d, 60d, 90d, 180d, 365d, 2025 (all for UAT)
# - Creates 6 cache files: metrics_cache_{range}_uat.pkl
# - Total time: 2-4 minutes (parallel collection enabled)
# - No 504 timeouts (pagination threshold: 0)
```

## Expected Results

### Successful Test Indicators

✅ **Configuration**: No validation errors, UAT environment recognized
✅ **Connectivity**: Jira API responds, filter queries succeed
✅ **Collection**: All ranges complete without 504 timeouts
✅ **Dashboard**: All pages render, metrics display correctly
✅ **Time Offset**: Dates shifted appropriately (180 days forward)
✅ **Cache Files**: All 6 cache files created with `_uat` suffix

### Common Issues & Fixes

**Issue**: "Environment 'uat' not found"
- **Fix**: Check `jira.default_environment` in config.yaml (line 9)

**Issue**: "No filter IDs for environment 'uat'"
- **Fix**: Verify team filter structure (should be nested: `filters.uat.wip`)

**Issue**: 504 Gateway Timeout
- **Fix**: Check `huge_dataset_threshold: 0` in config (disables changelog)

**Issue**: Dashboard shows wrong dates
- **Fix**: Verify `time_offset_days: 180` in UAT environment config

**Issue**: No releases/deployments found
- **Fix**: UAT may have limited release history, try longer date range (180d or 365d)

## Next Steps After Testing

1. **If tests pass**: Use UAT as development environment
   - Set `TEAM_METRICS_ENV=uat` in shell profile
   - Or always use `--env uat` flag
   - Dashboard will load `metrics_cache_{range}_uat.pkl` files

2. **Switch to PROD later**: Update config.yaml
   - Change `default_environment: "prod"`
   - Verify prod filter IDs are correct
   - Test prod connectivity first

3. **Parallel environments**: Keep both UAT and PROD configs
   - Use `--env` flag to switch between environments
   - Each environment creates separate cache files
   - No cross-contamination of data

## Test Execution Log

Record your test results here:

- [ ] Configuration validation: ____________________
- [ ] Jira connection test: ____________________
- [ ] Filter availability: ____________________
- [ ] Small collection (30d): ____________________
- [ ] Dashboard loads: ____________________
- [ ] Time offset verification: ____________________
- [ ] Full collection (all ranges): ____________________

**Notes:**
_Record any errors, warnings, or unexpected behavior_
