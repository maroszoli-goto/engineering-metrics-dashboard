# Lead Time Calculation Diagnosis

## Problem Statement

Native team shows unrealistically low lead time of **1.5 days median** (36 hours).

## Root Cause Identified

**88% of PRs (73 out of 83) are using the flawed time-based fallback** instead of accurate Jira-based mapping.

## Detailed Analysis (from logs - Jan 18, 2026)

### Issue-to-Version Mapping Statistics

```
Issue-to-version mapping for Native:
- Total releases: 33
- Releases with mapped issues: 8  (24%)
- Total unique issues mapped: 11
```

### Lead Time Mapping Results

```
Lead time mapping results: 83 PRs total,
- 5 Jira-mapped (6.0%)  ← ACCURATE lead times
- 71 time-based (85.5%)  ← INACCURATE (finds "next" deployment, not actual deployment)
```

### Breakdown of Failures

```
- 73 PRs had Jira key but not in issue_to_version_map  ← PRIMARY ISSUE
- 5 PRs had mapped issue but no matching release
```

## Key Findings

1. ✅ **PR title extraction is working**: 73 out of 83 PRs (88%) have Jira keys successfully extracted from titles/branches

2. ❌ **Jira→FixVersion mapping is broken**: Only 11 issues total are mapped to Fix Versions, but we have 73+ unique issue keys from PRs

3. ❌ **Most releases have NO issues**: Only 8 out of 33 releases (24%) have `related_issues` populated

## Why Time-Based Fallback Gives Wrong Results

When a PR can't be mapped via Jira, the code finds the **next chronological deployment** after PR merge:

```python
# Fallback: Find the next deployment after this PR was merged (time-based)
next_deploys = production_releases[production_releases["published_at"] > pr["merged_at"]]
```

**Problem**: This deployment might not contain the PR!

**Example**:
- PR merged: Jan 1
- Next deployment: Jan 2 (doesn't contain this PR) ← **WRONG**
- Recorded lead time: 1 day ❌
- Actual deployment with PR: Jan 15
- Actual lead time should be: 14 days ✓

## Hypothesis: Why Are Issues Not Being Mapped?

Possible reasons (needs investigation):

### Hypothesis 1: Team Member Filtering Too Restrictive

Code in `jira_collector.py:_get_issues_for_version()` filters issues by assignee:

```python
jql = f'project = {project_key} AND fixVersion = "{version_name}"'
if team_members:
    jql += f" AND assignee in ({members_str})"
```

**If**:
- Issues are assigned to people NOT in team config
- Issues are unassigned
- Team uses group assignments instead of individual

**Then**: Those issues won't be included in `related_issues`

### Hypothesis 2: Fix Versions Not Set on Jira Issues

**If**:
- Team creates Fix Versions in Jira
- But doesn't actually TAG issues with those versions
- Issues remain without Fix Version field set

**Then**: The JQL query `fixVersion = "Live - 6/Oct/2025"` returns 0 results

### Hypothesis 3: Jira Project Key Mismatch

**If**:
- PRs reference issues like `RN-123`
- But config specifies project key `RSC`
- JQL only queries: `project = RSC AND fixVersion = ...`

**Then**: RN-123 issues won't be found

## Next Steps to Fix

### 1. Run Collection with Verbose Mode (-v)

This will show debug logs we added:

```bash
python collect_data.py --date-range 90d -v
```

Look for lines like:
```
Version 'Live - 21/Oct/2025': 5 issues → ['RSC-1234', 'RSC-5678', ...]
Version 'Live - 14/Oct/2025': No team-assigned issues found
JQL: project = RSC AND fixVersion = "Live - 21/Oct/2025" AND assignee in (...) → Found 5 issues
```

### 2. Check Sample PRs

Inspect a few recent PRs to verify:
- Do they have Jira keys in title/branch? (e.g., `[RSC-123]` or `feature/RSC-123-*`)
- What project key? (RSC, RN, RW, etc.)
- Check those issues in Jira - do they have Fix Version set?

### 3. Verify Team Member List

Check `config/config.yaml`:
- Are all Native team Jira usernames listed?
- Do they match EXACTLY the assignee field in Jira?
- Try running without team filtering temporarily to see if that's the issue

### 4. Check Jira Issues Directly

Pick a recent release like "Live - 21/Oct/2025":

1. Go to Jira
2. Run JQL: `project = RSC AND fixVersion = "Live - 21/Oct/2025"`
3. How many results?
4. Are they assigned to team members?
5. Run without assignee filter: `project = RSC AND fixVersion = "Live - 21/Oct/2025"`
6. Compare result counts

### 5. Try Multiple Project Keys

If Native team works across multiple Jira projects, update config:

```yaml
teams:
  - name: "Native"
    jira:
      projects: ["RSC", "RN", "RW"]  # Add all relevant projects
```

## Logging Improvements Added

### 1. In `dora_metrics.py` (lines 238-330)

Added counters and detailed logging:
- Tracks Jira-mapped vs time-based count
- Logs why each PR failed to map (no key, not in map, no matching release)
- Outputs summary statistics

### 2. In `collect_data.py` (lines 449-473)

Added issue-to-version mapping diagnostics:
- Total releases
- Releases with issues
- Total unique issues mapped
- Sample mappings

### 3. In `jira_collector.py` (lines 849-856, 1031-1045)

Added per-version debugging:
- Shows which versions have issues
- Shows JQL queries used
- Shows result counts with/without team filtering

## Expected Output After Fix

Once the issue mapping is fixed, we should see:
- **60-80%+ Jira-mapped** (instead of 6%)
- **<20% time-based fallback** (instead of 85%)
- **Lead time median: 5-14 days** (instead of 1.5 days)
- **25-30+ releases with issues** (instead of 8)

## Files Modified

- `src/models/dora_metrics.py` - Added lead time mapping diagnostics
- `collect_data.py` - Added issue-to-version map logging
- `src/collectors/jira_collector.py` - Added per-version issue mapping logs
- `check_lead_time_mapping.py` - Diagnostic script (NEW)
- `docs/LEAD_TIME_DIAGNOSIS.md` - This document (NEW)
