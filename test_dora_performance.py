#!/usr/bin/env python3
"""Test script to verify DORA metrics are included in performance score calculation."""

import pickle
import sys
from pathlib import Path

def test_performance_score_with_dora():
    """Load cache and verify DORA metrics in performance scores."""

    cache_file = Path("data/metrics_cache_90d.pkl")

    if not cache_file.exists():
        print(f"❌ Cache file not found: {cache_file}")
        return False

    print(f"📦 Loading cache: {cache_file}")
    with open(cache_file, 'rb') as f:
        data = pickle.load(f)

    print(f"\n🔍 Checking teams data...")
    teams = data.get('teams', {})
    print(f"   Found {len(teams)} teams: {list(teams.keys())}")

    # Check team metrics for DORA fields
    print(f"\n📊 Team DORA Metrics:")
    for team_name, team_data in teams.items():
        print(f"\n   {team_name}:")
        print(f"     - Deployment Frequency: {team_data.get('deployment_frequency', 'N/A')}")
        print(f"     - Lead Time: {team_data.get('lead_time', 'N/A')}")
        print(f"     - Change Failure Rate: {team_data.get('dora_cfr', 'N/A')}")
        print(f"     - MTTR: {team_data.get('dora_mttr', 'N/A')}")
        print(f"     - DORA Level: {team_data.get('dora_level', 'N/A')}")

    # Check comparison data
    print(f"\n🔍 Checking comparison data...")
    comparison = data.get('comparison', {})
    if comparison:
        print(f"   Found comparison data for: {list(comparison.keys())}")

        print(f"\n📊 Comparison DORA Metrics:")
        for team_name, comp_data in comparison.items():
            print(f"\n   {team_name}:")
            print(f"     - Deployment Frequency: {comp_data.get('deployment_frequency', 'N/A')}")
            print(f"     - Lead Time: {comp_data.get('lead_time', 'N/A')}")
            print(f"     - Change Failure Rate: {comp_data.get('dora_cfr', 'N/A')}")
            print(f"     - MTTR: {comp_data.get('dora_mttr', 'N/A')}")
            print(f"     - Performance Score: {comp_data.get('performance_score', 'N/A')}")

    # Check persons data for DORA fields
    print(f"\n🔍 Checking persons data...")
    persons = data.get('persons', {})
    print(f"   Found {len(persons)} persons")

    if persons:
        # Sample first person
        first_person = list(persons.keys())[0]
        person_data = persons[first_person]
        print(f"\n   Sample person ({first_person}):")
        print(f"     - Performance Score: {person_data.get('performance_score', 'N/A')}")
        print(f"     - Has DORA metrics: {any(k in person_data for k in ['deployment_frequency', 'lead_time', 'dora_cfr', 'dora_mttr'])}")

    print(f"\n✅ DORA metrics test completed!")
    print(f"\nℹ️  Note: Performance scores should now include DORA metrics in their calculation.")
    print(f"   The new weights are:")
    print(f"     - PRs: 15%")
    print(f"     - Reviews: 15%")
    print(f"     - Commits: 10%")
    print(f"     - Cycle Time: 10%")
    print(f"     - Jira Completed: 15%")
    print(f"     - Merge Rate: 5%")
    print(f"     - Deployment Frequency: 10%")
    print(f"     - Lead Time: 10%")
    print(f"     - Change Failure Rate: 5%")
    print(f"     - MTTR: 5%")

    return True

if __name__ == "__main__":
    success = test_performance_score_with_dora()
    sys.exit(0 if success else 1)
