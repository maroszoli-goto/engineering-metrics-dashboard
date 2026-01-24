# Incident Filtering Change: Restricted to Explicit Issue Types

**Date**: January 23, 2026
**Status**: Implemented, Pending Data Collection
**Impact**: Configuration Change Required

## Summary

Changed incident counting for DORA metrics (CFR and MTTR) to only include issues with specific issue types: **"Incident"** and **"GCS Escalation"**. This provides more accurate production incident tracking by excluding high-priority bugs that aren't true incidents.

## What Changed

### Previous Behavior

The system used **three criteria** to identify production incidents:

1. **Issue Type**: `issuetype = "Incident"`
2. **High-Priority Bugs**: `issuetype in (Bug, Defect) AND priority in (Blocker, Critical, Highest)`
3. **Production Labels**: `labels in (production, incident, outage, p1, sev1, "production-incident")`

**JQL Query (Old)**:
```jql
project IN (YOUR_PROJECTS)
AND (created >= -90d OR resolved >= -90d)
AND (
    issuetype = "Incident"
    OR (issuetype in (Bug, Defect) AND priority in (Blocker, Critical, Highest))
    OR labels in (production, incident, outage, p1, sev1, "production-incident")
)
ORDER BY created DESC
```

### New Behavior

The system now uses **explicit issue type matching** only:

**JQL Query (New)**:
```jql
project IN (YOUR_PROJECTS)
AND (created >= -90d OR resolved >= -90d)
AND issuetype IN ("Incident", "GCS Escalation")
ORDER BY created DESC
```

## Why This Change?

### Problems with Previous Approach

1. **Over-counting**: High-priority bugs were counted as incidents even when they weren't production outages
2. **Inconsistency**: Label-based filtering was unreliable (labels aren't always applied consistently)
3. **Complexity**: Three different criteria made it hard to understand what was being counted
4. **CFR Inflation**: Change Failure Rate metrics were inflated by non-incident bugs

### Benefits of New Approach

1. **Accuracy**: Only true production incidents (with explicit issue types) are counted
2. **Clarity**: Single source of truth - issue type field
3. **Predictability**: Easier to audit and verify incident counts
4. **Simplicity**: Less complex logic to maintain and debug

## Impact on Metrics

### Affected Metrics

- **Change Failure Rate (CFR)**: Number of incidents correlated to deployments
- **Mean Time to Recovery (MTTR)**: Time to resolve production incidents
- **Production Incidents Count**: Total incident count displayed in dashboard

### Expected Changes

After re-collecting data with the new filter:

- **CFR may decrease**: Fewer issues will be classified as production incidents
- **MTTR may change**: Resolution time distribution may shift
- **Incident counts will be lower**: Only explicit incident types are counted

### Unaffected Metrics

- Deployment Frequency
- Lead Time for Changes
- All GitHub PR metrics
- Jira throughput, WIP, and bug metrics (unless they use the incidents filter)

## Files Changed

### Code Changes

1. **`src/collectors/jira_collector.py`**
   - **Lines 766-770**: Simplified JQL query construction in `collect_incidents()` method
   - **Lines 875-890**: Updated `_is_production_incident()` to validate only issue types

2. **`src/dashboard/templates/documentation.html`**
   - **Lines 386-391**: Updated incident tracking setup example with new JQL query

3. **`README.md`**
   - **Lines 403-408**: Updated incident tracking setup section with new JQL query

### Documentation Changes

1. **`RELEASE_NOTES.md`**: Added release notes entry for 2026-01-23
2. **`docs/INCIDENT_FILTERING_CHANGE.md`**: This document

## Migration Guide

### Step 1: Update Jira Incident Filters

If you have configured custom incident filters in `config/config.yaml`:

**Before**:
```yaml
teams:
  - name: "Your Team"
    jira:
      filters:
        incidents: 12345  # Old filter with broad criteria
```

**Action Required**:

1. Go to Jira and edit your incident filter (or create a new one)
2. Update the JQL query to:
   ```jql
   project IN (YOUR_PROJECTS)
   AND issuetype IN ("Incident", "GCS Escalation")
   AND (created >= -90d OR resolved >= -90d)
   ORDER BY created DESC
   ```
3. Save the filter and note the filter ID
4. Update `config/config.yaml` with the filter ID (if changed)

### Step 2: Verify Issue Types Exist

Ensure your Jira instance has the required issue types:

1. **"Incident"** - Standard issue type for production incidents
2. **"GCS Escalation"** - Custom issue type (if applicable to your workflow)

If "GCS Escalation" doesn't exist in your Jira instance, you can either:
- Create the issue type in Jira, or
- Modify the code to only use "Incident" (see Customization section below)

### Step 3: Re-collect Data

After updating filters:

```bash
# Re-collect data with new filtering
python collect_data.py --date-range 90d

# Or collect all date ranges
./scripts/collect_data.sh
```

### Step 4: Verify Results

1. Start the dashboard: `python -m src.dashboard.app`
2. Check team dashboards for "Production Incidents" section
3. Verify incident counts match your Jira filter results
4. Review CFR and MTTR metrics for accuracy

## Customization

### Using Only "Incident" Type

If your organization only uses "Incident" (not "GCS Escalation"), modify:

**File**: `src/collectors/jira_collector.py`

**Line 769** - Change from:
```python
jql += 'issuetype IN ("Incident", "GCS Escalation") '
```

To:
```python
jql += 'issuetype = "Incident" '
```

**Line 890** - Change from:
```python
return issue_type == "incident" or issue_type == "gcs escalation"
```

To:
```python
return issue_type == "incident"
```

### Adding Additional Issue Types

To include other issue types (e.g., "Outage", "Service Disruption"):

**Line 769**:
```python
jql += 'issuetype IN ("Incident", "GCS Escalation", "Outage", "Service Disruption") '
```

**Line 890**:
```python
return issue_type in ["incident", "gcs escalation", "outage", "service disruption"]
```

### Making Issue Types Configurable

For a more flexible solution, add to `config/config.yaml`:

```yaml
jira:
  incident_issue_types:
    - "Incident"
    - "GCS Escalation"
```

Then modify the code to read from configuration. (This requires additional implementation.)

## Validation

### Before Data Collection

1. **Check JQL Query**: Look for log output during collection:
   ```
   Collecting incidents with JQL: (project = RSC OR project = RA) AND (created >= -90d OR resolved >= -90d) AND issuetype IN ("Incident", "GCS Escalation")
   ```

2. **Verify Filter**: Run the JQL query directly in Jira UI to see what it returns

### After Data Collection

1. **Check Incident Counts**: Compare dashboard counts with Jira filter results
2. **Verify Issue Types**: Use analysis tools to inspect collected incidents:
   ```bash
   python tools/analyze_releases.py
   ```

3. **Compare Metrics**: Note differences in CFR/MTTR before and after the change

## Troubleshooting

### Problem: No Incidents Found

**Symptoms**: Dashboard shows 0 incidents, CFR/MTTR are N/A

**Possible Causes**:
1. Issue types don't exist in your Jira instance
2. No incidents were created/resolved in the date range
3. Jira filter is misconfigured

**Solutions**:
- Verify issue types exist: Check Jira → Settings → Issues → Issue Types
- Check date range: Use a longer range (e.g., `--date-range 365d`)
- Test JQL query: Run directly in Jira UI to verify it returns results
- Check logs: Look for error messages during collection

### Problem: Incident Counts Don't Match Filter

**Symptoms**: Dashboard shows different count than Jira filter

**Possible Causes**:
1. Time range mismatch (dashboard vs filter)
2. Validation method rejecting some issues
3. Cache is stale

**Solutions**:
- Check date range in both places
- Clear cache: `rm data/metrics_cache_*.pkl`
- Re-collect: `python collect_data.py --date-range 90d`
- Enable debug logging: `python collect_data.py -v`

### Problem: Issue Type Not Recognized

**Symptoms**: Issues not being counted even though they have the right type

**Possible Causes**:
1. Issue type name mismatch (case-sensitive in JQL, case-insensitive in validation)
2. Typo in issue type name
3. Special characters in issue type name

**Solutions**:
- Check exact issue type name in Jira: Click an incident → View issue type
- Update code to match exact name
- Use debug logging to see what types are being received

## Testing Checklist

Before deploying to production:

- [ ] Updated Jira incident filter with new JQL query
- [ ] Verified JQL query returns expected results in Jira UI
- [ ] Confirmed issue types exist in Jira instance
- [ ] Re-collected data with new filtering
- [ ] Checked incident counts in dashboard
- [ ] Verified CFR and MTTR calculations
- [ ] Compared metrics before/after change (expected differences)
- [ ] Tested with multiple date ranges (30d, 90d, 365d)
- [ ] Documented expected changes in team communications
- [ ] Updated any team runbooks or documentation

## References

### Related Files

- `src/collectors/jira_collector.py` - Incident collection implementation
- `src/models/dora_metrics.py` - CFR and MTTR calculation
- `src/dashboard/templates/documentation.html` - User-facing documentation
- `README.md` - Quick start guide

### Related Documentation

- `docs/JIRA_PAGINATION_FIX.md` - Jira collection implementation details
- `docs/ARCHITECTURE.md` - System architecture overview
- `docs/IMPLEMENTATION_GUIDE.md` - Configuration guide
- `RELEASE_NOTES.md` - Change history

## Support

If you encounter issues with this change:

1. Check the troubleshooting section above
2. Review log files: `logs/team_metrics.log`
3. Enable verbose logging: `python collect_data.py -v`
4. Verify Jira filter configuration
5. Open an issue on GitHub with:
   - Log output
   - JQL query being used
   - Expected vs actual incident counts
   - Jira issue type configuration
