# Analysis Commands Reference

Quick reference for analyzing collected metrics data.

## Quick Verification

```bash
# Run verification script to check collection success
./verify_collection.sh
```

## Detailed Analysis

```bash
# Analyze all releases for both teams
python analyze_releases.py

# Show details for a specific release
python analyze_releases.py "Native Team" "Live - 21/Oct/2025"
python analyze_releases.py "WebTC Team" "Live - 10/Nov/2025"
```

## Manual Python Analysis

### Load Cache and Explore

```python
import pickle

# Load cache
with open('data/metrics_cache_90d.pkl', 'rb') as f:
    cache = pickle.load(f)

# Show basic info
print(f"Teams: {list(cache['teams'].keys())}")
print(f"Persons: {len(cache['persons'])} team members")
print(f"Collection time: {cache['timestamp']}")
```

### Show Releases with Issue Counts

```python
# Native Team releases
native = cache['teams']['Native Team']
releases = native['raw_releases']

print(f"\nNative Team - {len(releases)} releases:")
for r in releases[:10]:
    print(f"  {r['tag_name']}: {r['team_issue_count']} team issues")
```

### Show DORA Metrics

```python
# Deployment Frequency
dora = native['dora']
deploy = dora['deployment_frequency']
print(f"\nDeployment Frequency: {deploy['per_week']:.2f}/week ({deploy['level']})")

# Lead Time
lead_time = dora['lead_time_for_changes']
print(f"Lead Time: {lead_time['median_days']:.1f} days ({lead_time['level']})")
print(f"  PRs with lead time: {lead_time['prs_with_lead_time']}/{lead_time['total_prs']}")
```

### Compare Releases (Before vs After Fix)

```python
# Count releases with 0 issues vs non-zero issues
zero_issues = sum(1 for r in releases if r['team_issue_count'] == 0)
with_issues = sum(1 for r in releases if r['team_issue_count'] > 0)

print(f"\nRelease Issue Mapping:")
print(f"  Releases with 0 issues: {zero_issues} ({zero_issues/len(releases)*100:.1f}%)")
print(f"  Releases with issues: {with_issues} ({with_issues/len(releases)*100:.1f}%)")
print(f"  Total issues mapped: {sum(r['team_issue_count'] for r in releases)}")
```

### Show Person-Level Metrics

```python
# Show top contributors by PRs
persons = cache['persons']
top_prs = sorted(persons.items(),
                 key=lambda x: x[1].get('pr_count', 0),
                 reverse=True)[:5]

print("\nTop Contributors by PRs:")
for name, data in top_prs:
    prs = data.get('pr_count', 0)
    reviews = data.get('review_count', 0)
    commits = data.get('commit_count', 0)
    print(f"  {name}: {prs} PRs, {reviews} reviews, {commits} commits")
```

### Check for Specific Issues in Releases

```python
# Find which release contains a specific issue
issue_key = "RSC-1234"  # Change to your issue key

for release in releases:
    if issue_key in release.get('related_issues', []):
        print(f"Issue {issue_key} found in release: {release['tag_name']}")
        print(f"  Date: {release['published_at']}")
        print(f"  Environment: {'Production' if not release['is_prerelease'] else 'Staging'}")
        break
else:
    print(f"Issue {issue_key} not found in any release")
```

## Log Analysis

### Check for Errors in Collection

```bash
# Check for any warnings or errors
grep -i "warning\|error" /tmp/collection_final.log | head -20

# Check NoneType errors specifically
grep "NoneType" /tmp/collection_final.log

# Check collection summary
grep "Collection Summary" -A 10 /tmp/collection_final.log
```

### Show Collection Progress

```bash
# Show team collection summaries
grep "✅.*Team metrics complete" /tmp/collection_final.log

# Show person collection progress
grep "✅$" /tmp/collection_final.log | tail -20
```

## Verification Checklist

After running `./verify_collection.sh`, check:

- ✅ **No NoneType errors** - Bug fix worked correctly
- ✅ **Releases collected** - Both teams have releases (Native: ~36, WebTC: ~4)
- ✅ **Issues mapped** - Non-zero issue counts (Native: ~13+, WebTC: varies)
- ✅ **Collection completed** - "All metrics collected and saved" message
- ✅ **Cache file exists** - Fresh timestamp, reasonable size

## Expected Results (After Bug Fix)

### Native Team
- **Releases**: ~36 (24 production, 12 staging)
- **Issues mapped**: 13+ (was 0 before fix)
- **Deployment frequency**: ~2.7/week
- **Lead time**: ~1-2 days median (using Jira-based calculation)

### WebTC Team
- **Releases**: ~4 (4 production, 0 staging)
- **Issues mapped**: Varies (was 0 before fix)
- **Deployment frequency**: ~0.4/week
- **Lead time**: ~5-7 days median

## Next Steps

1. Run verification: `./verify_collection.sh`
2. Run analysis: `python analyze_releases.py`
3. Check dashboard: Open http://localhost:5000
4. Push commits: `git push origin main`
5. Reload cron job: `launchctl load ~/Library/LaunchAgents/com.team-metrics.collect.plist`
