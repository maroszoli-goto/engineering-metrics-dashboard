# Developer Guide - Team Metrics Dashboard

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Common Development Tasks](#common-development-tasks)
5. [Blueprint Development](#blueprint-development)
6. [Testing Guidelines](#testing-guidelines)
7. [Code Quality Standards](#code-quality-standards)
8. [Git Workflow](#git-workflow)

---

## Architecture Overview

### High-Level Architecture

Team Metrics Dashboard follows a **3-tier architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                     Collectors Layer                     │
│  (GitHub GraphQL API + Jira REST API)                   │
│  ├── GitHubGraphQLCollector - Fetch PRs, reviews, etc  │
│  └── JiraCollector - Fetch issues, filters, etc        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                      Models Layer                        │
│  (Business Logic & Calculations)                        │
│  ├── MetricsCalculator - Core metrics orchestration    │
│  ├── DORAMetrics - DORA metrics calculations           │
│  ├── JiraMetrics - Jira metrics processing             │
│  └── PerformanceScorer - Performance scoring           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    Dashboard Layer                       │
│  (Flask Web Application)                                │
│  ├── Blueprints - Route handlers (21 routes)           │
│  ├── Services - Business logic (cache, refresh)        │
│  └── Utils - Reusable functions (format, validate)     │
└─────────────────────────────────────────────────────────┘
```

### Dashboard Architecture (Post Week 7-8 Refactoring)

The dashboard uses a **modular blueprint architecture**:

```
Flask App (app.py)
├── Blueprint Registration
│   ├── API Blueprint (/api/*)
│   ├── Dashboard Blueprint (/*)
│   ├── Export Blueprint (/api/export/*)
│   └── Settings Blueprint (/settings/*)
├── Service Layer
│   ├── CacheService
│   └── MetricsRefreshService
└── Utility Layer
    ├── Data utilities
    ├── Export utilities
    ├── Formatting utilities
    └── Validation utilities
```

**Key Principles:**
- **Single Responsibility**: Each module has one clear purpose
- **Dependency Injection**: Blueprints access shared services via `current_app.extensions`
- **Loose Coupling**: Blueprints don't directly import services
- **High Cohesion**: Related routes grouped in same blueprint

---

## Development Setup

### Prerequisites

- Python 3.9+
- Git
- GitHub personal access token (for data collection)
- Jira API token (for data collection)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/your-org/team-metrics.git
cd team-metrics

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing and development

# Copy configuration template
cp config/config.example.yaml config/config.yaml

# Edit config.yaml with your tokens
nano config/config.yaml  # Or use your preferred editor
```

### Configuration

Edit `config/config.yaml`:

```yaml
github:
  token: "ghp_your_token_here"
  organization: "your-org"

jira:
  server: "https://jira.yourcompany.com"
  username: "your-username"  # NOT email
  api_token: "your_bearer_token"

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
```

### Running the Application

```bash
# Collect data (first time or when you need fresh data)
python collect_data.py --date-range 90d

# Start dashboard
python -m src.dashboard.app

# Access at http://localhost:5001
```

### Verification

```bash
# Run tests to verify setup
pytest tests/ -v

# Check code quality
black --check src/ tests/
isort --check src/ tests/
mypy src/

# Expected: All tests pass, no linting errors
```

---

## Project Structure

### Directory Layout

```
team_metrics/
├── src/                      # Source code
│   ├── collectors/           # Data collectors (GitHub, Jira)
│   ├── models/               # Business logic (metrics calculations)
│   ├── dashboard/            # Flask web application
│   │   ├── app.py            # App initialization (228 lines)
│   │   ├── auth.py           # Authentication (153 lines)
│   │   ├── blueprints/       # Route blueprints (4 files, 21 routes)
│   │   ├── services/         # Business services (2 files)
│   │   ├── utils/            # Utilities (6 files)
│   │   ├── templates/        # Jinja2 HTML templates
│   │   └── static/           # CSS, JavaScript
│   ├── utils/                # Shared utilities
│   └── config.py             # Configuration loader
├── tests/                    # Test suite (803 tests)
│   ├── unit/                 # Unit tests
│   ├── collectors/           # Collector tests
│   ├── dashboard/            # Dashboard tests
│   │   ├── blueprints/       # Blueprint tests
│   │   ├── services/         # Service tests
│   │   └── utils/            # Utility tests
│   └── integration/          # Integration tests
├── config/                   # Configuration files
├── data/                     # Cached metrics data
├── docs/                     # Documentation
└── scripts/                  # Automation scripts
```

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/dashboard/app.py` | Flask app initialization | 228 |
| `src/dashboard/blueprints/api.py` | API routes | 171 |
| `src/dashboard/blueprints/dashboard.py` | Dashboard views | 588 |
| `src/dashboard/blueprints/export.py` | Export endpoints | 361 |
| `src/dashboard/blueprints/settings.py` | Settings routes | 139 |
| `src/dashboard/services/cache_service.py` | Cache management | 213 |
| `src/dashboard/services/metrics_refresh_service.py` | Metrics refresh | 156 |
| `src/models/metrics.py` | Core metrics calculator | 605 |
| `src/models/dora_metrics.py` | DORA metrics | 635 |
| `src/collectors/github_graphql_collector.py` | GitHub collector | 1331 |
| `src/collectors/jira_collector.py` | Jira collector | 1180 |

---

## Common Development Tasks

### Adding a New Dashboard Route

**1. Determine the appropriate blueprint:**
- API operations (metrics, refresh) → `api.py`
- Dashboard pages (views, reports) → `dashboard.py`
- Data exports (CSV, JSON) → `export.py`
- Configuration (settings) → `settings.py`
- New feature domain → Create new blueprint

**2. Add route to blueprint:**

```python
# src/dashboard/blueprints/dashboard.py

@dashboard_bp.route('/new-feature')
@timed_route  # Performance monitoring
@require_auth  # Authentication (if enabled)
def new_feature():
    """New feature route handler"""
    # Access dependencies
    config = get_config()
    cache = get_metrics_cache()
    cache_service = get_cache_service()

    # Business logic
    data = process_feature_data(cache)

    # Render template
    return render_template('new_feature.html', data=data)
```

**3. Create template:**

```html
<!-- src/dashboard/templates/new_feature.html -->
{% extends "base.html" %}

{% block title %}New Feature{% endblock %}

{% block content %}
<h1>New Feature</h1>
<!-- Your content here -->
{% endblock %}
```

**4. Add tests:**

```python
# tests/dashboard/blueprints/test_dashboard.py

def test_new_feature(client, mock_cache):
    """Test new feature route"""
    response = client.get('/new-feature')
    assert response.status_code == 200
    assert b'New Feature' in response.data
```

### Adding a New Metric

**1. Add collector method (if new data needed):**

```python
# src/collectors/github_graphql_collector.py

def fetch_new_metric_data(self, team_members):
    """Fetch new metric data from GitHub"""
    # GraphQL query
    query = """
    query {
      # Your query here
    }
    """
    result = self._execute_query(query)
    return result
```

**2. Add calculation in model:**

```python
# src/models/metrics.py

def calculate_new_metric(self, data):
    """Calculate new metric from collected data"""
    df = pd.DataFrame(data)
    metric_value = df['field'].sum()  # Your calculation
    return metric_value
```

**3. Update metrics calculation flow:**

```python
# src/models/metrics.py

def calculate_team_metrics(self, github_data, jira_data, team_config):
    """Calculate all team metrics"""
    # Existing metrics...

    # Add new metric
    new_metric = self.calculate_new_metric(github_data)

    return {
        # Existing metrics...
        'new_metric': new_metric,
    }
```

**4. Display in template:**

```html
<!-- src/dashboard/templates/team_dashboard.html -->
<div class="metric-card">
    <h3>New Metric</h3>
    <p class="metric-value">{{ metrics.new_metric }}</p>
</div>
```

**5. Add tests:**

```python
# tests/unit/test_metrics_calculator.py

def test_calculate_new_metric():
    """Test new metric calculation"""
    calculator = MetricsCalculator()
    data = [{'field': 10}, {'field': 20}]
    result = calculator.calculate_new_metric(data)
    assert result == 30
```

### Adding a New Export Format

**1. Add export utility function:**

```python
# src/dashboard/utils/export.py

def create_xml_response(data: Any, filename: str = "") -> Response:
    """Create XML response from data"""
    import xml.etree.ElementTree as ET

    # Convert data to XML
    root = ET.Element("metrics")
    for key, value in data.items():
        child = ET.SubElement(root, key)
        child.text = str(value)

    xml_str = ET.tostring(root, encoding='utf-8')

    response = Response(
        xml_str,
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "Content-Disposition": 'attachment; filename="export.xml"',
        },
    )
    return response
```

**2. Add export route:**

```python
# src/dashboard/blueprints/export.py

@export_bp.route('/team/<team_name>/xml')
@timed_route
@require_auth
def export_team_xml(team_name):
    """Export team metrics as XML"""
    cache = get_metrics_cache()

    if not validate_identifier(team_name):
        return jsonify({"error": "Invalid team name"}), 400

    team_data = cache["data"]["teams"].get(team_name)
    if not team_data:
        return jsonify({"error": "Team not found"}), 404

    return create_xml_response(team_data, f"team_{team_name}.xml")
```

**3. Add tests:**

```python
# tests/dashboard/utils/test_export.py

def test_create_xml_response():
    """Test XML export response creation"""
    data = {"name": "Team", "score": 95}
    response = create_xml_response(data)

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xml; charset=utf-8"
    assert b'<name>Team</name>' in response.data
```

---

## Blueprint Development

### Blueprint Structure

Each blueprint follows this structure:

```python
# src/dashboard/blueprints/example.py

from flask import Blueprint, render_template, current_app, request
from src.dashboard.auth import require_auth
from src.dashboard.utils.performance import timed_route

# Create blueprint
example_bp = Blueprint('example', __name__)

# Helper functions to access dependencies
def get_metrics_cache():
    """Get metrics cache from current app"""
    return current_app.extensions["metrics_cache"]

def get_cache_service():
    """Get cache service from current app"""
    return current_app.extensions["cache_service"]

def get_config():
    """Get app configuration from current app"""
    return current_app.extensions["app_config"]

# Routes
@example_bp.route('/example')
@timed_route  # Performance monitoring
@require_auth  # Authentication
def example_route():
    """Example route handler"""
    # Access dependencies
    cache = get_metrics_cache()
    config = get_config()

    # Business logic
    data = process_data(cache, config)

    # Render response
    return render_template('example.html', data=data)
```

### Dependency Injection Pattern

Blueprints access shared dependencies via `current_app.extensions`:

```python
# In app.py - Initialize dependencies
from src.dashboard.blueprints import init_blueprint_dependencies

app.extensions["metrics_cache"] = metrics_cache
app.extensions["cache_service"] = cache_service
app.extensions["refresh_service"] = refresh_service
app.extensions["app_config"] = config

# In blueprint - Access dependencies
cache = current_app.extensions["metrics_cache"]
service = current_app.extensions["cache_service"]
```

**Why this pattern?**
- ✅ Avoids circular imports
- ✅ Makes testing easier (mock via extensions)
- ✅ Clear dependency boundaries
- ✅ Easy to add new dependencies

### When to Create a New Blueprint

Create a new blueprint when:

1. **New functional domain** - Feature doesn't fit existing blueprints
2. **5+ related routes** - Enough routes to justify separation
3. **Different URL prefix** - Routes share a common prefix (e.g., `/admin/*`)
4. **Independent testing needs** - Feature needs isolated test suite
5. **Team ownership** - Different team will maintain the routes

**Example: Admin Blueprint**

```python
# src/dashboard/blueprints/admin.py

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users')
def admin_users():
    """Manage users"""
    # Implementation
    pass

@admin_bp.route('/audit-log')
def admin_audit_log():
    """View audit log"""
    # Implementation
    pass

# Register in __init__.py
def register_blueprints(app):
    # ... existing blueprints
    from .admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")
```

### Blueprint Testing

Test blueprints using Flask test client:

```python
# tests/dashboard/blueprints/test_example.py

import pytest
from flask import Flask
from src.dashboard.blueprints import register_blueprints, init_blueprint_dependencies

@pytest.fixture
def app():
    """Create Flask app with blueprints registered"""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Mock dependencies
    from unittest.mock import MagicMock
    cache = {"data": {"teams": {}}}
    cache_service = MagicMock()
    config = MagicMock()

    # Initialize and register
    init_blueprint_dependencies(app, config, cache, cache_service, None)
    register_blueprints(app)

    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

def test_example_route(client):
    """Test example route"""
    response = client.get('/example')
    assert response.status_code == 200
```

---

## Testing Guidelines

### Test Organization

```
tests/
├── unit/                     # Pure logic tests (90%+ coverage target)
│   ├── test_metrics_calculator.py
│   ├── test_dora_metrics.py
│   └── ...
├── collectors/               # API response parsing tests
│   ├── test_github_graphql_collector.py
│   └── test_jira_collector.py
├── dashboard/                # Dashboard component tests
│   ├── test_app.py
│   ├── blueprints/
│   │   ├── test_api.py
│   │   └── test_dashboard.py
│   ├── services/
│   │   ├── test_cache_service.py
│   │   └── test_metrics_refresh_service.py
│   └── utils/
│       ├── test_export.py
│       └── test_formatting.py
└── integration/              # End-to-end tests
    └── test_dora_lead_time_mapping.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific file
pytest tests/unit/test_metrics_calculator.py -v

# Run tests matching pattern
pytest -k "test_dora" -v

# Run with coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Run fast tests only (skip slow integration tests)
pytest -m "not slow"
```

### Writing Good Tests

**1. Use descriptive names:**

```python
# Good
def test_calculates_deployment_frequency_with_multiple_releases():
    """Test that deployment frequency is calculated correctly with multiple releases"""
    pass

# Bad
def test_dora():
    pass
```

**2. Follow Arrange-Act-Assert pattern:**

```python
def test_calculate_lead_time():
    # Arrange
    calculator = MetricsCalculator()
    prs = [{'merged_at': '2024-01-01', 'number': 1}]
    releases = [{'published_at': '2024-01-02', 'tag_name': 'v1.0'}]

    # Act
    result = calculator.calculate_lead_time(prs, releases)

    # Assert
    assert result == 24.0  # 24 hours
```

**3. Use fixtures for common setup:**

```python
@pytest.fixture
def sample_pr_data():
    """Sample PR data for testing"""
    return [
        {'number': 1, 'merged_at': '2024-01-01', 'additions': 100},
        {'number': 2, 'merged_at': '2024-01-02', 'additions': 200},
    ]

def test_pr_processing(sample_pr_data):
    result = process_prs(sample_pr_data)
    assert len(result) == 2
```

**4. Test edge cases:**

```python
def test_handles_empty_data():
    """Test graceful handling of empty data"""
    result = calculate_metric([])
    assert result is None

def test_handles_none_values():
    """Test graceful handling of None values"""
    data = [{'value': None}, {'value': 10}]
    result = calculate_average(data)
    assert result == 10
```

### Coverage Expectations

| Component | Target Coverage |
|-----------|----------------|
| **Unit tests** | 90%+ |
| **Blueprints** | 100% routes |
| **Services** | 85%+ |
| **Utils** | 95%+ |
| **Collectors** | 35%+ (API mocking is expensive) |
| **Overall** | 70%+ |

---

## Code Quality Standards

### Code Formatting

**Black** (code formatter):
```bash
# Format code
black src/ tests/

# Check formatting (CI)
black --check src/ tests/

# Configuration: 120 character lines
# See pyproject.toml
```

**isort** (import sorting):
```bash
# Sort imports
isort src/ tests/

# Check sorting (CI)
isort --check src/ tests/

# Configuration: black-compatible
# See pyproject.toml
```

### Type Hints

Use type hints for all functions:

```python
from typing import Dict, List, Optional, Any

def calculate_average(values: List[float]) -> Optional[float]:
    """Calculate average of values"""
    if not values:
        return None
    return sum(values) / len(values)

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process metrics data"""
    return {
        'processed': True,
        'count': len(data),
    }
```

**mypy** (type checking):
```bash
# Check types
mypy src/

# Expected: No errors
```

### Linting

**pylint** (code quality):
```bash
# Check code quality
pylint src/

# Target: 9.0+ score per file
```

Common issues to avoid:
- Long functions (> 50 lines)
- Too many local variables (> 15)
- Deeply nested code (> 5 levels)
- Unused imports or variables
- Missing docstrings

### Docstrings

Follow Google-style docstrings:

```python
def calculate_metric(data: List[Dict], threshold: float = 0.5) -> Dict[str, float]:
    """Calculate metric from data with threshold.

    Args:
        data: List of dictionaries containing metric data
        threshold: Minimum value threshold (default: 0.5)

    Returns:
        Dictionary with calculated metrics:
        - 'average': Average value
        - 'count': Number of items processed

    Raises:
        ValueError: If data is empty or invalid

    Example:
        >>> data = [{'value': 10}, {'value': 20}]
        >>> result = calculate_metric(data)
        >>> result['average']
        15.0
    """
    if not data:
        raise ValueError("Data cannot be empty")

    values = [item['value'] for item in data]
    return {
        'average': sum(values) / len(values),
        'count': len(values),
    }
```

---

## Git Workflow

### Branch Naming

```
feature/short-description    # New features
bugfix/issue-description     # Bug fixes
refactor/component-name      # Code refactoring
docs/topic                   # Documentation updates
test/component-name          # Test additions
```

### Commit Messages

Follow conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `docs`: Documentation changes
- `chore`: Build/tooling changes
- `style`: Code style changes (formatting)
- `perf`: Performance improvements
- `security`: Security fixes

**Examples:**

```bash
# Feature
git commit -m "feat(dashboard): add team comparison export to PDF"

# Bug fix
git commit -m "fix(collectors): handle rate limit errors in GitHub collector"

# Refactoring
git commit -m "refactor(blueprints): extract common route logic to helper function"

# Security
git commit -m "security(export): sanitize filename to prevent XSS"
```

### Pull Request Process

1. **Create feature branch:**
```bash
git checkout -b feature/new-dashboard-widget
```

2. **Make changes and commit:**
```bash
git add src/dashboard/blueprints/dashboard.py
git commit -m "feat(dashboard): add new performance widget"
```

3. **Run tests and quality checks:**
```bash
pytest
black --check src/ tests/
isort --check src/ tests/
mypy src/
```

4. **Push to remote:**
```bash
git push origin feature/new-dashboard-widget
```

5. **Create pull request:**
- Use descriptive title
- Include description of changes
- Link related issues
- Add screenshots if UI changes
- Request reviewers

6. **Address review feedback:**
```bash
git add <files>
git commit -m "fix(dashboard): address PR feedback"
git push
```

7. **Merge after approval:**
- Squash and merge preferred
- Delete branch after merge

### CI/CD Pipeline

All commits trigger:

1. **Linting** - black, isort, pylint
2. **Type checking** - mypy
3. **Tests** - pytest (all 803 tests)
4. **Security** - CodeQL scanning
5. **Coverage** - Coverage report uploaded

PRs must pass all checks before merge.

---

## Additional Resources

- **Architecture Details**: `docs/ARCHITECTURE.md`
- **Refactoring Summary**: `docs/WEEKS7-8_REFACTORING_SUMMARY.md`
- **API Documentation**: `docs/API_DOCUMENTATION.md`
- **CLAUDE.md**: AI assistant guidance and project details
- **GitHub Issues**: Bug reports and feature requests

---

## Getting Help

1. **Check documentation** in `docs/` directory
2. **Search existing issues** on GitHub
3. **Ask in team chat** (Slack/Teams/etc.)
4. **Create new issue** if problem persists

---

*Document Version: 1.0*
*Last Updated: January 25, 2026*
*For: Week 7-8 Refactored Architecture*
