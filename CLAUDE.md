# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Team Metrics Dashboard - A Python-based metrics collection and visualization tool for tracking engineering team performance across GitHub and Jira.

**Key Technology**: Uses GitHub GraphQL API v4 for efficient data collection (50-70% fewer API calls than REST).

## Development Commands

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your GitHub token, Jira credentials, and team configuration
```

### Data Collection
```bash
# Collect metrics with flexible date ranges
python collect_data.py --date-range 90d     # Last 90 days (default)
python collect_data.py --date-range 30d     # Last 30 days
python collect_data.py --date-range 180d    # Last 6 months
python collect_data.py --date-range Q1-2025 # Specific quarter
python collect_data.py --date-range 2024    # Full year

# List available Jira filters (utility to find filter IDs)
python list_jira_filters.py
```

**Note**: Each collection creates a separate cache file (e.g., `metrics_cache_90d.pkl`) allowing you to switch between date ranges in the dashboard without re-collecting data.

### Parallel Data Collection

**Performance Optimization** (5-6x total speedup):

The system implements multiple performance optimizations for faster data collection:

1. **Team Parallelization**: Collects multiple teams concurrently (3 workers default)
2. **Repository Parallelization**: Within each team, collects multiple repos concurrently (5 workers default)
3. **Person Parallelization**: Collects multiple person metrics concurrently (8 workers default)
4. **Filter Parallelization**: Within each team, collects multiple Jira filters concurrently (4 workers default)
5. **Connection Pooling**: Reuses HTTP connections to reduce TCP handshake overhead (automatic, 5-10% speedup)
6. **Repository Caching**: Caches team repository lists for 24 hours to eliminate redundant queries (automatic, 5-15s saved)
7. **GraphQL Query Batching**: Combines PRs and Releases queries into single requests (automatic, 20-40% speedup, 50% fewer API calls)

**Configuration** (`config/config.yaml`):
```yaml
parallel_collection:
  enabled: true           # Master switch
  person_workers: 8       # Concurrent person collections
  team_workers: 3         # Concurrent team collections
  repo_workers: 5         # Concurrent repo collections per team
  filter_workers: 4       # Concurrent Jira filter collections per team
```

**Performance Impact**:
- Single collection: 5 minutes → ~1.5 minutes (3.3x speedup)
- 12-range collection: ~18 hours → ~4 hours (4.5x speedup)
- Person collection: 100s → 15s (7-8x speedup)
- Team collection: 120s → 50s (2-3x speedup)
- Repository collection: 60s → 12-15s per team (4-5x speedup)
- Filter collection: 24-50s → 8-12s per team (60-70% speedup)

**Rate Limiting**:
- **GitHub**: Secondary rate limits (403 errors) may occur with aggressive parallelization
  - System handles these gracefully with built-in retry logic
  - Reduce `repo_workers` to 3-4 if errors are too frequent
- **Jira**: No documented rate limits, but conservative defaults used
  - Reduce `filter_workers` to 2-3 if experiencing timeouts or throttling

**Disable Parallelization**:
Set `enabled: false` in config to fall back to sequential mode for troubleshooting or if experiencing excessive rate limiting.

### HTTP Connection Pooling

**Automatic Optimization** (5-10% speedup):

The GitHub GraphQL collector uses `requests.Session` for HTTP connection pooling, reducing TCP handshake overhead:

**Implementation** (`src/collectors/github_graphql_collector.py`):
```python
# Session created in __init__()
self.session = requests.Session()
self.session.headers.update(self.headers)

# Connection pool configured for parallel operations
adapter = requests.adapters.HTTPAdapter(
    pool_connections=20,  # Connection pools
    pool_maxsize=20,      # Max connections per pool
    max_retries=0         # Manual retry logic
)
self.session.mount('https://', adapter)
self.session.mount('http://', adapter)
```

**Benefits**:
- **Connection Reuse**: Avoids creating new TCP connections for every API request
- **Reduced Overhead**: ~50-100ms per new connection → ~5-10ms for pooled connections
- **Thread-Safe**: Each collector has its own session, safe for parallel operations
- **Automatic Cleanup**: Session manages connection lifecycle automatically

**Performance Impact**:
- Per-collector savings: ~4 seconds per 100 requests (80% reduction in connection overhead)
- Overall collection: 5-10% speedup from eliminated TCP handshakes
- Example: 11 parallel collectors × 4s = 44 seconds saved per collection

**No Configuration Required**: Connection pooling is always enabled and requires no user configuration.

### Repository List Caching

**Automatic Optimization** (5-15 second speedup per collection):

Team repository lists rarely change, so the system caches them to avoid redundant GraphQL queries on every collection.

**Implementation** (`src/utils/repo_cache.py` + `src/collectors/github_graphql_collector.py`):
```python
# Check cache first
cached_repos = get_cached_repositories(organization, teams)
if cached_repos is not None:
    return cached_repos

# Cache miss - fetch from GitHub and save for 24 hours
repo_list = _fetch_from_github()
save_cached_repositories(organization, teams, repo_list)
```

**Cache Behavior**:
- **Location**: `data/repo_cache/` (JSON files, one per org+teams combination)
- **Expiration**: 24 hours (ensures max 1-day staleness)
- **Cache Key**: MD5 hash of `{organization}:{team1,team2,...}`
- **Graceful Degradation**: If cache read fails, fetches from GitHub automatically

**Benefits**:
- **Eliminates Redundant Queries**: Saves 1-2 GraphQL queries per team per collection
- **Significant Speedup**: 5-15 seconds saved on cached collections (zero API calls for repos)
- **Daily Collections**: First collection caches, next 23 collections benefit (~2-6 minutes daily savings)
- **Transparent**: Works automatically, no configuration needed

**Cache Management**:
```bash
# Clear cache manually if repository list changes
python scripts/clear_repo_cache.py

# Or remove cache directory
rm -rf data/repo_cache/
```

**Expected Output**:
```
# First collection (cache miss)
  📡 Fetching repositories from GitHub...
    Team: itsg-rescue-native
      Found 16 repositories
  💾 Cached 16 repositories

# Subsequent collections (cache hit)
  ✅ Using cached repositories (age: 0.0h)
Total repositories to collect: 16
```

**No Configuration Required**: Repository caching is always enabled and requires no user configuration.

### GraphQL Query Batching

**Automatic Optimization** (20-40% speedup, 50% fewer API calls):

The system batches multiple GraphQL queries into a single request to minimize network overhead and API calls.

**Implementation** (`src/collectors/github_graphql_collector.py:660-838`):

**Before** (2 separate queries per repository):
1. Query 1: Fetch PRs + Reviews + Commits
2. Query 2: Fetch Releases (separate API call)

**After** (1 batched query per repository):
```python
# Single batched query fetches everything
def _collect_repository_metrics_batched(owner, repo_name):
    query = """
    query($owner: String!, $name: String!, $prCursor: String, $releaseCursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequests(first: 50, after: $prCursor, ...) { ... }
        releases(first: 100, after: $releaseCursor, ...) { ... }
      }
    }
    """
```

**Key Features**:
- **Dual Pagination**: Independent cursors for PRs and releases
- **Early Termination**: Stops when both datasets exceed date range
- **Data Extraction**: Helper methods parse responses efficiently
- **Backward Compatible**: Old methods preserved as fallback

**Benefits**:
- **50% Fewer API Calls**: Combines 2 queries into 1 per page
- **Reduced Network Overhead**: Single TCP connection per page vs. 2
- **Faster Collection**: 20-40% speedup on typical repositories
- **Example Savings**: 30 repos × 8 pages = 240 calls saved (480 → 240)

**Performance Impact**:
- **Per Repository**: 2 minutes saved on typical 30-repository collection
- **API Call Reduction**: 50% fewer GraphQL requests
- **Network Efficiency**: Single round-trip vs. multiple sequential requests

**Helper Methods** (lines 421-488):
- `_is_pr_in_date_range()` - Date filtering for PRs
- `_is_release_in_date_range()` - Date filtering for releases
- `_extract_pr_data()` - Extract PR metadata
- `_extract_review_data()` - Extract review data from PRs
- `_extract_commit_data()` - Extract commit data from PRs

**No Configuration Required**: Query batching is always enabled and requires no user configuration.

### Configuration Validation

Before running collection or starting the dashboard, validate your configuration:

```bash
python validate_config.py
python validate_config.py --config path/to/config.yaml
```

**Validation Checks:**
- Config file exists and is valid YAML
- Required sections present (github, jira, teams)
- GitHub token format (ghp_*, gho_*, ghs_*, github_pat_*)
- Jira server URL format (http:// or https://)
- Team structure (name, members with github/jira)
- No duplicate team names
- Dashboard config (port 1-65535, positive timeouts/cache duration)
- Performance weights (sum to 1.0, range 0.0-1.0)
- Jira filter IDs are integers

**Exit Codes:**
- `0`: Validation passed
- `1`: Validation failed with errors

**Integration:**
Use in CI/CD pipelines or pre-commit hooks to catch config errors early.

### Running the Dashboard
```bash
# Start Flask web server
python -m src.dashboard.app

# Access at http://localhost:5001
# Available routes:
#   /                                 - Main overview
#   /team/<team_name>                 - Team-specific dashboard
#   /team/<team_name>/compare         - Team member comparison
#   /person/<username>                - Individual contributor dashboard
#   /comparison                       - Cross-team comparison
```

### Automation (macOS)

**Persistent Dashboard** - Run dashboard continuously in background:
```bash
# Load service (starts dashboard, auto-restarts on failure, persists across reboots)
launchctl load ~/Library/LaunchAgents/com.team-metrics.dashboard.plist

# Check status
launchctl list | grep team-metrics

# Stop/Start
launchctl stop com.team-metrics.dashboard
launchctl start com.team-metrics.dashboard

# View logs
tail -f logs/dashboard.log
```

**Scheduled Data Collection** - Daily at 10:00 AM:
```bash
# Load scheduler
launchctl load ~/Library/LaunchAgents/com.team-metrics.collect.plist

# Trigger manually
launchctl start com.team-metrics.collect

# View logs
tail -f logs/collect_data.log
```

**Files**:
- `scripts/start_dashboard.sh` - Dashboard wrapper script
- `scripts/collect_data.sh` - Collection wrapper script
- `~/Library/LaunchAgents/com.team-metrics.dashboard.plist` - Dashboard service
- `~/Library/LaunchAgents/com.team-metrics.collect.plist` - Collection scheduler
- `logs/` - All service logs
```

### Testing
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests (135+ tests, ~2.5 seconds)
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest tests/unit/test_time_periods.py -v

# Run tests matching pattern
pytest -k "test_quarter" -v

# Generate HTML coverage report
pytest --cov --cov-report=html
open htmlcov/index.html

# Run fast tests only (exclude slow integration tests)
pytest -m "not slow"
```

**Test Organization:**
- `tests/unit/` - Pure logic and utility function tests (95%+ coverage target)
  - `test_dora_trends.py` - 13 tests for DORA trend calculations (NEW)
  - `test_performance_score.py` - 19 tests for performance scoring
  - `test_config.py` - 27 tests for configuration validation
  - `test_metrics_calculator.py` - 30+ tests for metrics calculations
  - `test_time_periods.py` - 30+ tests for date utilities
  - `test_activity_thresholds.py` - 15+ tests for thresholds
- `tests/collectors/` - API response parsing tests (70%+ coverage target)
- `tests/fixtures/` - Mock data generators for consistent test data
- `tests/conftest.py` - Shared pytest fixtures

**Coverage Status:**
| Module | Target | Actual | Status |
|--------|--------|--------|--------|
| time_periods.py | 95% | 96% | ✅ |
| activity_thresholds.py | 90% | 92% | ✅ |
| metrics.py | 85% | 87% | ✅ |
| github_graphql_collector.py | 70% | 72% | ✅ |
| jira_collector.py | 75% | 78% | ✅ |
| **Overall Project** | **80%** | **83%** | **✅** |

### Analysis Tools

**Quick Verification:**
```bash
# Verify collection completed successfully
./verify_collection.sh
```

Checks for:
- NoneType errors (should be 0 after bug fix)
- Releases collected per team
- Issue mapping success (non-zero counts)
- Collection completion status
- Cache file freshness

**Detailed Release Analysis:**
```bash
# Analyze all releases with DORA metrics
python analyze_releases.py

# Show specific release details
python analyze_releases.py "Native Team" "Live - 21/Oct/2025"
```

Shows:
- Release list with issue counts
- Production vs staging breakdown
- Issue mapping statistics
- Full DORA metrics (deployment frequency, lead time, CFR, MTTR)
- Related issues per release

**Command Reference:**
- `ANALYSIS_COMMANDS.md` - Complete guide with Python snippets, log analysis commands, and verification checklist
- Includes manual cache inspection examples
- Expected results after bug fix
- Next steps for post-collection workflow

## Architecture

### Data Flow

1. **Collection Phase** (`collect_data.py`):
   - **Parallel Collection** - Uses `ThreadPoolExecutor` for concurrent data gathering:
     - Teams collected in parallel (3 workers)
     - Repositories within each team collected in parallel (5 workers)
     - Person metrics collected in parallel (8 workers)
   - `GitHubGraphQLCollector` → Fetches PRs, reviews, commits from GitHub GraphQL API
   - `JiraCollector` → Fetches team filter results from Jira REST API
   - `MetricsCalculator` → Processes raw data into metrics
   - Cache saved to `data/metrics_cache_<range>.pkl` (pickle format)

2. **Dashboard Phase** (`src/dashboard/app.py`):
   - Flask app loads cached metrics on startup
   - Renders templates with pre-calculated metrics
   - Optional: Refresh button re-runs collection using GraphQL API

### Key Components

**Collectors** (`src/collectors/`):
- `github_graphql_collector.py` - **Primary collector**, uses GraphQL API v4 for efficiency
- `github_collector.py` - Legacy REST API collector (kept for reference)
- `jira_collector.py` - Jira REST API with Bearer token authentication

**Models** (`src/models/`):
- `metrics.py` - `MetricsCalculator` class processes raw data into metrics
  - `calculate_team_metrics()` - Team-level aggregations with Jira filters
  - `calculate_person_metrics()` - Individual contributor metrics (90-day rolling window)
  - `calculate_team_comparison()` - Cross-team comparison data
  - `calculate_performance_score()` - Composite 0-100 scoring for rankings (lines 656-759)

**Configuration** (`src/config.py`):
- `Config` class loads from `config/config.yaml`
- Multi-team support with separate GitHub/Jira member lists per team
- Each team has Jira filter IDs for custom metrics

**Dashboard** (`src/dashboard/`):
- `app.py` - Flask routes and cache management
- `templates/` - Jinja2 templates with Plotly charts
  - `teams_overview.html` - Main dashboard (2-column grid)
  - `team_dashboard.html` - Team metrics with Jira integration
  - `person_dashboard.html` - Individual contributor view
  - `comparison.html` - Side-by-side team comparison with DORA metrics
- `static/css/main.css` - Theme CSS with dark mode variables
- `static/css/hamburger.css` - Hamburger menu styles with animations
- `static/js/theme-toggle.js` - Dark/light mode switcher
- `static/js/charts.js` - Shared chart utilities and CHART_COLORS constants

### Configuration Structure

`config/config.yaml` has this structure:
```yaml
github:
  token: "ghp_..."
  organization: "your-org"
  days_back: 90

jira:
  server: "https://jira.yourcompany.com"
  username: "username"  # NOT email
  api_token: "bearer_token"

teams:
  - name: "Backend"
    display_name: "Backend Team"
    members:
      - name: "John Doe"
        github: "johndoe"
        jira: "jdoe"
      - name: "Jane Smith"
        github: "janesmith"
        jira: "jsmith"
    github:
      team_slug: "backend-team"
    jira:
      filters:
        wip: 12345
        completed_12weeks: 12346
        bugs: 12347
        incidents: 12348  # For DORA CFR/MTTR (optional but recommended)
        # ... more filter IDs

dashboard:
  port: 5001                     # Web server port
  debug: true                    # Enable debug mode
  cache_duration_minutes: 60     # How long to cache metrics before auto-refresh
  jira_timeout_seconds: 120      # Timeout for Jira API requests (configurable)

# Performance Score Weights (optional - if omitted, uses built-in defaults)
# Customize via Settings page (http://localhost:5001/settings) or here
# All weights must sum to 1.0 (100%)
performance_weights:
  # GitHub metrics
  prs: 0.15
  reviews: 0.15
  commits: 0.10
  cycle_time: 0.10
  merge_rate: 0.05
  jira_completed: 0.15
  # DORA metrics
  deployment_frequency: 0.10
  lead_time: 0.10
  change_failure_rate: 0.05
  mttr: 0.05
```

**Configurable Timeouts:**
- `cache_duration_minutes`: Dashboard checks cache age and auto-refreshes if older than this value
- `jira_timeout_seconds`: Maximum time to wait for Jira API responses (applies to all Jira operations during collection)

These settings can be adjusted without code changes to accommodate slower networks or larger datasets.

### Performance Scoring System

**Algorithm** (`src/models/metrics.py:1339-1499`):
- Composite score from 0-100 (higher is better)
- Uses min-max normalization across all teams/members
- Weighted sum of normalized metrics

**Default Weights (10 metrics including DORA)**:
```python
# GitHub metrics (55%)
'prs': 0.15,                    # Pull requests created
'reviews': 0.15,                # Code reviews given
'commits': 0.10,                # Total commits
'cycle_time': 0.10,             # PR merge time (lower is better - inverted)
'merge_rate': 0.05,             # PR merge success rate
'jira_completed': 0.15,         # Jira issues resolved

# DORA metrics (30%)
'deployment_frequency': 0.10,   # Deployments per week
'lead_time': 0.10,              # Lead time (lower is better - inverted)
'change_failure_rate': 0.05,    # CFR (lower is better - inverted)
'mttr': 0.05                    # MTTR (lower is better - inverted)
```

**Configuration Options:**
- **Settings Page (Recommended)**: http://localhost:5001/settings with interactive sliders and presets
- **Config File**: Add `performance_weights` section to `config.yaml` (optional, uses defaults if omitted)
- **Backward Compatibility**: Old configs with only 6 metrics automatically use new 10-metric defaults with warning

**Key Features**:
- **Cycle Time Inversion**: Score = (100 - normalized_value) for cycle time
- **Team Size Normalization**: Divides volume metrics by team_size for per-capita comparison
- **Edge Case Handling**: Returns 50.0 when all values are equal (no variation)

**Used In**:
- Team Comparison page: Overall Performance card
- Team Member Comparison: Top Performers leaderboard with rankings

### GitHub GraphQL Queries

**Why GraphQL is used**:
- Separate rate limit (5000 points/hour vs REST's 5000 requests/hour)
- Single query fetches PRs + reviews + commits (vs 3+ REST calls)
- Pagination built-in, no need for multiple page requests
- 50-70% fewer API calls = faster collection

**Example PR Query** (`github_graphql_collector.py:268-298`):
```graphql
query {
  repository(owner: "org", name: "repo") {
    pullRequests(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number
        title
        createdAt
        mergedAt
        closedAt
        author { login }
        reviews(first: 100) {
          nodes {
            author { login }
            createdAt
            state
          }
        }
        additions
        deletions
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

**Example Repository Query** (lines 118-134):
```graphql
query {
  organization(login: "org") {
    teams(first: 100) {
      nodes {
        slug
        repositories(first: 100) {
          nodes {
            name
            owner { login }
          }
        }
      }
    }
  }
}
```

**Pagination**: Uses `endCursor` and `hasNextPage` for automatic pagination
**Ordering**: PRs ordered by `CREATED_AT` (not `UPDATED_AT`) to ensure consistent results

### Jira JQL Queries

**Project Query** (`jira_collector.py:60`):
```jql
project = {key} AND (
  created >= -90d OR
  resolved >= -90d OR
  (statusCategory != Done AND updated >= -90d)
)
```

**Person Query** (`jira_collector.py:195`):
```jql
assignee = "username" AND (
  created >= -90d OR
  resolved >= -90d OR
  (statusCategory != Done AND updated >= -90d)
)
```

**Anti-Noise Filtering Rationale**:
- `updated >= -90d` only applies to non-Done tickets
- Prevents mass administrative updates (e.g., bulk label changes) from polluting results
- Only captures actual work: new issues, resolved issues, and active WIP
- Without this filter, bulk updates can include thousands of old closed tickets

**Filter Query** (line 278):
```python
# Uses Jira filter IDs from team config
# Dynamically adds time constraints: created >= -90d OR resolved >= -90d
filter_url = f"{server}/rest/api/2/filter/{filter_id}"
```

**Worklogs Query** (line 153):
```python
# Fetches time tracking data for cycle time calculations
worklog_url = f"{server}/rest/api/2/issue/{issue_key}/worklog"
```

### Metrics Time Windows

- **All metrics (Team, Person)**: Fixed 90-day rolling window (default)
- **Time window control**: Edit `DAYS_BACK` constant in `collect_data.py` line 19
- **Jira metrics**: Team-specific filters define their own time ranges

### Dashboard UI Features

**Navigation:**
- **Hamburger Menu**: Team links auto-generate from config/cache (no code changes needed when adding teams)
- **Back to Top Button**: Floating button appears after scrolling 300px down (CSS: `#back-to-top` in main.css)
- **Data Freshness**: "Data from X hours ago" badges use `format_time_ago()` Jinja filter

**Loading States:**
- **Reload Button**: Shows ⏳ icon, "Reloading..." text, and disables during operation
- **Implementation**: `reloadCache()` function in `theme-toggle.js`

**Export:**
- All export filenames include current date: `team_native_metrics_2026-01-14.csv`
- 8 export routes total (CSV/JSON for team/person/comparison/team-members)

## UI Architecture

**Template Architecture (3-Tier Inheritance):**

1. **Master Template** (`base.html`):
   - Contains: `<head>`, hamburger menu, footer, theme toggle integration
   - Provides blocks: `title`, `extra_css`, `extra_js`, `header`, `content`
   - All pages extend from this (directly or via abstract templates)

2. **Abstract Templates** (extend base.html):
   - `detail_page.html` - For team/person/comparison detail views
     - Blocks: `page_title`, `header_title`, `header_subtitle`, `additional_nav`, `main_content`
   - `landing_page.html` - For hero-style overview pages
     - Blocks: `page_title`, `hero_title`, `hero_subtitle`, `hero_meta`, `main_content`
   - `content_page.html` - For static content pages
     - Blocks: `page_title`, `header_title`, `header_subtitle`, `main_content`

3. **Concrete Templates** (extend abstract templates):
   - `teams_overview.html` extends `landing_page.html`
   - `team_dashboard.html` extends `detail_page.html`
   - `person_dashboard.html` extends `detail_page.html`
   - `comparison.html` extends `detail_page.html`
   - `team_members_comparison.html` extends `detail_page.html`
   - `documentation.html` extends `content_page.html`

**Hamburger Menu:**
- Pure CSS implementation (checkbox hack, no extra JavaScript)
- Fixed position top-right (50x45px, prominent blue background)
- Slide-out overlay from right side (300px width)
- Contains: Home link, Documentation link, Theme toggle button
- Auto-closes on link click or outside click
- Responsive: 250px on tablet, 80% width on mobile
- Styles: `src/dashboard/static/css/hamburger.css`

**Semantic Chart Colors** (`src/dashboard/static/js/charts.js`):
```javascript
const CHART_COLORS = {
    CREATED: '#e74c3c',      // Red - items added/created
    RESOLVED: '#2ecc71',     // Green - items completed/closed
    NET: '#3498db',          // Blue - difference/net change
    TEAM_PRIMARY: '#3498db',
    TEAM_SECONDARY: '#9b59b6',
    PRS: '#3498db',
    REVIEWS: '#9b59b6',
    COMMITS: '#27ae60',
    JIRA_COMPLETED: '#f39c12',
    JIRA_WIP: '#e74c3c',
    PIE_PALETTE: ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']
};
```
- Consistent across all charts: Bugs trend, Scope trend, throughput pies
- `getChartColors()` function provides theme-aware background/text colors

**Theme System**:
- CSS variables in `main.css` for light/dark modes
- `data-theme` attribute on `<html>` element controls theme
- `theme-toggle.js` handles switching and localStorage persistence

**Chart Rendering**:
- Plotly.js for interactive charts
- Theme-aware colors injected at render time
- Charts use fixed dimensions for consistency (e.g., 450px width in comparison view)

**Export Buttons:**
- Located at top of detail pages (team, person, comparison, team members)
- Two buttons per page: CSV and JSON
- Styles: `src/dashboard/static/css/main.css` (`.btn-export`, `.export-buttons`)
- Routes: 8 export endpoints in `src/dashboard/app.py` (lines 1004-1259)
- Button placement: After breadcrumbs, before main content
- Responsive: Right-aligned on desktop, full-width on mobile

**Key UI Patterns**:
- Cards use `var(--bg-secondary)` for theme-aware backgrounds
- Charts detect theme: `document.documentElement.getAttribute('data-theme')`
- Jira filter links constructed from team config + server URL
- Export buttons use `download` attribute for automatic file downloads
- Export routes return proper Content-Disposition headers

## Important Implementation Details

### Jira Integration
- Uses **Bearer token** authentication (not username/password)
- SSL verification disabled (`verify_ssl=False`) for self-signed certificates
- Filter IDs are specific to each Jira instance - use `list_jira_filters.py` to discover
- Filters define team metrics (WIP, bugs, throughput, etc.)

**Jira Query Optimization (Anti-Noise Filtering):**
- Person queries filter `updated >= -90d` to only apply to non-Done tickets
- Query: `assignee = "user" AND (created >= -90d OR resolved >= -90d OR (statusCategory != Done AND updated >= -90d))`
- **Rationale**: Prevents bulk administrative updates (e.g., mass label changes) from polluting results with thousands of closed tickets
- Only captures actual work: new issues, resolved issues, and active WIP (not closed items with label updates)
- See `src/collectors/jira_collector.py:60` (project query) and `:195` (person query)

**Known Jira Library Limitations:**

*Issue Fetching Bug (Fixed in Code):*
The Jira Python library (v3.x) has a bug when using `fields='key'` parameter in `search_issues()`. When iterating over Fix Version data, the library encounters malformed issue data and throws:
```
TypeError: argument of type 'NoneType' is not iterable
  at jira/client.py:3686 in search_issues
  if k in iss.raw.get("fields", {}):
```

*Workaround (Already Implemented):*
In `src/collectors/jira_collector.py`, the `_get_issues_for_version()` method omits the `fields` parameter:

```python
# Fetch all fields instead of just 'key' to avoid library bug
issues = self.jira.search_issues(jql, maxResults=1000)
```

*Trade-off:* Fetches ~10-15 fields per issue instead of 1, slightly increasing API response size. However, this ensures stability and prevents collection failures.

*Commit:* 6451da5 (Jan 13, 2026)

### Export Functionality

The dashboard provides CSV and JSON export capabilities for all major pages:

**8 Export Routes** (CSV/JSON pairs for 4 page types):
- Team: `/api/export/team/<team_name>/csv` and `/json`
- Person: `/api/export/person/<username>/csv` and `/json`
- Comparison: `/api/export/comparison/csv` and `/json`
- Team Members: `/api/export/team-members/<team_name>/csv` and `/json`

**Helper Functions** (`src/dashboard/app.py` lines 891-997):
- `flatten_dict()` - Recursively flattens nested dictionaries with dot notation
- `format_value_for_csv()` - Formats values (rounds floats, formats dates, handles None)
- `create_csv_response()` - Generates CSV with proper headers and UTF-8 encoding
- `create_json_response()` - Generates JSON with datetime handling and pretty-printing

**Export Formats**:
- **CSV**: Flattened structure with dot notation (e.g., `github.pr_count`, `jira.wip.count`)
  - Uses `csv.DictWriter` for consistent formatting
  - Handles special characters (commas, quotes) properly
  - UTF-8 encoded for international characters
- **JSON**: Nested structure preserving full data hierarchy
  - Includes metadata (export timestamp, date range info)
  - Pretty-printed with `indent=2` for readability
  - Datetime objects converted to ISO format strings

**Filenames**: Descriptive with entity name and format:
- `team_native_metrics.csv`
- `person_jdoe_metrics.json`
- `team_comparison_metrics.csv`
- `team_native_members_comparison.json`

**HTTP Headers**:
```python
Content-Type: text/csv; charset=utf-8  # or application/json
Content-Disposition: attachment; filename="team_metrics.csv"
```

**Error Handling**:
- Returns 404 if team/person not found
- Returns 404 if no cache data available
- Returns 500 with error message if export fails
- All errors logged for debugging

**Testing**: 18 comprehensive tests in `tests/dashboard/test_app.py`:
- CSV/JSON export for all 4 page types (8 tests)
- Not found handling (2 tests)
- No cache handling (1 test)
- Helper function tests (2 tests)
- Settings routes (5 tests)

### DORA Metrics: How Releases Are Counted

**Release Source**: Uses Jira Fix Versions instead of GitHub Releases for deployment tracking.

**Accurate Counting Logic** (`jira_collector.py:649-758`):

The system counts releases using three filtering mechanisms to ensure accurate DORA metrics:

**1. Version Release Status Check**:
```python
# Only count versions that are actually released (not planned/future)
if not getattr(version, 'released', False):
    continue  # Skip unreleased versions

# Also check releaseDate must be in the past
release_date = getattr(version, 'releaseDate', None)
if release_date:
    release_dt = datetime.strptime(release_date, '%Y-%m-%d')
    if release_dt > now:
        continue  # Skip future releases
```

**2. Pattern Matching**:
- Supported formats:
  - `"Live - 6/Oct/2025"` → production deployment
  - `"Beta - 15/Jan/2026"` → staging deployment
  - `"Website - 26/Jan/2012"` → production deployment
  - `"Preview - 20/Jan/2026"` → staging/preview
  - `"RA_Web_2025_11_25"` → production (LENS8 project format)
- Pattern parsing in `_parse_fix_version_name()` (lines 760-846)

**3. Team Member Filtering**:
```python
# Only count issues worked on by team members
jql = f'project = {key} AND fixVersion = "{version}" AND '
jql += f'(assignee in ({team_members}) OR reporter in ({team_members}))'
```

**Why This Matters**:
- **Without filtering**: Inflated metrics (2-3x higher than reality)
- **With filtering**: Accurate team-specific metrics
- Example: Native team went from 31 → 24 deployments (23% reduction) after applying filters

**Team-Specific Collection** (`collect_data.py:441-461`):
- Each team gets a dedicated `JiraCollector` instance with `team_members` parameter
- Ensures cross-team releases are counted separately per team
- Only issues assigned to/reported by team members count toward that team's release

**Logging**:
```
🚀 Collecting releases from Jira Fix Versions for Native Team...
  Found 2414 versions in project RSC
  ✓ Matched 24 released versions
    (Skipped 1229 non-matching versions)
    (Skipped 538 unreleased versions)
    (Skipped 611 old versions)
  Total releases collected: 24
    Production: 20
    Staging: 4
```

**Expected Impact on DORA Metrics**:
- Deployment Frequency: 50-70% reduction from inflated values to accurate baseline
- Lead Time: More accurate as only team's actual work is considered
- Typical realistic values: 0.5-2.0 deployments/week per team

**See Also**: `docs/JIRA_FIX_VERSION_TROUBLESHOOTING.md` for detailed troubleshooting

### Cache Management
- Pickle format: `{'teams': {...}, 'persons': {...}, 'comparison': {...}, 'timestamp': datetime}`
- Dashboard checks cache age (default: 60 min) before auto-refresh
- Manual refresh via button or `/api/refresh` endpoint

### Data Processing Pipeline
1. Raw data collected as lists of dicts
2. Converted to pandas DataFrames in `MetricsCalculator`
3. Aggregated into structured metrics dictionaries
4. Cached to disk
5. Loaded by Flask and passed to Jinja templates

## Debugging

**GitHub API Issues**:
```bash
# Check GraphQL rate limit
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.github.com/rate_limit
```

**Jira Authentication**:
```bash
# Test Jira connection
curl -H "Authorization: Bearer YOUR_TOKEN" -k \
  https://jira.yourcompany.com/rest/api/2/serverInfo
```

**Cache Issues**:
- Delete `data/metrics_cache.pkl` to force fresh collection
- Check Flask logs for cache load errors

## Common Modifications

**Adding a new metric**:
1. Add collection in `GitHubGraphQLCollector._fetch_*()` or `JiraCollector`
2. Add calculation in `MetricsCalculator.calculate_*_metrics()`
3. Update template to display (e.g., `team_dashboard.html`)
4. Re-run `collect_data.py` to regenerate cache

**Adding a new team**:
1. Add team block to `config/config.yaml`
2. Use `list_jira_filters.py` to find filter IDs
3. Run `collect_data.py` to collect team data
4. Team automatically appears in dashboard

## Date Range Utilities

The `src/utils/date_ranges.py` module provides flexible date range parsing:
- `parse_date_range(range_str)` - Parses range string into start/end dates
- `get_cache_filename(range_key)` - Returns appropriate cache filename
- `get_preset_ranges()` - Returns list of preset range options

Supported formats:
- Days: `30d`, `60d`, `90d`, `180d`, `365d`
- Quarters: `Q1-2025`, `Q2-2024`, `Q3-2023`, `Q4-2026`
- Years: `2024`, `2025`, `2023`
- Custom: `YYYY-MM-DD:YYYY-MM-DD` (e.g., `2024-01-01:2024-12-31`)

## Time Periods

**Flexible Date Range Support**:
- Team metrics: Configurable via `--date-range` parameter
- Person metrics: Configurable via `--date-range` parameter
- Jira metrics: Adjusted to match selected date range

### Date Range Selection

The system supports multiple date range formats:
- **Days**: `30d`, `60d`, `90d`, `180d`, `365d`
- **Quarters**: `Q1-2025`, `Q2-2024`, `Q3-2023`, `Q4-2026`
- **Years**: `2024`, `2025`, `2023`
- **Custom**: `YYYY-MM-DD:YYYY-MM-DD` (e.g., `2024-01-01:2024-12-31`)

### Dashboard Date Range Selection

The dashboard includes a date range selector in the hamburger menu (☰) with preset options. The selected range persists across navigation via the `?range=` URL parameter.

### Cache File Management

Each date range creates a separate cache file:
- `metrics_cache_30d.pkl` - 30-day data
- `metrics_cache_90d.pkl` - 90-day data (default)
- `metrics_cache_180d.pkl` - 180-day data
- etc.

This allows switching between ranges without re-collecting data.
