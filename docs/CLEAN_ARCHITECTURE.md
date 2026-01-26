# Clean Architecture - Team Metrics Dashboard

**Version:** 1.0
**Last Updated:** 2026-01-26
**Status:** Phases 1-2 Complete, Phase 3 In Progress

---

## Quick Reference

### Four Layers
1. **Presentation** (`blueprints/`) → HTTP, templates, routing
2. **Application** (`services/`) → Use cases, orchestration, DI
3. **Domain** (`models/`) → Business logic (pure Python)
4. **Infrastructure** (`collectors/`, `utils/`) → APIs, external services

### Dependency Rule
```
Presentation → Application → Domain
                ↓
         Infrastructure → Domain (models only)
```

**Key Principle:** Dependencies point inward. Domain has NO dependencies.

---

## Layer Diagrams

### Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│            (User Interface & HTTP Handling)                 │
│                                                             │
│  • Flask Blueprints (dashboard.py, api.py, export.py)      │
│  • Jinja2 Templates (*.html)                               │
│  • Static Assets (CSS, JS)                                 │
│  • Request/Response Formatting                             │
│                                                             │
│  Dependencies: ✅ Application Layer                         │
│               ❌ Domain, Infrastructure                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ current_app.container.get("service")
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   APPLICATION LAYER                         │
│            (Business Use Cases & Services)                  │
│                                                             │
│  • Services (cache_service.py, metrics_refresh_service.py) │
│  • ServiceContainer (dependency injection)                 │
│  • Cache Backends (FileBackend, MemoryBackend)             │
│  • Eviction Policies (LRU, TTL)                            │
│  • Use Case Orchestration                                  │
│                                                             │
│  Dependencies: ✅ Domain, Infrastructure                    │
│               ❌ Presentation                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Uses models for calculations
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     DOMAIN LAYER                            │
│            (Business Logic - Pure Python)                   │
│                                                             │
│  • MetricsCalculator (metrics.py)                          │
│  • DORAMetrics (dora_metrics.py)                           │
│  • JiraMetrics (jira_metrics.py)                           │
│  • PerformanceScorer (performance_scoring.py)              │
│  • Pure functions, no side effects                         │
│                                                             │
│  Dependencies: ❌ NONE (pure logic only)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Models used by (inverted dependency)
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                        │
│            (External Services & Utilities)                  │
│                                                             │
│  • GitHubGraphQLCollector (GitHub API client)              │
│  • JiraCollector (Jira REST API client)                    │
│  • Config (configuration loading)                          │
│  • Utils (date_ranges, logging, repo_cache)                │
│                                                             │
│  Dependencies: ✅ Domain (models only), External libs       │
│               ❌ Presentation, Application                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. Presentation Layer
**Location:** `src/dashboard/blueprints/`, `templates/`, `static/`

#### What It Does
- Handles HTTP requests and responses
- Routes URLs to handlers
- Renders Jinja2 templates
- Validates user input
- Manages sessions and auth
- Formats data for display

#### What It Contains
```
src/dashboard/
├── blueprints/
│   ├── dashboard.py     # Team/person view routes
│   ├── api.py           # REST API endpoints
│   ├── export.py        # CSV/JSON export routes
│   └── settings.py      # Configuration UI routes
├── templates/
│   ├── base.html        # Base template
│   ├── team_dashboard.html
│   └── person_dashboard.html
└── static/
    ├── css/
    └── js/
```

#### Example Code
```python
# blueprints/dashboard.py
from flask import Blueprint, current_app, render_template

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/team/<team_name>")
@require_auth
def team_dashboard(team_name):
    # Get service from container (dependency injection)
    cache_service = current_app.container.get("cache_service")
    config = current_app.container.get("config")

    # Load data via service (Application Layer)
    cache_data = cache_service.load_cache("90d", "prod")

    # Render template (Presentation Layer)
    return render_template("team_dashboard.html",
                          team=team_name,
                          data=cache_data,
                          config=config)
```

#### Rules
- ✅ Can import: Application Layer services via DI container
- ❌ Cannot import: Domain models, Infrastructure collectors directly
- ✅ Access services: `current_app.container.get("service_name")`
- ❌ No business logic: Delegate to Application Layer

---

### 2. Application Layer
**Location:** `src/dashboard/services/`

#### What It Does
- Orchestrates use cases
- Coordinates multiple services
- Manages transactions
- Implements caching strategies
- Provides dependency injection

#### What It Contains
```
src/dashboard/services/
├── service_container.py          # DI container
├── cache_service.py               # Legacy cache
├── enhanced_cache_service.py      # Two-tier cache
├── cache_backends.py              # File/Memory backends
├── cache_protocols.py             # Interfaces
├── eviction_policies.py           # LRU, TTL policies
└── metrics_refresh_service.py     # Refresh orchestration
```

#### Example Code
```python
# services/metrics_refresh_service.py
from src.models.metrics import MetricsCalculator  # Domain
from src.collectors.github_graphql_collector import GitHubGraphQLCollector  # Infrastructure

class MetricsRefreshService:
    """Orchestrates metrics refresh across collectors"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def refresh_metrics(self):
        # Step 1: Coordinate infrastructure (collectors)
        github_collector = GitHubGraphQLCollector(
            token=self.config.github_token,
            organization=self.config.github_organization
        )
        jira_collector = JiraCollector(...)

        # Step 2: Collect raw data
        github_data = github_collector.collect_all_metrics()
        jira_data = jira_collector.collect_all_issues()

        # Step 3: Use domain logic (calculations)
        calculator = MetricsCalculator()
        metrics = calculator.calculate_team_metrics(github_data, jira_data)

        # Step 4: Cache results
        self._save_to_cache(metrics)

        return metrics
```

#### Rules
- ✅ Can import: Domain models, Infrastructure services
- ❌ Cannot import: Presentation Layer
- ✅ Orchestration: Coordinate Domain + Infrastructure
- ✅ Side effects: OK (I/O, caching, logging)

---

### 3. Domain Layer
**Location:** `src/models/`

#### What It Does
- Implements business rules
- Performs calculations
- Enforces domain logic
- Pure functions (no side effects)

#### What It Contains
```
src/models/
├── __init__.py
├── metrics.py                 # MetricsCalculator (main orchestrator)
├── dora_metrics.py            # DORA four key metrics
├── jira_metrics.py            # Jira-specific metrics
└── performance_scoring.py      # Performance score algorithm
```

#### Example Code
```python
# models/dora_metrics.py
from datetime import datetime
from typing import List, Dict, Optional

class DORAMetrics:
    """Pure business logic for DORA metrics"""

    @staticmethod
    def calculate_lead_time(prs: List[Dict], releases: List[Dict]) -> Optional[float]:
        """Calculate median lead time for changes

        Pure function: Takes data, returns number, no side effects.

        Args:
            prs: List of pull request dicts with merged_at, key fields
            releases: List of release dicts with date, fixes fields

        Returns:
            Median lead time in hours, or None if no matches
        """
        lead_times = []

        for pr in prs:
            # Business rule: Find release containing this PR
            release = DORAMetrics._find_matching_release(pr, releases)
            if not release:
                continue

            # Business calculation: Time from merge to release
            merge_date = datetime.fromisoformat(pr["merged_at"])
            release_date = datetime.fromisoformat(release["date"])
            lead_time_hours = (release_date - merge_date).total_seconds() / 3600

            lead_times.append(lead_time_hours)

        # Business rule: Use median (not mean) for robustness
        return statistics.median(lead_times) if lead_times else None
```

#### Rules
- ✅ Pure Python: Standard library only
- ❌ No imports: From other layers (Presentation, Application, Infrastructure)
- ❌ No side effects: No I/O, no logging, no caching
- ✅ Testable: Easy unit tests, no mocks needed
- ✅ Inject dependencies: Pass via parameters if needed

---

### 4. Infrastructure Layer
**Location:** `src/collectors/`, `src/utils/`, `src/config.py`

#### What It Does
- Integrates with external APIs
- Handles file I/O
- Manages configuration
- Provides utility functions

#### What It Contains
```
src/
├── collectors/
│   ├── github_graphql_collector.py  # GitHub API client
│   └── jira_collector.py            # Jira REST API client
├── utils/
│   ├── date_ranges.py               # Date parsing utilities
│   ├── logging/                     # Logging setup
│   ├── jira_filters.py              # Jira filter utilities
│   └── repo_cache.py                # Repository caching
└── config.py                        # Config file loading
```

#### Example Code
```python
# collectors/github_graphql_collector.py
import requests
from typing import List, Dict

class GitHubGraphQLCollector:
    """Infrastructure: GitHub API client"""

    def __init__(self, token: str, organization: str, days_back: int = 90):
        self.token = token
        self.organization = organization
        self.days_back = days_back
        self.api_url = "https://api.github.com/graphql"

    def collect_pull_requests(self, repos: List[str]) -> List[Dict]:
        """Fetch PRs from GitHub API

        Infrastructure concern: External API calls, error handling, rate limiting.
        """
        query = self._build_graphql_query(repos)

        # External API call
        response = requests.post(
            self.api_url,
            json={"query": query},
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30
        )

        # Error handling (infrastructure concern)
        if response.status_code != 200:
            raise APIError(f"GitHub API returned {response.status_code}")

        # Parse and return raw data
        return self._parse_response(response.json())
```

#### Rules
- ✅ Can import: Domain models (for types), External libraries
- ❌ Cannot import: Presentation, Application
- ✅ Side effects: OK (API calls, file I/O)
- ✅ Error handling: Handle external failures gracefully

---

## Dependency Injection Pattern

### Registration (in create_app)
```python
# src/dashboard/app.py
def create_app():
    container = ServiceContainer()

    # Register services with dependencies
    container.register("config", lambda c: Config())
    container.register("logger", lambda c: get_logger("dashboard"))

    container.register("cache_service", lambda c: EnhancedCacheService(
        data_dir=c.get("data_dir"),
        backend=c.get("cache_backend"),
        eviction_policy=c.get("eviction_policy"),
        logger=c.get("logger")
    ))

    container.register("refresh_service", lambda c: MetricsRefreshService(
        config=c.get("config"),
        logger=c.get("logger")
    ))

    app.container = container
    return app
```

### Usage (in blueprints)
```python
# blueprints/api.py
@api_bp.route("/refresh")
def refresh():
    # Get service from container
    refresh_service = current_app.container.get("refresh_service")

    # Use service
    result = refresh_service.refresh_metrics()
    return jsonify(result)
```

### Testing (with mocks)
```python
# tests/test_api.py
def test_refresh_endpoint():
    # Create mock service
    mock_refresh = Mock(spec=MetricsRefreshService)
    mock_refresh.refresh_metrics.return_value = {"success": True}

    # Override in container
    app.container.override("refresh_service", mock_refresh)

    # Test
    with app.test_client() as client:
        response = client.post("/api/refresh")
        assert response.status_code == 200
        mock_refresh.refresh_metrics.assert_called_once()
```

---

## Best Practices

### 1. Adding New Features

**Step 1: Identify the correct layer**
```
Does it handle HTTP?              → Presentation (blueprint)
Does it orchestrate services?     → Application (service)
Does it contain business logic?   → Domain (model)
Does it call external APIs?       → Infrastructure (collector/util)
```

**Step 2: Follow dependency rules**
- Only import from allowed layers
- Use DI container for cross-layer access
- Keep Domain pure (no imports)

**Step 3: Write tests**
- Unit tests for Domain (pure functions)
- Integration tests for Application (mock infrastructure)
- E2E tests for Presentation (full stack)

### 2. When to Use Each Layer

| Task | Layer | Why |
|------|-------|-----|
| Add new route | Presentation | HTTP handling |
| Calculate DORA metric | Domain | Business logic |
| Refresh metrics | Application | Orchestration |
| Call GitHub API | Infrastructure | External service |
| Format date for display | Presentation | View formatting |
| Cache management | Application | Cross-cutting concern |
| Validate business rule | Domain | Core logic |
| Load configuration | Infrastructure | External resource |

### 3. Common Mistakes

❌ **Wrong:** Presentation calls Infrastructure directly
```python
# blueprints/dashboard.py (WRONG)
from src.collectors.github_graphql_collector import GitHubGraphQLCollector

@dashboard_bp.route("/data")
def get_data():
    collector = GitHubGraphQLCollector(...)  # Direct infrastructure access
    data = collector.collect()
    return jsonify(data)
```

✅ **Right:** Presentation uses Application service
```python
# blueprints/dashboard.py (CORRECT)
@dashboard_bp.route("/data")
def get_data():
    service = current_app.container.get("metrics_service")  # Via DI
    data = service.collect_metrics()
    return jsonify(data)
```

❌ **Wrong:** Domain imports utilities
```python
# models/dora_metrics.py (WRONG)
from src.utils.date_ranges import parse_date  # External dependency

class DORAMetrics:
    def calculate_lead_time(self, pr_date_str: str):
        date = parse_date(pr_date_str)  # Domain depends on utils
```

✅ **Right:** Caller parses dates, Domain receives pure data
```python
# models/dora_metrics.py (CORRECT)
class DORAMetrics:
    def calculate_lead_time(self, pr_date: datetime):  # Accept parsed date
        # Pure calculation, no dependencies
```

---

## Current Status

### ✅ Compliant
- Enhanced cache service (Application Layer)
- ServiceContainer (Application Layer)
- Blueprints use container for services
- Domain models are pure Python

### ⚠️ Violations (To Be Fixed)
1. Some blueprints may import collectors directly
2. Some models may import from utils
3. app.py mixes Application and Presentation concerns

### 📋 Next Steps
1. Create ADRs documenting architecture decisions
2. Analyze and document all violations
3. Add import-linter to enforce rules
4. Fix violations gradually

---

## Related Documentation

- `docs/PHASE2_APPLICATION_FACTORY.md` - Dependency injection implementation
- `docs/ARCHITECTURE_ROADMAP.md` - Long-term architecture plan
- `docs/adr/` - Architecture Decision Records (coming soon)

---

**Last Updated:** 2026-01-26 by Claude
