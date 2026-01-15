#!/usr/bin/env python3
"""Verify WebTC scope filter returns data"""
import sys
from src.config import Config
from src.collectors.jira_collector import JiraCollector

config = Config()
jira_config = config.jira_config

# Get WebTC team config
webtc_team = next((t for t in config.teams if t['name'] == 'WebTC'), None)
if not webtc_team:
    print("❌ WebTC team not found in config")
    sys.exit(1)

scope_filter_id = webtc_team.get('jira', {}).get('filters', {}).get('scope')
print(f"WebTC Scope Filter ID: {scope_filter_id}")

if not scope_filter_id:
    print("❌ No scope filter configured for WebTC")
    sys.exit(1)

# Connect to Jira
jira_collector = JiraCollector(
    server=jira_config['server'],
    username=jira_config['username'],
    api_token=jira_config['api_token'],
    project_keys=['RSC'],
    days_back=90,
    verify_ssl=False
)

# Fetch filter
print(f"\nFetching filter {scope_filter_id}...")
try:
    issues = jira_collector.collect_filter_issues(scope_filter_id, add_time_constraint=True)
    print(f"✅ Retrieved {len(issues)} issues")

    if len(issues) == 0:
        print("\n⚠️  Filter returns 0 issues")
        print("Possible causes:")
        print("  1. No issues match filter criteria in last 90 days")
        print("  2. Filter is too restrictive")
        print("  3. Check filter in Jira UI to verify it returns results")

        # Try to get the filter details
        try:
            filter_url = f"{jira_config['server']}/rest/api/2/filter/{scope_filter_id}"
            print(f"\nFilter URL: {filter_url}")
            print("Open this URL in browser to inspect filter criteria")
        except Exception as e:
            print(f"Could not construct filter URL: {e}")
    else:
        print(f"\nSample issues:")
        for issue in issues[:5]:
            print(f"  - {issue['key']}: {issue.get('summary', 'N/A')[:60]}")

        # Show date distribution
        print(f"\nDate analysis:")
        created_dates = [i.get('created') for i in issues if i.get('created')]
        resolved_dates = [i.get('resolved') for i in issues if i.get('resolved')]
        print(f"  Issues created in window: {len(created_dates)}")
        print(f"  Issues resolved in window: {len(resolved_dates)}")

except Exception as e:
    print(f"❌ Error fetching filter: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
