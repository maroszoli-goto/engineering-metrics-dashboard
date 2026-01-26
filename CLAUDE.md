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
# Collect metrics with flexible date ranges (6 essential ranges)
python collect_data.py --date-range 90d     # Last 90 days (default)
python collect_data.py --date-range 30d     # Last 30 days
python collect_data.py --date-range 60d     # Last 60 days
python collect_data.py --date-range 180d    # Last 6 months
python collect_data.py --date-range 365d    # Last year
python collect_data.py --date-range 2025    # Previous year (for annual reviews)

# Multi-environment collection
python collect_data.py --date-range 90d --env uat   # Collect from UAT
python collect_data.py --date-range 90d --env prod  # Collect from production

# Set default environment via variable
export TEAM_METRICS_ENV=uat
python collect_data.py --date-range 90d  # Uses UAT

# List available Jira filters (utility to find filter IDs)
python list_jira_filters.py
```

**Note**: Each collection creates a separate cache file (e.g., `metrics_cache_90d.pkl`, `metrics_cache_90d_uat.pkl`) allowing you to switch between date ranges AND environments in the dashboard without re-collecting data.

**Automated Collection**: The `scripts/collect_data.sh` script automatically collects all 6 ranges (30d, 60d, 90d, 180d, 365d, previous year) in 2-4 minutes. See `docs/COLLECTION_CHANGES.md` for details on recent simplification from 15+ ranges.

### Performance Optimizations

The system includes multiple automatic optimizations for 5-6x faster data collection:

1. **Parallel Collection** - Teams (3 workers), repos (5 workers), persons (8 workers), Jira filters (4 workers)
2. **Connection Pooling** - Reuses HTTP connections (5-10% speedup, automatic)
3. **Repository Caching** - Caches team repo lists for 24 hours (5-15s saved, automatic)
4. **GraphQL Query Batching** - Combines PRs and Releases queries (20-40% speedup, 50% fewer API calls, automatic)

**Configuration** (`config/config.yaml`):
```yaml
parallel_collection:
  enabled: true           # Master switch (set false to troubleshoot)
  person_workers: 8
  team_workers: 3
  repo_workers: 5         # Reduce to 3-4 if hitting GitHub rate limits
  filter_workers: 4       # Reduce to 2-3 if Jira timeouts occur
```

**Cache Management**:
```bash
python scripts/clear_repo_cache.py  # Clear repo cache if team repos change
```

See implementation in `src/collectors/github_graphql_collector.py` and `src/utils/repo_cache.py`.

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

### Switching Environments in Dashboard
```bash
# Access specific environment via URL
http://localhost:5001/?env=uat&range=90d
http://localhost:5001/?env=prod&range=30d

# Or use the environment selector in hamburger menu:
#   1. Click hamburger icon (top-left)
#   2. Select environment from "🌍 Environment" dropdown
#   3. Page reloads with selected environment data

# Environment badge shows current environment:
#   ⚠️ UAT - User Acceptance Testing environment
#   ✅ PROD - Production environment
```

**Cache Files:**
- Format: `metrics_cache_{range}_{env}.pkl`
- Examples: `metrics_cache_90d_uat.pkl`, `metrics_cache_30d_prod.pkl`
- Each environment maintains separate cache files

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

### Dashboard Authentication

**New**: Optional HTTP Basic Authentication for securing the dashboard.

```bash
# Generate password hash
python scripts/generate_password_hash.py

# Add to config.yaml:
# dashboard:
#   auth:
#     enabled: true
#     users:
#       - username: admin
#         password_hash: pbkdf2:sha256:...

# Restart dashboard - all routes now require authentication
```

**Features:**
- Disabled by default (backward compatible)
- PBKDF2-SHA256 password hashing
- All 21 routes protected when enabled
- Multiple user support
- Zero overhead when disabled

**See:** `docs/AUTHENTICATION.md` for complete guide

### Performance Monitoring

**New**: Performance monitoring system for tracking route and API call timing.

```bash
# Performance logs are automatically written to logs/team_metrics.log
# Analysis tool to identify bottlenecks
python tools/analyze_performance.py logs/team_metrics.log

# Show only routes
python tools/analyze_performance.py logs/team_metrics.log --type route

# Show top 5 slowest operations with histograms
python tools/analyze_performance.py logs/team_metrics.log --top 5 --histogram
```

**Instrumented Components:**
- All 21 dashboard routes (`@timed_route` decorator)
- GitHub collector methods (GraphQL queries, repository collection)
- Jira collector methods (pagination, filter collection)

**See:** `docs/PERFORMANCE.md` for complete documentation

### Testing
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests (903 tests, all passing)
# Execution time: ~58 seconds
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest tests/unit/test_jira_metrics.py -v

# Run tests matching pattern
pytest -k "test_lead_time" -v

# Generate HTML coverage report
pytest --cov --cov-report=html
open htmlcov/index.html

# Run fast tests only (exclude slow integration tests)
pytest -m "not slow"

# Validate Clean Architecture (import-linter)
lint-imports
```

**Test Organization:**
- `tests/unit/` - Pure logic and utility function tests (90%+ coverage target)
  - `test_jira_metrics.py` - 26 tests for Jira metrics processing (NEW)
  - `test_dora_metrics.py` - 39 tests for DORA metrics & trends (EXPANDED)
  - `test_dora_trends.py` - 13 tests for DORA trend calculations
  - `test_performance_score.py` - 19 tests for performance scoring
  - `test_config.py` - 27 tests for configuration validation
  - `test_metrics_calculator.py` - 44 tests for metrics calculations (EXPANDED)
- `tests/integration/` - End-to-end workflow tests (52 tests)
  - `test_dora_lead_time_mapping.py` - 19 tests for PR→Jira→Release mapping
  - `test_github_collection_workflows.py` - 21 tests for GitHub collector workflows (NEW)
  - `test_jira_collection_workflows.py` - 17 tests for Jira collector workflows (NEW)
  - `test_metrics_orchestration.py` - 14 tests for metrics orchestration (NEW)
- `tests/collectors/` - API response parsing tests (35%+ coverage target)
  - `test_github_graphql_collector.py` - 27 tests for GitHub GraphQL API (EXPANDED)
  - `test_github_graphql_simple.py` - 15 tests for GraphQL data extraction (NEW)
  - `test_jira_collector.py` - 27 tests for Jira collector (EXPANDED)
  - `test_jira_pagination.py` - 14 tests for Jira pagination strategies (NEW)
  - `test_jira_fix_versions.py` - 6 tests for fix version parsing (NEW)
- `tests/fixtures/` - Mock data generators for consistent test data
- `tests/conftest.py` - Shared pytest fixtures

**Coverage Status:**
| Module | Target | Actual | Status |
|--------|--------|--------|--------|
| **jira_metrics.py** | **70%** | **94.44%** | **✅** |
| **dora_metrics.py** | **70%** | **90.54%** | **✅** |
| date_ranges.py | 80% | 96.39% | ✅ |
| performance_scoring.py | 85% | 97.37% | ✅ |
| metrics.py (orchestration) | 30% | 32.18% | ✅ |
| **github_graphql_collector.py** | **35%** | **63.09%** | **✅** |
| **jira_collector.py** | **35%** | **58.62%** | **✅** |
| **Overall Project** | **60%** | **77.03%** | **✅** |

*Note: Overall coverage (77%) reflects excellent coverage across all modules with comprehensive integration tests. All 903 tests passing. Recent improvements: +52 integration tests covering GitHub/Jira collectors and metrics orchestration workflows. Architecture contracts validated via import-linter (6 contracts enforced).

### Analysis Tools

Located in `tools/` directory. See `tools/README.md` for complete documentation.

**Quick Verification:**
```bash
# Verify collection completed successfully
./tools/verify_collection.sh
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
python tools/analyze_releases.py

# Show specific release details
python tools/analyze_releases.py "Native Team" "Live - 21/Oct/2025"
```

Shows:
- Release list with issue counts
- Production vs staging breakdown
- Issue mapping statistics
- Full DORA metrics (deployment frequency, lead time, CFR, MTTR)
- Related issues per release

**Command Reference:**
- `docs/ANALYSIS_COMMANDS.md` - Complete guide with Python snippets, log analysis commands, and verification checklist
- Includes manual cache inspection examples
- Expected results after bug fix
- Next steps for post-collection workflow

## Logging

**Dual-Mode Logging**: Automatically adapts to environment
- **Interactive** (terminal): Colorful emoji output with progress indicators
- **Background** (cron/launchd): Structured JSON logs for machine parsing

**Configuration**: `config/logging.yaml` (10MB rotation, 10 backups, gzip compression)

**Files**:
- `logs/team_metrics.log` - All activity (JSON format)
- `logs/team_metrics_error.log` - Errors/warnings only

**CLI Flags**:
```bash
python collect_data.py -v        # Verbose (DEBUG)
python collect_data.py -q        # Quiet (warnings/errors only)
python collect_data.py --log-file /path/to/log
```

**Implementation**: See `src/utils/logging/` modules. Thread-safe, auto-detects TTY, works with launchd services unchanged.

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
- `jira_collector.py` - Jira REST API with Bearer token authentication

**Models** (`src/models/`):
- `metrics.py` - `MetricsCalculator` class (605 lines)
  - Core orchestration and calculation methods
  - `calculate_team_metrics()` - Team-level aggregations with Jira filters
  - `calculate_person_metrics()` - Individual contributor metrics (90-day rolling window)
  - `calculate_team_comparison()` - Cross-team comparison data
  - Inherits from `DORAMetrics` and `JiraMetrics` mixins
- `dora_metrics.py` - `DORAMetrics` mixin class (635 lines)
  - DORA four key metrics (Deployment Frequency, Lead Time, CFR, MTTR)
  - Trend analysis and historical tracking
- `performance_scoring.py` - `PerformanceScorer` static class (270 lines)
  - Composite 0-100 performance scoring
  - Normalization and weighting utilities
  - Team size adjustments
- `jira_metrics.py` - `JiraMetrics` mixin class (226 lines)
  - Jira filter processing
  - Throughput, WIP, bug tracking
  - Scope trend analysis

**Configuration** (`src/config.py`):
- `Config` class loads from `config/config.yaml`
- Multi-team support with separate GitHub/Jira member lists per team
- Each team has Jira filter IDs for custom metrics

**Dashboard** (`src/dashboard/`) - **Modular Blueprint Architecture (Week 7-8 Refactoring)**:
- `app.py` - Flask app initialization (228 lines, down from 1,676 - 86% reduction)
- `auth.py` - HTTP Basic Authentication (153 lines)
- `blueprints/` - Modular route organization (4 files, 21 routes):
  - `__init__.py` - Blueprint registration and dependency injection (69 lines)
  - `api.py` - API routes: /api/metrics, /api/refresh (171 lines, 4 routes)
  - `dashboard.py` - Dashboard routes: /, /team, /person, /comparison (588 lines, 6 routes)
  - `export.py` - Export routes: CSV/JSON exports (361 lines, 8 routes)
  - `settings.py` - Settings routes: /settings (139 lines, 3 routes)
- `services/` - Business logic services (2 files, extracted Week 7):
  - `cache_service.py` - Cache management (213 lines)
  - `metrics_refresh_service.py` - Metrics refresh orchestration (156 lines)
- `utils/` - Reusable utilities (6 files, extracted Week 7):
  - `data.py` - Data manipulation (41 lines)
  - `data_filtering.py` - Date filtering (143 lines)
  - `error_handling.py` - Error utilities (48 lines)
  - `export.py` - Export helpers (132 lines)
  - `formatting.py` - Display formatting (93 lines)
  - `performance.py` - Performance monitoring (228 lines)
  - `validation.py` - Input validation (48 lines)
- `templates/` - Jinja2 templates with Plotly charts
  - `teams_overview.html` - Main dashboard (2-column grid)
  - `team_dashboard.html` - Team metrics with Jira integration
  - `person_dashboard.html` - Individual contributor view
  - `comparison.html` - Side-by-side team comparison with DORA metrics
- `static/css/main.css` - Theme CSS with dark mode variables
- `static/css/hamburger.css` - Hamburger menu styles with animations
- `static/js/theme-toggle.js` - Dark/light mode switcher
- `static/js/charts.js` - Shared chart utilities and CHART_COLORS constants

**See Also**: `docs/WEEKS7-8_REFACTORING_SUMMARY.md` for complete refactoring details

### Clean Architecture (Phase 3 - Completed 2026-01-26)

The codebase follows Clean Architecture with automated enforcement via import-linter.

**Layer Structure**:
```
Presentation (src/dashboard/blueprints/) → Application (src/dashboard/services/)
                                                ↓
                                          Domain (src/models/)
                                                ↑
                                    Infrastructure (src/collectors/, src/utils/)
```

**Dependency Rule**: Outer layers depend on inner layers. Domain layer is pure (no external dependencies).

**Key Principles**:
1. **Domain Layer Purity**: `src/models/` has zero infrastructure imports
   - Uses dependency injection for logger (optional)
   - Domain logic is portable and framework-agnostic
2. **Application Services**: `src/dashboard/services/` orchestrates use cases
   - Wraps Domain logic for Presentation layer
   - Examples: `TrendsService`, `MetricsRefreshService`, `CacheService`
3. **Presentation Isolation**: `src/dashboard/blueprints/` only accesses Application layer
   - Uses `current_app.logger` (Flask built-in) instead of infrastructure logging
   - No direct Domain imports
4. **Infrastructure Independence**: `src/collectors/`, `src/utils/` can only access Domain

**Automated Enforcement**:
```bash
# Validate architecture contracts (6 contracts enforced)
lint-imports

# Expected output:
# ✅ Domain layer must not import from other layers KEPT
# ✅ Presentation layer must not import Domain directly KEPT
# ✅ Presentation layer must not import Infrastructure KEPT
# ✅ Infrastructure must not import Presentation KEPT
# ✅ Infrastructure must not import Application services KEPT
# ✅ Application layer must not import Presentation KEPT
# Contracts: 6 kept, 0 broken.
```

**Architecture Metrics** (as of 2026-01-26):
- Total dependencies: 81
- Architecture violations: 0 critical
- Contracts enforced: 6
- Acceptable exceptions: 4 (performance monitoring decorator)

**Documentation**:
- **Clean Architecture Guide**: `docs/CLEAN_ARCHITECTURE.md`
- **Phase 3 Completion**: `docs/PHASE3_COMPLETION.md`
- **ADRs**: `docs/architecture/adr/` (4 architectural decision records)
- **CI/CD Fixes**: `docs/CI_CD_FIXES.md`
- **Blueprint Logging Fix**: `docs/BLUEPRINT_LOGGING_FIX.md`

**Recent Improvements (2026-01-26)**:
- ✅ Removed all logging imports from blueprints (use Flask's `current_app.logger`)
- ✅ Fixed CI/CD pipeline (added requirements-dev.txt, Python 3.9 compatibility)
- ✅ All 903 tests passing across Python 3.9-3.13
- ✅ 77% test coverage maintained
- ✅ Zero critical architecture violations

### Configuration Structure

See `config/config.example.yaml` for complete template. Key sections:

```yaml
github:
  token: "ghp_..."
  organization: "your-org"

jira:
  server: "https://jira.yourcompany.com"
  username: "username"  # NOT email
  api_token: "bearer_token"

teams:
  - name: "Backend"
    members:
      - name: "John Doe"
        github: "johndoe"
        jira: "jdoe"
    jira:
      filters:
        wip: 12345
        bugs: 12346
        incidents: 12347  # For DORA metrics

dashboard:
  port: 5001
  cache_duration_minutes: 60
  jira_timeout_seconds: 120

performance_weights:  # Optional - customize via Settings page
  prs: 0.15
  deployment_frequency: 0.10
  # ... (must sum to 1.0)
```

### Performance Scoring System

**Algorithm** (`src/models/performance_scoring.py:PerformanceScorer`):
- Composite 0-100 score using min-max normalization
- 10 metrics: PRs, reviews, commits, cycle time, merge rate, Jira completed, deployment frequency, lead time, CFR, MTTR
- Configurable weights via Settings page (http://localhost:5001/settings) or `config.yaml`
- Cycle time/lead time/CFR/MTTR inverted (lower is better)
- Team size normalization for fair per-capita comparison
- MetricsCalculator delegates to PerformanceScorer.calculate_performance_score()

### GitHub GraphQL Queries

**Benefits**: 50-70% fewer API calls, separate rate limit (5000 points/hour), single query for PRs+reviews+commits

**Queries**: See `src/collectors/github_graphql_collector.py:268-298` (PR query), `:118-134` (repository query)

Uses `CREATED_AT` ordering and cursor-based pagination for consistent results.

### Jira JQL Queries

**Anti-Noise Filtering** (`jira_collector.py:60`, `:195`):
- Queries include: `created >= -90d OR resolved >= -90d OR (statusCategory != Done AND updated >= -90d)`
- Prevents bulk admin updates (label changes) from including thousands of old closed tickets
- Only captures actual work: new issues, resolved issues, and active WIP

**Filter Queries**: Uses filter IDs from team config with dynamic time constraints (line 278)

**Time Windows**: Configurable via `--date-range` parameter (default: 90 days)

### Dashboard UI Features

- **Hamburger Menu**: Team links auto-generate from config/cache
- **Theme Toggle**: Dark/light mode with localStorage persistence
- **Date Range Selector**: Preset options with URL parameter persistence
- **Export**: 8 routes (CSV/JSON for team/person/comparison/team-members)
- **Reload Button**: Shows ⏳ during operation (`reloadCache()` in `theme-toggle.js`)

#### Date Range Display Pattern

All dashboard pages display the selected date range using the `date_range_info` context variable.

**Template Pattern**:
```jinja2
{% block period_info %}
{% if date_range_info and date_range_info.get('description') %}
📊 Viewing: {{ date_range_info.get('description') }}
{% else %}
📊 Default fallback text (e.g., "Last 90 days")
{% endif %}
{% endblock %}
```

**Available in Routes**: Automatically injected via context processor (`app.py:28-50`)

**Structure**:
- `description`: "Last 30 days", "Last 90 days", etc.
- `start_date`: datetime object
- `end_date`: datetime object
- `label`: "30d", "90d", etc.

**Used In**:
- `team_dashboard.html`
- `person_dashboard.html`
- `team_members_comparison.html`
- `comparison.html`

## UI Architecture

**3-Tier Template Inheritance**:
1. `base.html` - Master template (hamburger menu, footer, theme toggle)
2. Abstract templates - `detail_page.html`, `landing_page.html`, `content_page.html`
3. Concrete pages - Teams overview, team dashboard, person dashboard, comparison

**Styles & Components**:
- **Theme**: CSS variables in `main.css`, `data-theme` attribute, `theme-toggle.js`
- **Charts**: Plotly.js with semantic color palette (`charts.js`), theme-aware rendering
- **Hamburger Menu**: Pure CSS (checkbox hack), responsive, styles in `hamburger.css`

**Export**: 8 endpoints in `app.py` (lines 1004-1259), CSV/JSON formats with UTF-8 encoding

## Important Implementation Details

### Jira Integration
- Uses **Bearer token** authentication (not username/password)
- SSL verification disabled (`verify_ssl=False`) for self-signed certificates
- Filter IDs are specific to each Jira instance - use `list_jira_filters.py` to discover
- Filters define team metrics (WIP, bugs, throughput, etc.)

**Incident Filtering (Updated 2026-01-23):**
- Production incidents are identified **only by issue type**: `issuetype IN ("Incident", "GCS Escalation")`
- **No longer includes**: High-priority bugs, label-based filtering, or keyword matching
- **Rationale**: More accurate CFR/MTTR metrics by counting only true production incidents
- **Impact**: Users must update Jira incident filters to use explicit issue type matching
- See `docs/INCIDENT_FILTERING_CHANGE.md` for complete details and migration guide

**Jira Query Optimization (Anti-Noise Filtering):**
- Person queries filter `updated >= -90d` to only apply to non-Done tickets
- Query: `assignee = "user" AND (created >= -90d OR resolved >= -90d OR (statusCategory != Done AND updated >= -90d))`
- **Rationale**: Prevents bulk administrative updates (e.g., mass label changes) from polluting results with thousands of closed tickets
- Only captures actual work: new issues, resolved issues, and active WIP (not closed items with label updates)
- See `src/collectors/jira_collector.py:60` (project query) and `:195` (person query)

**Smart Adaptive Pagination (504 Timeout Fix):**

The system uses intelligent pagination to handle large Jira datasets and prevent 504 Gateway Timeout errors:

*Strategy*:
- **Count First**: Queries `maxResults=0` to determine total issue count
- **Adaptive Batching**:
  - <500 issues: Single batch with changelog
  - 500-2000: Batches of 500 with changelog
  - 2000-5000: Batches of 1000 with changelog
  - \>5000: Batches of 1000 WITHOUT changelog (prevents timeouts)
- **Retry Logic**: 3 retry attempts on 504/503/502 errors with 5s delay
- **Graceful Degradation**: Returns partial results if all retries fail
- **Progress Tracking**: Shows progress bars in interactive mode (auto-disabled for cron/launchd)

*Configuration* (`config.yaml`):
```yaml
jira:
  pagination:
    enabled: true                    # Master switch
    batch_size: 1000                 # Issues per API request
    huge_dataset_threshold: 0        # Disable changelog for ALL queries (0 = always disable)
    fetch_changelog_for_large: false # Force changelog for large datasets
    max_retries: 5                   # Retry attempts on timeout
    retry_delay_seconds: 5           # Base delay (exponential backoff)
```

**Threshold Values**:
- `0`: Disable changelog for ALL queries (recommended for large Jira instances with timeouts)
- `150-1000`: Disable changelog only for large result sets (better cycle time accuracy, but risk of timeouts)
- `5000`: Default value (changelog always enabled unless dataset is huge)

**Rationale for threshold: 0**:
The production config uses `0` to completely disable changelog fetching because:
- ✅ Eliminates all 504 timeout errors (100% reliability)
- ✅ Significantly faster collection (50-70% speedup)
- ⚠️ Trade-off: Less accurate cycle time calculations (no status transition history)
- ⚠️ DORA metrics (lead time, MTTR) still accurate (uses PR merge dates and release dates, not Jira changelog)

*Implementation*:
- Core method: `_paginate_search()` in `src/collectors/jira_collector.py:59-197`
- Replaces all 6 `search_issues()` calls: project issues, worklogs, person queries, filters, incidents, fix versions
- Handles missing changelog gracefully (line 276): Returns empty status times when changelog unavailable

*Trade-offs*:
- ✅ Eliminates 504 timeouts (100% person query success vs 0% before)
- ✅ No data truncation (fetches all issues vs hard limit of 1000)
- ✅ Automatic retry on transient failures
- ⚠️ Disabling changelog for huge datasets = less accurate cycle time (acceptable trade-off)
- ⚠️ 30-50% longer collection time (but 100% data completeness)

*Documentation*: See `docs/JIRA_PAGINATION_FIX.md` for complete implementation details, test results, and troubleshooting guide.

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

**Status Transition Metrics vs Cycle Time:**

When `huge_dataset_threshold: 0` is configured (changelog disabled for all queries):

**Affected Metrics (always return 0)**:
- `time_in_todo_hours` - Requires changelog for status history
- `time_in_progress_hours` - Requires changelog for status history
- `time_in_review_hours` - Requires changelog for status history

**Unaffected Metrics (still accurate)**:
- `cycle_time_days` - Uses `created` and `resolutiondate` field dates directly (not changelog)
- All DORA metrics - Use PR merge dates and release dates (not Jira changelog)
- Issue counts, throughput, WIP - Use field queries, not changelog
- Jira trend metrics - Respect user's selected date range for bugs/scope trends

**Trade-off**: Disabling changelog eliminates 504 timeouts but loses workflow visibility. For large Jira instances with >5000 issues, reliability is prioritized over status transition granularity.

**Date Range Consistency**: Jira trend calculations (bugs created/resolved, scope created/resolved) dynamically respect the user's selected date range (30d, 90d, 365d, etc.) instead of using a hardcoded 90-day window.

**Person Query Fallback**: When person queries timeout with the requested date range, the system attempts a 30-day fallback. A warning banner is displayed on the person dashboard when fallback occurs: "⚠️ Data limited to 30 days due to large dataset".

### Time Offset Consistency (Updated 2026-01-26)

**Purpose:** Aligns collection time windows when UAT databases are snapshots from the past.

**How It Works:**
- **Jira**: Queries database state from `time_offset_days` ago (e.g., 180 days = 6 months ago)
- **GitHub**: Queries current API but filters by dates from `time_offset_days` ago
  - NOTE: GitHub API returns current state only (no historical snapshots)
  - We filter PRs/releases/commits by old created_at/merged_at dates
  - This correctly retrieves data that existed 6 months ago

**Example** (time_offset_days: 180):
- Today: 2026-01-26
- Requested range: Last 90 days
- **Actual query dates**: 2024-05-03 to 2024-07-29 (270 days ago)
  - Jira: Queries UAT database (6 months old snapshot)
  - GitHub: Queries current API, filters by 6-month-old merge dates

**DORA Metrics Alignment:**
With time_offset_days configured correctly:
- ✅ PRs from 6 months ago match releases from 6 months ago
- ✅ Lead time calculation works (PR→Release mapping successful)
- ✅ CFR/MTTR show accurate historical data (incidents correlate to deployments)
- ✅ Deployment frequency aligned to UAT release schedule

**Configuration** (`config.yaml`):
```yaml
jira:
  environments:
    prod:
      server: "https://jira.company.com"
      time_offset_days: 0  # Production: current data
                          # NOTE: Applies to BOTH GitHub and Jira collectors
    uat:
      server: "https://jira-uat.company.com"
      time_offset_days: 180  # UAT: 6 months behind
                            # NOTE: Applies to BOTH GitHub and Jira collectors
```

**Why under jira.environments?** Although `time_offset_days` affects both collectors, it's configured here because:
1. Backward compatibility (maintains existing config structure)
2. Jira-driven use case (offset needed when Jira UAT is a database snapshot)
3. Single source of truth (not duplicated across sections)

**Prior to 2026-01-26:** time_offset_days only applied to Jira, causing DORA metric failures in UAT environments. See `docs/TIME_OFFSET_FIX.md` for complete details.

### Export Functionality

**Routes** (`src/dashboard/app.py:891-997`):
- Team, Person, Comparison, Team Members (CSV & JSON for each)
- Filenames include date: `team_native_metrics_2026-01-14.csv`

**Helpers**: `flatten_dict()`, `format_value_for_csv()`, `create_csv_response()`, `create_json_response()`

**Testing**: 18 tests in `tests/dashboard/test_app.py`

### DORA Metrics: How Releases Are Counted

**Release Source**: Uses Jira Fix Versions (not GitHub Releases) for deployment tracking.

**Three-Tier Filtering** (`jira_collector.py:649-758`):
1. **Status Check**: Only released versions (not planned/future), releaseDate in past
2. **Pattern Matching**: Supports `"Live - 6/Oct/2025"`, `"Beta - 15/Jan/2026"`, `"RA_Web_2025_11_25"` formats (see `_parse_fix_version_name()` lines 760-846)
3. **Team Member Filtering**: Only issues assigned to team members (assignee field only)

**Four-Tier Filtering for Lead Time** (`collect_data.py:449-457`):
4. **Cross-Team Filtering**: Releases with zero team-assigned issues are filtered out before metrics calculation
   - Prevents teams' PRs from matching against other teams' releases in time-based fallback
   - Example: Native team (8 releases) no longer matches against WebTC team releases (25+ filtered out)
   - Improves lead time accuracy from unrealistic values (1.5 days) to realistic values (7+ days)

**Why Filtering Matters**: Without filtering, metrics inflated 2-3x. Typical realistic values: 0.5-2.0 deployments/week per team.

**See Also**:
- `docs/JIRA_FIX_VERSION_TROUBLESHOOTING.md`
- `docs/LEAD_TIME_FIX_RESULTS.md` - Cross-team filtering implementation details

### Lead Time for Changes: How It's Calculated

**Measures**: Time from code commit (PR merge) to production deployment.

**Two-Method Approach** (Jira-based preferred, time-based fallback):

#### Method 1: Jira-Based Mapping (Preferred - Most Accurate)
Flow: PR → Jira Issue → Fix Version → Deployment

1. **Extract Issue Key from PR**:
   - Searches PR title: `"[RSC-123] Add feature"` → `RSC-123`
   - Searches branch name: `feature/RSC-123-add-feature` → `RSC-123`
   - Pattern: `([A-Z]+-\d+)`

2. **Map to Fix Version**:
   - Uses `issue_to_version_map` built during collection
   - Example: `RSC-123` → `"Live - 21/Oct/2025"`

3. **Calculate Lead Time**:
   ```
   Lead Time = Fix Version Date - PR Merged Date
   ```

#### Method 2: Time-Based Fallback
When Jira mapping unavailable:
- Finds next production deployment after PR merge
- Lead Time = Next Deployment - PR Merge
- **Cross-Team Filtering**: Only searches releases where the team has assigned issues (prevents contamination from other teams' releases)

**Release Workflow Support**:
Works with cherry-pick workflows:
- Feature branches merge to `master`: `feature/RSC-456-*` → `master`
- Release branches created later: `release/Rescue-7.55-AI`
- Commits cherry-picked: `master` → `release/Rescue-7.55-AI`
- Connection tracked through Jira Fix Versions (not git history)

**Performance Levels** (DORA standard):
- **Elite**: < 24 hours (< 1 day)
- **High**: < 168 hours (< 1 week)
- **Medium**: < 720 hours (< 1 month)
- **Low**: ≥ 720 hours (≥ 1 month)

#### Handling Missing DORA Metrics

DORA metrics may return `None` when insufficient data is available:

**When Metrics Return None**:
- **Lead Time**: No releases with mapped PRs in the date range
- **Change Failure Rate (CFR)**: No incidents filter configured OR no deployments in range
- **MTTR**: No incidents to resolve in the date range
- **Deployment Frequency**: No releases in the date range

**Template Handling**: Always check for `None` before formatting:
```jinja2
{% if comparison.Native.dora_lead_time is not none %}
  {{ "%.1f"|format(comparison.Native.dora_lead_time) }} hours
{% else %}
  <span style="color: var(--text-tertiary);">N/A</span>
{% endif %}
```

**Best Practices**:
- Use `is not none` (not `if value`) to avoid treating `0` as falsy
- Display "N/A" or similar placeholder instead of raw `None`
- Apply consistent styling (`--text-tertiary` color) for missing values
- Consider adding tooltips explaining why metric is unavailable

**Example from `comparison.html`**:
All DORA metric displays include None checks (see lines 180-220 in template).

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

## Date Ranges

**Recommended Ranges (Automated Collection)**:
- Days: `30d`, `60d`, `90d`, `180d`, `365d`
- Years: `2025` (previous year for annual reviews)

**Also Supported** (manual collection only):
- Quarters: `Q1-2025`, `Q2-2024`, `Q3-2023`, `Q4-2026`
- Any year: `2024`, `2025`, `2023`
- Custom: `YYYY-MM-DD:YYYY-MM-DD` (e.g., `2024-01-01:2024-12-31`)

**Cache Files**: Each range creates separate cache (`metrics_cache_90d.pkl`), allowing switching without re-collection.

**Dashboard Selector**: Preset options in hamburger menu, persists via `?range=` URL parameter.

**Implementation**: See `src/utils/date_ranges.py` for parsing utilities.

**Note**: Automated collection via `scripts/collect_data.sh` only collects the 6 recommended ranges for faster performance (2-4 min vs 5-10 min). See `docs/COLLECTION_CHANGES.md` for rationale.
