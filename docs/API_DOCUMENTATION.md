# API Documentation - Team Metrics Dashboard

**Version**: 1.0  
**Last Updated**: January 16, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Collectors](#collectors)
   - [GitHub GraphQL Collector](#github-graphql-collector)
   - [Jira Collector](#jira-collector)
3. [Models](#models)
   - [Metrics Calculator](#metrics-calculator)
4. [Dashboard](#dashboard)
   - [Flask Routes](#flask-routes)
   - [Export APIs](#export-apis)
5. [Utilities](#utilities)
   - [Date Ranges](#date-ranges)
   - [Jira Filters](#jira-filters)
   - [Repository Cache](#repository-cache)
   - [Logging](#logging)
6. [Configuration](#configuration)

---

## Overview

The Team Metrics Dashboard provides a comprehensive API for collecting, calculating, and visualizing engineering team metrics across GitHub and Jira.

### Key Components

- **Collectors**: Fetch data from GitHub and Jira APIs
- **Models**: Calculate metrics from raw data
- **Dashboard**: Web interface with Flask routes
- **Utilities**: Helper functions for common operations

---

## Collectors

### GitHub GraphQL Collector

**Module**: `src.collectors.github_graphql_collector`  
**Class**: `GitHubGraphQLCollector`

Collects data from GitHub using the GraphQL API v4 for efficient queries.

#### Constructor

```python
GitHubGraphQLCollector(token: str, organization: str, base_url: str = "https://api.github.com/graphql")
```

**Parameters**:
- `token` (str): GitHub personal access token
- `organization` (str): GitHub organization name
- `base_url` (str, optional): GraphQL endpoint URL

**Example**:
```python
from src.collectors.github_graphql_collector import GitHubGraphQLCollector

collector = GitHubGraphQLCollector(
    token="ghp_yourtokenhere",
    organization="your-org"
)
```

#### Methods

##### `collect_repository_metrics()`

Collects pull requests, reviews, commits, and releases for a repository.

```python
collect_repository_metrics(
    owner: str,
    repo_name: str,
    since: datetime,
    until: datetime
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]
```

**Parameters**:
- `owner` (str): Repository owner (usually organization name)
- `repo_name` (str): Repository name
- `since` (datetime): Start date for collection
- `until` (datetime): End date for collection

**Returns**: Tuple of (prs, reviews, commits, releases)

**Example**:
```python
from datetime import datetime, timedelta, timezone

since = datetime.now(timezone.utc) - timedelta(days=90)
until = datetime.now(timezone.utc)

prs, reviews, commits, releases = collector.collect_repository_metrics(
    owner="your-org",
    repo_name="your-repo",
    since=since,
    until=until
)
```

##### Helper Methods

- `_is_pr_in_date_range(pr_node, since, until)`: Check if PR is within date range
- `_is_release_in_date_range(release, since, until)`: Check if release is within date range
- `_extract_pr_data(pr_node)`: Extract PR metadata from GraphQL response
- `_extract_review_data(pr_node)`: Extract review data from PR node
- `_extract_commit_data(pr_node)`: Extract commit data from PR node
- `_classify_release_environment(tag_name, is_prerelease)`: Classify as production/staging

---

### Jira Collector

**Module**: `src.collectors.jira_collector`  
**Class**: `JiraCollector`

Collects issues and metrics from Jira REST API.

#### Constructor

```python
JiraCollector(
    server: str,
    username: str,
    api_token: str,
    project_keys: List[str],
    days_back: int = 90,
    verify_ssl: bool = True,
    team_members: Optional[List[str]] = None
)
```

**Parameters**:
- `server` (str): Jira server URL
- `username` (str): Jira username
- `api_token` (str): Jira API token
- `project_keys` (List[str]): List of project keys to query
- `days_back` (int): Number of days to look back
- `verify_ssl` (bool): Whether to verify SSL certificates
- `team_members` (List[str], optional): Filter to specific team members

**Example**:
```python
from src.collectors.jira_collector import JiraCollector

collector = JiraCollector(
    server="https://jira.yourcompany.com",
    username="your.username",
    api_token="your_api_token",
    project_keys=["PROJ1", "PROJ2"],
    days_back=90
)
```

#### Methods

##### `collect_issue_metrics()`

Collects issues for a project with anti-noise filtering.

```python
collect_issue_metrics(project_key: str) -> List[Dict]
```

**Parameters**:
- `project_key` (str): Jira project key

**Returns**: List of issue dictionaries

**Example**:
```python
issues = collector.collect_issue_metrics("PROJ1")
```

##### `collect_person_issues()`

Collects issues assigned to or reported by a specific person.

```python
collect_person_issues(username: str) -> List[Dict]
```

##### `collect_filter_results()`

Fetches issues using a Jira filter ID.

```python
collect_filter_results(filter_id: int) -> Dict
```

##### `collect_releases()`

Collects releases from Jira Fix Versions.

```python
collect_releases(project_key: str, team_members: List[str]) -> List[Dict]
```

---

## Models

### Metrics Calculator

**Module**: `src.models.metrics`  
**Class**: `MetricsCalculator`

Calculates metrics from collected data.

#### Constructor

```python
MetricsCalculator(dfs: Dict[str, pd.DataFrame])
```

**Parameters**:
- `dfs` (dict): Dictionary of pandas DataFrames with keys:
  - `pull_requests`: PR data
  - `reviews`: Review data
  - `commits`: Commit data
  - `deployments`: Release/deployment data

**Example**:
```python
import pandas as pd
from src.models.metrics import MetricsCalculator

dfs = {
    'pull_requests': pd.DataFrame(prs),
    'reviews': pd.DataFrame(reviews),
    'commits': pd.DataFrame(commits),
    'deployments': pd.DataFrame(releases)
}

calculator = MetricsCalculator(dfs)
```

#### Methods

##### `calculate_pr_metrics()`

Calculates pull request metrics.

```python
calculate_pr_metrics() -> Dict
```

**Returns**:
```python
{
    'total_prs': int,
    'merged_prs': int,
    'merge_rate': float,
    'avg_cycle_time_hours': float,
    'median_cycle_time_hours': float,
    'avg_pr_size': float,
    'size_distribution': dict,
    'avg_time_to_first_review_hours': float
}
```

##### `calculate_review_metrics()`

Calculates code review metrics.

```python
calculate_review_metrics() -> Dict
```

**Returns**:
```python
{
    'total_reviews': int,
    'unique_reviewers': int,
    'top_reviewers': dict,
    'avg_reviews_per_pr': float
}
```

##### `calculate_contributor_metrics()`

Calculates contributor activity metrics.

```python
calculate_contributor_metrics() -> Dict
```

**Returns**:
```python
{
    'total_commits': int,
    'unique_contributors': int,
    'avg_commits_per_day': float,
    'total_lines_added': int,
    'total_lines_deleted': int,
    'top_contributors': dict,  # {author: {'sha': count, 'additions': sum, 'deletions': sum}}
    'daily_commit_count': dict
}
```

##### `calculate_performance_score()`

Calculates performance score (0-100) based on multiple metrics.

```python
@staticmethod
calculate_performance_score(
    person_metrics: Dict,
    all_metrics: List[Dict],
    weights: Optional[Dict] = None,
    team_size: Optional[int] = None
) -> float
```

**Parameters**:
- `person_metrics` (dict): Individual's metrics
- `all_metrics` (list): List of all team members' metrics for normalization
- `weights` (dict, optional): Custom weights for each metric (must sum to 1.0)
- `team_size` (int, optional): Team size for per-capita normalization

**Default Weights**:
```python
{
    'prs': 0.15,
    'reviews': 0.15,
    'commits': 0.10,
    'cycle_time': 0.10,
    'jira_completed': 0.15,
    'merge_rate': 0.05,
    'deployment_frequency': 0.10,
    'lead_time': 0.10,
    'change_failure_rate': 0.05,
    'mttr': 0.05
}
```

**Returns**: Score from 0-100

---

## Dashboard

### Flask Routes

**Module**: `src.dashboard.app`  
**Flask App**: `app`

#### Main Routes

##### GET /

Main overview page showing all teams.

**Response**: HTML page

##### GET /team/<team_name>

Team-specific dashboard with metrics and Jira integration.

**Parameters**:
- `team_name` (str): URL-encoded team name

**Query Parameters**:
- `range` (str, optional): Date range (e.g., "90d", "Q1-2024")

**Response**: HTML page

##### GET /team/<team_name>/compare

Team member comparison page.

**Response**: HTML page with performance rankings

##### GET /person/<username>

Individual contributor dashboard.

**Parameters**:
- `username` (str): GitHub username

**Response**: HTML page

##### GET /comparison

Cross-team comparison page.

**Response**: HTML page comparing multiple teams

##### GET /documentation

In-dashboard help and documentation.

**Response**: HTML page

##### GET /settings

Performance weight configuration page.

**Response**: HTML page with weight sliders

---

### Export APIs

All export endpoints return data in CSV or JSON format.

#### Team Export

##### GET /api/export/team/<team_name>/csv

Export team metrics as CSV.

**Response**: CSV file with headers

##### GET /api/export/team/<team_name>/json

Export team metrics as JSON.

**Response**: JSON object with metadata

#### Person Export

##### GET /api/export/person/<username>/csv

Export person metrics as CSV.

##### GET /api/export/person/<username>/json

Export person metrics as JSON.

#### Comparison Export

##### GET /api/export/comparison/csv

Export cross-team comparison as CSV.

##### GET /api/export/comparison/json

Export cross-team comparison as JSON.

#### Team Members Export

##### GET /api/export/team-members/<team_name>/csv

Export team member comparison as CSV.

##### GET /api/export/team-members/<team_name>/json

Export team member comparison as JSON.

#### Settings API

##### POST /api/settings/weights

Update performance weights.

**Request Body**:
```json
{
    "prs": 0.15,
    "reviews": 0.15,
    "commits": 0.10,
    "cycle_time": 0.10,
    "jira_completed": 0.15,
    "merge_rate": 0.05,
    "deployment_frequency": 0.10,
    "lead_time": 0.10,
    "change_failure_rate": 0.05,
    "mttr": 0.05
}
```

**Validation**:
- All weights must sum to 1.0 (±0.01 tolerance)
- Each weight must be between 0.0 and 1.0

**Response**: JSON with success status

---

## Utilities

### Date Ranges

**Module**: `src.utils.date_ranges`

#### parse_date_range()

Parses date range string into DateRange object.

```python
parse_date_range(
    range_spec: str,
    reference_date: Optional[datetime] = None
) -> DateRange
```

**Supported Formats**:
- Days: `30d`, `60d`, `90d`, `180d`, `365d`
- Quarters: `Q1-2025`, `Q2-2024`, `Q3-2023`, `Q4-2026`
- Years: `2024`, `2025`, `2023`
- Custom: `YYYY-MM-DD:YYYY-MM-DD`

**Example**:
```python
from src.utils.date_ranges import parse_date_range

dr = parse_date_range("90d")
print(f"Start: {dr.start_date}, End: {dr.end_date}, Days: {dr.days}")

dr = parse_date_range("Q1-2025")
print(f"Q1 2025: {dr.start_date} to {dr.end_date}")
```

#### get_cache_filename()

Generates cache filename for date range.

```python
get_cache_filename(range_key: str) -> str
```

**Returns**: Filename like `metrics_cache_90d.pkl`

---

### Jira Filters

**Module**: `src.utils.jira_filters`

#### list_user_filters()

Lists user's favorite Jira filters.

```python
list_user_filters(jira_client) -> List[Dict]
```

**Returns**: List of filter dictionaries with keys: id, name, jql, owner, favourite

#### search_filters_by_name()

Searches filters by name (case-insensitive, partial match).

```python
search_filters_by_name(jira_client, search_term: str) -> List[Dict]
```

#### get_filter_jql()

Gets JQL query for a filter ID.

```python
get_filter_jql(jira_client, filter_id: str) -> Optional[str]
```

---

### Repository Cache

**Module**: `src.utils.repo_cache`

Caches repository lists for 24 hours to reduce API calls.

#### get_cached_repositories()

Retrieves cached repository list if available and fresh.

```python
get_cached_repositories(
    organization: str,
    teams: List[str]
) -> Optional[List[Dict]]
```

**Returns**: Repository list or None if cache miss

#### save_cached_repositories()

Saves repository list to cache.

```python
save_cached_repositories(
    organization: str,
    teams: List[str],
    repositories: List[Dict]
) -> bool
```

---

### Logging

**Module**: `src.utils.logging`

Provides dual-output logging (console + JSON) with automatic mode detection.

#### setup_logging()

Configures logging system.

```python
setup_logging(
    log_level: str = "INFO",
    config_file: Optional[str] = "config/logging.yaml"
) -> None
```

#### get_logger()

Gets a logger instance.

```python
get_logger(name: str) -> ConsoleOutput
```

**Methods**:
- `info(message, emoji=None)`: Log info message
- `warning(message, emoji=None)`: Log warning
- `error(message, emoji=None)`: Log error
- `success(message, emoji=None)`: Log success
- `section(message)`: Log section header
- `progress(current, total, item, status_emoji=None)`: Log progress

---

## Configuration

**Module**: `src.config`  
**Class**: `Config`

### Loading Configuration

```python
from src.config import Config

config = Config.load_from_file("config/config.yaml")
```

### Accessing Configuration

```python
# GitHub settings
github_token = config.github['token']
organization = config.github['organization']

# Jira settings
jira_server = config.jira['server']
jira_username = config.jira['username']

# Teams
for team in config.teams:
    print(f"Team: {team['name']}")
    for member in team['members']:
        print(f"  - {member['name']} (GitHub: {member['github']})")

# Dashboard settings
port = config.dashboard['port']
debug = config.dashboard['debug']

# Performance weights
weights = config.get_performance_weights()
```

### Validation

```python
# Validate weight updates
try:
    config.update_performance_weights({
        'prs': 0.20,
        'reviews': 0.20,
        # ... other weights (must sum to 1.0)
    })
except ValueError as e:
    print(f"Invalid weights: {e}")
```

---

## Error Handling

### Common Exceptions

- `DateRangeError`: Invalid date range format or values
- `ConnectionError`: Network connectivity issues
- `Timeout`: API request timeout
- `KeyError`: Missing required data fields
- `ValueError`: Invalid parameter values

### Example Error Handling

```python
from src.utils.date_ranges import parse_date_range, DateRangeError

try:
    dr = parse_date_range("invalid")
except DateRangeError as e:
    print(f"Invalid date range: {e}")

try:
    collector.collect_repository_metrics(...)
except Timeout:
    print("GitHub API timeout, retrying...")
```

---

## Best Practices

1. **Use Context Managers**: Close resources properly
2. **Handle Timeouts**: Set reasonable timeouts for API calls
3. **Cache Results**: Use repository cache to reduce API calls
4. **Validate Input**: Always validate user input before processing
5. **Log Errors**: Use structured logging for debugging
6. **Rate Limiting**: Respect GitHub API rate limits (5000 points/hour)
7. **Thread Safety**: Each collector instance should have its own session

---

## Examples

### Complete Collection Example

```python
from datetime import datetime, timedelta, timezone
from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector
from src.models.metrics import MetricsCalculator
import pandas as pd

# Setup
github_collector = GitHubGraphQLCollector("token", "org")
jira_collector = JiraCollector("https://jira.com", "user", "token", ["PROJ"])

# Collect data
since = datetime.now(timezone.utc) - timedelta(days=90)
until = datetime.now(timezone.utc)

prs, reviews, commits, releases = github_collector.collect_repository_metrics(
    "org", "repo", since, until
)

jira_issues = jira_collector.collect_issue_metrics("PROJ")

# Calculate metrics
dfs = {
    'pull_requests': pd.DataFrame(prs),
    'reviews': pd.DataFrame(reviews),
    'commits': pd.DataFrame(commits),
    'deployments': pd.DataFrame(releases)
}

calculator = MetricsCalculator(dfs)
pr_metrics = calculator.calculate_pr_metrics()
review_metrics = calculator.calculate_review_metrics()

print(f"Total PRs: {pr_metrics['total_prs']}")
print(f"Merge Rate: {pr_metrics['merge_rate']:.1%}")
print(f"Total Reviews: {review_metrics['total_reviews']}")
```

---

## Version History

### 1.0 (January 2026)
- Initial API documentation
- Complete coverage of all public APIs
- Examples and best practices

---

For more information, see:
- [CLAUDE.md](CLAUDE.md) - Development guide
- [README.md](../README.md) - Project overview
- [TESTING.md](TESTING.md) - Testing guide
