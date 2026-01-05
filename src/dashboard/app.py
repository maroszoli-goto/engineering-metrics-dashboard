from flask import Flask, render_template, jsonify, redirect, request
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import Config
from src.collectors.github_collector import GitHubCollector
from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector
from src.models.metrics import MetricsCalculator
import pandas as pd

app = Flask(__name__)

# Global cache
metrics_cache = {
    'data': None,
    'timestamp': None
}

def load_cache_from_file():
    """Load cached metrics from file if available"""
    import pickle
    from pathlib import Path

    cache_file = Path(__file__).parent.parent.parent / 'data' / 'metrics_cache.pkl'
    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                # Handle both old format (cache_data['data']) and new format (direct structure)
                if 'data' in cache_data:
                    metrics_cache['data'] = cache_data['data']
                else:
                    # New format: teams, persons, comparison at top level
                    metrics_cache['data'] = cache_data
                metrics_cache['timestamp'] = cache_data.get('timestamp')
                print(f"Loaded cached metrics from {cache_file}")
                print(f"Cache timestamp: {metrics_cache['timestamp']}")
                return True
        except Exception as e:
            print(f"Failed to load cache: {e}")
            return False
    return False

# Try to load cache on startup
load_cache_from_file()

def get_config():
    """Load configuration"""
    return Config()

def should_refresh_cache(cache_duration_minutes=60):
    """Check if cache should be refreshed"""
    if metrics_cache['timestamp'] is None:
        return True

    elapsed = (datetime.now() - metrics_cache['timestamp']).total_seconds() / 60
    return elapsed > cache_duration_minutes

def refresh_metrics():
    """Collect and calculate metrics using GraphQL API"""
    config = get_config()
    teams = config.teams

    if not teams:
        print("⚠️ No teams configured. Please configure teams in config.yaml")
        return None

    print(f"🔄 Refreshing metrics for {len(teams)} team(s) using GraphQL API...")

    # Connect to Jira
    jira_config = config.jira_config
    jira_collector = None

    if jira_config.get('server'):
        try:
            jira_collector = JiraCollector(
                server=jira_config['server'],
                username=jira_config['username'],
                api_token=jira_config['api_token'],
                project_keys=jira_config.get('project_keys', []),
                days_back=config.days_back,
                verify_ssl=False
            )
            print("✅ Connected to Jira")
        except Exception as e:
            print(f"⚠️ Could not connect to Jira: {e}")

    # Collect data for each team
    team_metrics = {}
    all_github_data = {
        'pull_requests': [],
        'reviews': [],
        'commits': [],
        'deployments': []
    }

    for team in teams:
        team_name = team.get('name')
        print(f"\n📊 Collecting {team_name} Team...")

        github_members = team.get('github', {}).get('members', [])
        filter_ids = team.get('jira', {}).get('filters', {})

        # Collect GitHub metrics using GraphQL
        github_collector = GitHubGraphQLCollector(
            token=config.github_token,
            organization=config.github_organization,
            teams=[team.get('github', {}).get('team_slug')] if team.get('github', {}).get('team_slug') else [],
            team_members=github_members,
            days_back=config.days_back
        )

        team_github_data = github_collector.collect_all_metrics()

        all_github_data['pull_requests'].extend(team_github_data['pull_requests'])
        all_github_data['reviews'].extend(team_github_data['reviews'])
        all_github_data['commits'].extend(team_github_data['commits'])

        print(f"   - PRs: {len(team_github_data['pull_requests'])}")
        print(f"   - Reviews: {len(team_github_data['reviews'])}")
        print(f"   - Commits: {len(team_github_data['commits'])}")

        # Collect Jira filter metrics
        jira_filter_results = {}
        if jira_collector and filter_ids:
            print(f"📊 Collecting Jira filters for {team_name}...")
            jira_filter_results = jira_collector.collect_team_filters(filter_ids)

        # Calculate team metrics
        team_dfs = {
            'pull_requests': pd.DataFrame(team_github_data['pull_requests']),
            'reviews': pd.DataFrame(team_github_data['reviews']),
            'commits': pd.DataFrame(team_github_data['commits']),
            'deployments': pd.DataFrame(team_github_data['deployments']),
        }

        calculator = MetricsCalculator(team_dfs)
        team_metrics[team_name] = calculator.calculate_team_metrics(
            team_name=team_name,
            team_config=team,
            jira_filter_results=jira_filter_results
        )

    # Calculate team comparison
    all_dfs = {
        'pull_requests': pd.DataFrame(all_github_data['pull_requests']),
        'reviews': pd.DataFrame(all_github_data['reviews']),
        'commits': pd.DataFrame(all_github_data['commits']),
        'deployments': pd.DataFrame(all_github_data['deployments']),
    }

    calculator_all = MetricsCalculator(all_dfs)
    team_comparison = calculator_all.calculate_team_comparison(team_metrics)

    # Package data
    cache_data = {
        'teams': team_metrics,
        'comparison': team_comparison,
        'timestamp': datetime.now()
    }

    metrics_cache['data'] = cache_data
    metrics_cache['timestamp'] = datetime.now()

    print(f"\n✅ Metrics refreshed at {metrics_cache['timestamp']}")

    return cache_data

@app.route('/')
def index():
    """Main dashboard page - shows team overview"""
    config = get_config()

    # If no cache exists, show loading page
    if metrics_cache['data'] is None:
        return render_template('loading.html')

    cache = metrics_cache['data']

    # Check if we have the new team-based structure
    if 'teams' in cache:
        # New structure - show team overview
        teams = config.teams
        team_list = []

        for team in teams:
            team_name = team.get('name')
            team_data = cache['teams'].get(team_name, {})
            github_metrics = team_data.get('github', {})
            jira_metrics = team_data.get('jira', {})

            team_list.append({
                'name': team_name,
                'display_name': team.get('display_name', team_name),
                'pr_count': github_metrics.get('pr_count', 0),
                'review_count': github_metrics.get('review_count', 0),
                'commit_count': github_metrics.get('commit_count', 0),
                'avg_cycle_time': github_metrics.get('avg_cycle_time', 0),
                'throughput': jira_metrics.get('throughput', {}).get('weekly_avg', 0) if jira_metrics.get('throughput') else 0,
                'wip_count': jira_metrics.get('wip', {}).get('count', 0) if jira_metrics.get('wip') else 0,
            })

        return render_template('teams_overview.html',
                             teams=team_list,
                             cache=cache,
                             config=config,
                             updated_at=metrics_cache['timestamp'])
    else:
        # Legacy structure - use old dashboard
        return render_template('dashboard.html',
                             metrics=cache,
                             updated_at=metrics_cache['timestamp'])

@app.route('/api/metrics')
def api_metrics():
    """API endpoint for metrics data"""
    config = get_config()

    if should_refresh_cache(config.dashboard_config.get('cache_duration_minutes', 60)):
        try:
            refresh_metrics()
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify(metrics_cache['data'])

@app.route('/api/refresh')
def api_refresh():
    """Force refresh metrics"""
    try:
        metrics = refresh_metrics()
        return jsonify({'status': 'success', 'metrics': metrics})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/collect')
def collect():
    """Trigger collection and redirect to dashboard"""
    try:
        refresh_metrics()
        return redirect('/')
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/team/<team_name>')
def team_dashboard(team_name):
    """Team-specific dashboard"""
    config = get_config()

    if metrics_cache['data'] is None:
        return render_template('loading.html')

    # Check if this is new team-based cache structure
    cache = metrics_cache['data']

    if 'teams' in cache:
        # New structure
        team_data = cache['teams'].get(team_name)

        if not team_data:
            return render_template('error.html', error=f"Team '{team_name}' not found")

        team_config = config.get_team_by_name(team_name)

        return render_template('team_dashboard.html',
                             team_name=team_name,
                             team_display_name=team_config.get('display_name', team_name) if team_config else team_name,
                             team_data=team_data,
                             team_config=team_config,
                             config=config,
                             days_back=config.days_back,
                             jira_server=config.jira_config.get('server', 'https://jira.ops.expertcity.com'),
                             updated_at=metrics_cache['timestamp'])
    else:
        # Legacy structure - show error
        return render_template('error.html',
                             error="Team dashboards require team configuration. Please update config.yaml and re-run data collection.")

@app.route('/person/<username>')
def person_dashboard(username):
    """Person-specific dashboard"""
    config = get_config()

    if metrics_cache['data'] is None:
        return render_template('loading.html')

    cache = metrics_cache['data']

    if 'persons' not in cache:
        return render_template('error.html',
                             error="Person dashboards require team configuration. Please update config.yaml and re-run data collection.")

    person_data = cache['persons'].get(username)

    if not person_data:
        return render_template('error.html', error=f"No metrics found for user '{username}'")

    # Get period parameter
    period = request.args.get('period', '90d')

    # Find which team this person belongs to
    team_name = None
    for team in config.teams:
        if username in team.get('github', {}).get('members', []):
            team_name = team.get('name')
            break

    return render_template('person_dashboard.html',
                         username=username,
                         person_data=person_data,
                         team_name=team_name,
                         period=period,
                         available_periods=config.time_periods.get('last_n_days', []),
                         updated_at=metrics_cache['timestamp'])

@app.route('/comparison')
def team_comparison():
    """Side-by-side team comparison"""
    if metrics_cache['data'] is None:
        return render_template('loading.html')

    cache = metrics_cache['data']

    if 'comparison' not in cache:
        return render_template('error.html',
                             error="Team comparison requires team configuration.")

    return render_template('comparison.html',
                         comparison=cache['comparison'],
                         teams=cache.get('teams', {}),
                         updated_at=metrics_cache['timestamp'])

def main():
    config = get_config()
    dashboard_config = config.dashboard_config

    app.run(
        debug=dashboard_config.get('debug', True),
        port=dashboard_config.get('port', 5000),
        host='0.0.0.0'
    )

if __name__ == '__main__':
    main()
