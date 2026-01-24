# Team Metrics Dashboard - Testing Guide

## Running Tests

### All Tests
```bash
# Run full test suite
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov --cov-report=term-missing
pytest --cov --cov-report=html  # Generate HTML report
```

### Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/collectors/ -v

# Dashboard tests only
pytest tests/dashboard/ -v

# Fast tests (exclude slow)
pytest -m "not slow"
```

### Coverage Reports
```bash
# Terminal coverage report
pytest --cov=src --cov-report=term-missing

# HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html  # macOS
```

## Test Structure

### Unit Tests (`tests/unit/`)
- `test_jira_metrics.py` - Jira metrics processing (26 tests)
- `test_dora_metrics.py` - DORA metrics & trends (39 tests)
- `test_dora_trends.py` - DORA trend calculations (13 tests)
- `test_metrics_calculator.py` - Core metrics calculations (44 tests)
- `test_performance_score.py` - Performance scoring (19 tests)
- `test_config.py` - Configuration validation (27 tests)
- `test_date_ranges.py` - Date utility functions (40 tests)

### Collector Tests (`tests/collectors/`)
- `test_github_graphql_collector.py` - GitHub GraphQL API (27 tests)
- `test_github_graphql_simple.py` - GraphQL data extraction (15 tests)
- `test_jira_collector.py` - Jira API response parsing (27 tests)
- `test_jira_pagination.py` - Jira pagination strategies (14 tests)
- `test_jira_fix_versions.py` - Fix version parsing (6 tests)

### Integration Tests (`tests/integration/`)
- `test_dora_lead_time_mapping.py` - PR→Jira→Release mapping (19 tests)

### Dashboard Tests (`tests/dashboard/`)
- `test_app.py` - Flask route integration tests (18 tests)

### Fixtures (`tests/fixtures/`)
- `sample_data.py` - Mock data generators

## Writing New Tests

### Test Naming Convention
- File: `test_<module_name>.py`
- Class: `Test<FeatureName>`
- Method: `test_<what>_<expected_behavior>`

### Using Fixtures
```python
import pytest

def test_with_fixture(sample_pr_dataframe):
    # Use fixture
    assert len(sample_pr_dataframe) > 0
```

### Mocking External APIs
```python
import responses

@responses.activate
def test_api_call():
    responses.add(responses.GET, 'https://api.example.com', json={'data': []})
    # Your test code
```

### Flask Testing

#### Route Tests
```python
def test_route(client, mock_cache):
    """Test a Flask route"""
    response = client.get('/some/route')
    assert response.status_code == 200
    assert b'Expected Content' in response.data
```

#### Template Tests
```python
def test_template(app_context):
    """Test template rendering"""
    from flask import render_template
    result = render_template('template_name.html', data='value')
    assert 'Expected Output' in result
```

## Coverage Targets

| Module | Target | Actual | Status |
|--------|--------|--------|--------|
| **Core Business Logic** |  |  |  |
| jira_metrics.py | 70% | 94.44% | ✅ Excellent |
| dora_metrics.py | 70% | 90.54% | ✅ Excellent |
| performance_scoring.py | 85% | 97.37% | ✅ Excellent |
| date_ranges.py | 80% | 96.39% | ✅ Excellent |
| metrics.py (orchestration) | 60% | 43.56% | ⚠️ Needs improvement |
| **Data Collectors** |  |  |  |
| github_graphql_collector.py | 25% | 27.66% | ✅ Met target |
| jira_collector.py | 35% | 37.25% | ✅ Met target |
| **Dashboard** |  |  |  |
| dashboard/app.py | 65% | 64.42% | 🟡 Close to target |
| **Overall** | **60%** | **60.49%** | **✅ Target Met** |

**Test Suite Status**: 509 tests, all passing (~5 seconds execution)

**Recent Improvements**:
- +92 tests (+22% increase)
- +7.53% overall coverage
- +13.54% Jira collector coverage (most improved)
- +15.46% DORA metrics coverage
- 35 new collector tests for production reliability

## Test Artifacts

The following files are generated during test runs and are gitignored:

- `.coverage` - Binary coverage data
- `htmlcov/` - HTML coverage reports
- `.pytest_cache/` - Pytest cache directory
- `*.cover` - Alternative coverage file format

## Troubleshooting

### ImportError: No module named 'src'
Make sure you're running pytest from the project root directory.

### Fixture not found
Shared fixtures are defined in `tests/conftest.py`. Check there first.

### Template not found
Flask templates are in `src/dashboard/templates/`. Ensure tests run with proper app context.

### Tests taking too long
Use `-m "not slow"` to skip slow tests, or run specific test files.

## Continuous Integration

When setting up CI/CD:

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests with coverage
pytest --cov=src --cov-report=xml --cov-report=term

# Generate coverage badge (optional)
coverage-badge -o coverage.svg -f
```

## Best Practices

1. **Isolate tests** - Each test should be independent
2. **Use fixtures** - Leverage shared fixtures from `conftest.py`
3. **Mock external calls** - Use `responses` for API calls, `monkeypatch` for other mocks
4. **Test edge cases** - Include tests for empty data, None values, invalid inputs
5. **Keep tests fast** - Mark slow tests with `@pytest.mark.slow`
6. **Descriptive names** - Test names should explain what's being tested
7. **Arrange-Act-Assert** - Follow AAA pattern consistently

## Example Test

```python
import pytest
from src.models.metrics import MetricsCalculator

class TestMetricsCalculator:
    """Tests for MetricsCalculator class"""

    def test_calculate_pr_metrics_with_valid_data(self, sample_pr_dataframe):
        """Test PR metrics calculation with valid data"""
        # Arrange
        calculator = MetricsCalculator()

        # Act
        result = calculator.calculate_pr_metrics(sample_pr_dataframe)

        # Assert
        assert 'pr_count' in result
        assert result['pr_count'] > 0
```

## Documentation

- Main README: `../README.md`
- Developer Guide: `../CLAUDE.md`
- Quick Start: `../docs/QUICK_START.md`
- Implementation Guide: `../IMPLEMENTATION_GUIDE.md`
