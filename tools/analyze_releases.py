#!/usr/bin/env python3
"""
Analyze Release Data from Metrics Cache

This script analyzes the collected release data to show:
1. List of releases with issue counts
2. Lead time calculation methods used
3. DORA metrics summary
4. Issue-to-version mapping statistics
"""

import pickle
import sys
from datetime import datetime


def load_cache(cache_file="data/metrics_cache_90d.pkl"):
    """Load the metrics cache file"""
    try:
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"Error: Cache file not found: {cache_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading cache: {e}")
        sys.exit(1)


def analyze_releases(cache, team_name):
    """Analyze releases for a specific team"""
    if team_name not in cache["teams"]:
        print(f"Error: Team '{team_name}' not found in cache")
        return

    team_data = cache["teams"][team_name]

    print(f"\n{'='*70}")
    print(f"Team: {team_name}")
    print(f"{'='*70}")

    # Raw releases data
    raw_releases = team_data.get("raw_releases", [])
    print(f"\nTotal Releases Collected: {len(raw_releases)}")

    # Separate by environment
    production = [r for r in raw_releases if not r.get("is_prerelease", True)]
    staging = [r for r in raw_releases if r.get("is_prerelease", True)]

    print(f"  Production: {len(production)}")
    print(f"  Staging: {len(staging)}")

    # Show releases with issue counts
    print(f"\n{'Release Name':<30} {'Date':<12} {'Type':<10} {'Issues':<8}")
    print("-" * 70)

    for release in sorted(raw_releases, key=lambda r: r.get("published_at", ""), reverse=True)[:15]:
        name = release.get("tag_name", "Unknown")
        date = release.get("published_at", "")
        if isinstance(date, datetime):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = str(date)[:10] if date else "Unknown"

        env_type = "Staging" if release.get("is_prerelease", True) else "Production"
        issue_count = release.get("team_issue_count", 0)

        print(f"{name:<30} {date_str:<12} {env_type:<10} {issue_count:<8}")

    if len(raw_releases) > 15:
        print(f"... and {len(raw_releases) - 15} more releases")

    # Issue count statistics
    issue_counts = [r.get("team_issue_count", 0) for r in raw_releases]
    total_issues = sum(issue_counts)
    releases_with_issues = sum(1 for c in issue_counts if c > 0)
    releases_without_issues = sum(1 for c in issue_counts if c == 0)

    print(f"\nIssue Mapping Statistics:")
    print(f"  Total issues mapped: {total_issues}")
    print(f"  Releases with issues: {releases_with_issues} ({releases_with_issues/len(raw_releases)*100:.1f}%)")
    print(
        f"  Releases without issues: {releases_without_issues} ({releases_without_issues/len(raw_releases)*100:.1f}%)"
    )
    print(f"  Average issues per release: {total_issues/len(raw_releases):.1f}")

    # DORA metrics
    dora = team_data.get("dora", {})

    print(f"\nDORA Metrics Summary:")

    # Deployment Frequency
    deploy_freq = dora.get("deployment_frequency", {})
    print(f"\nDeployment Frequency:")
    print(f"  Total deployments: {deploy_freq.get('total_deployments', 0)}")
    print(f"  Per week: {deploy_freq.get('per_week', 0):.2f}")
    print(f"  Level: {deploy_freq.get('level', 'unknown')}")

    # Lead Time
    lead_time = dora.get("lead_time_for_changes", {})
    print(f"\nLead Time for Changes:")
    print(f"  Median: {lead_time.get('median_days', 0):.1f} days")
    print(f"  P75: {lead_time.get('p75_days', 0):.1f} days")
    print(f"  P90: {lead_time.get('p90_days', 0):.1f} days")
    print(f"  PRs with lead time: {lead_time.get('prs_with_lead_time', 0)}")
    print(f"  Total PRs: {lead_time.get('total_prs', 0)}")
    print(f"  Coverage: {lead_time.get('prs_with_lead_time', 0)/max(lead_time.get('total_prs', 1), 1)*100:.1f}%")
    print(f"  Level: {lead_time.get('level', 'unknown')}")

    # Change Failure Rate
    cfr = dora.get("change_failure_rate", {})
    print(f"\nChange Failure Rate:")
    if cfr.get("has_data", False):
        print(f"  Rate: {cfr.get('percentage', 0):.1f}%")
        print(f"  Level: {cfr.get('level', 'unknown')}")
    else:
        print(f"  No incident data available")

    # MTTR
    mttr = dora.get("mean_time_to_recovery", {})
    print(f"\nMean Time to Recovery:")
    if mttr.get("has_data", False):
        print(f"  Median: {mttr.get('median_hours', 0):.1f} hours")
        print(f"  Level: {mttr.get('level', 'unknown')}")
    else:
        print(f"  No incident data available")


def show_release_details(cache, team_name, release_name):
    """Show detailed information for a specific release"""
    if team_name not in cache["teams"]:
        print(f"Error: Team '{team_name}' not found in cache")
        return

    team_data = cache["teams"][team_name]
    raw_releases = team_data.get("raw_releases", [])

    release = next((r for r in raw_releases if r.get("tag_name") == release_name), None)

    if not release:
        print(f"Error: Release '{release_name}' not found for team '{team_name}'")
        return

    print(f"\n{'='*70}")
    print(f"Release Details: {release_name}")
    print(f"{'='*70}")

    print(f"\nRelease Information:")
    print(f"  Name: {release.get('tag_name')}")
    print(f"  Date: {release.get('published_at')}")
    print(f"  Environment: {'Staging' if release.get('is_prerelease', True) else 'Production'}")
    print(f"  Team Issue Count: {release.get('team_issue_count', 0)}")
    print(f"  Version ID: {release.get('version_id', 'N/A')}")
    print(f"  Version Name: {release.get('version_name', 'N/A')}")

    # Show related issues if available
    related_issues = release.get("related_issues", [])
    if related_issues:
        print(f"\nRelated Issues ({len(related_issues)}):")
        for issue in related_issues[:20]:
            print(f"  - {issue}")
        if len(related_issues) > 20:
            print(f"  ... and {len(related_issues) - 20} more issues")
    else:
        print(f"\nNo related issues found for this release")


def main():
    """Main analysis function"""
    cache = load_cache()

    print(f"\n{'='*70}")
    print(f"Team Metrics Release Analysis")
    print(f"{'='*70}")
    print(f"\nCache Timestamp: {cache.get('timestamp', 'Unknown')}")
    print(f"Date Range: {cache.get('from_date', 'Unknown')} to {cache.get('to_date', 'Unknown')}")
    print(f"Teams: {', '.join(cache.get('teams', {}).keys())}")

    # Analyze each team
    for team_name in cache.get("teams", {}).keys():
        analyze_releases(cache, team_name)

    print(f"\n{'='*70}")
    print(f"Analysis Complete")
    print(f"{'='*70}")
    print(f"\nTo see details for a specific release:")
    print(f"  python analyze_releases.py TEAM_NAME RELEASE_NAME")
    print(f"\nExample:")
    print(f"  python analyze_releases.py 'Native Team' 'Live - 21/Oct/2025'")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        cache = load_cache()
        show_release_details(cache, sys.argv[1], sys.argv[2])
    else:
        main()
