# Code Quality Guide

This document describes the code quality tools and standards for the Team Metrics Dashboard project.

## Tools Setup

### Installed Tools

All code quality tools are configured in `pyproject.toml`:

- **Black** - Opinionated code formatter (line length: 120)
- **isort** - Import statement organizer (compatible with Black)
- **Pylint** - Comprehensive linter (score: 9.28/10 ✅)
- **Mypy** - Static type checker

### Installation

```bash
# Install in virtual environment
source venv/bin/activate
pip install black isort pylint mypy

# Or install all dev dependencies
pip install -e ".[dev]"
```

### Quick Commands

```bash
# Format code
black src/ collect_data.py list_jira_filters.py validate_config.py analyze_releases.py

# Organize imports
isort src/ collect_data.py list_jira_filters.py validate_config.py analyze_releases.py

# Run linter
pylint src/

# Run type checker
mypy src/

# Run all in sequence
black src/ && isort src/ && pylint src/ && mypy src/
```

## Pre-commit Hooks (Optional)

Pre-commit hooks automatically run checks before each commit.

### Setup

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Configuration

See `.pre-commit-config.yaml` for hook configuration. By default:
- **Black** and **isort** run on every commit (auto-fix)
- **Pylint** and **mypy** run manually only (informational)

## Current Status

### Pylint Score: 9.28/10 ✅

**Top Issues to Address:**
1. **Too many branches/statements** in large functions (refactoring needed)
2. **Import-outside-toplevel** in several places (move to top)
3. **Bare-except** clauses (specify exception types)
4. **Unused imports** (clean up imports)
5. **Line too long** (a few lines exceed 120 chars)

**Disabled Checks** (see `pyproject.toml`):
- `C0103` - invalid-name (we use short names like 'df', 'pr', 'jql')
- `C0114/115/116` - missing-docstring (focus on public APIs)
- `R0913` - too-many-arguments (common in data processing)
- `R0914` - too-many-locals (will address in refactoring)

### Mypy Type Checking

**Found: 74 type errors across 9 files**

**Common Issues:**
1. **Implicit Optional** - Functions with `param=None` need `Optional[Type]` annotation
   - Example: `def func(param: str = None)` → `def func(param: Optional[str] = None)`
   - Affects ~15 functions in `metrics.py`, `jira_collector.py`, `github_graphql_collector.py`

2. **Missing type annotations** - Variables like `trends = {}` need hints
   - Example: `trends = {}` → `trends: Dict[str, int] = {}`
   - Affects ~10 dictionary initializations

3. **Missing stubs** - Third-party libraries without type information
   - `yaml` - Install: `pip install types-PyYAML`
   - `requests` - Install: `pip install types-requests`

4. **app.py has 0% type hint coverage** - Critical priority for improvement

**Type Hint Coverage by Module:**

| Module | Coverage | Priority |
|--------|----------|----------|
| `jira_collector.py` | 96% | ✅ Excellent |
| `github_graphql_collector.py` | 96% | ✅ Excellent |
| `metrics.py` | 83% | 🟡 Good |
| `app.py` | **0%** | 🔴 Critical |

### Black Formatting

**Result: 18 files reformatted** ✅

All code now follows Black style guide (120 char line length, consistent quotes, trailing commas).

### isort Import Organization

**Result: 12 files reorganized** ✅

All imports now follow the standard order:
1. Standard library imports
2. Third-party imports
3. Local application imports

## Code Complexity

### Largest Functions (Need Refactoring)

| Function | File | Lines | Complexity | Status |
|----------|------|-------|------------|--------|
| `calculate_team_metrics` | metrics.py | 255 | Very High | 🔴 Critical |
| `_calculate_lead_time_for_changes` | metrics.py | 174 | High | 🟡 High Priority |
| `calculate_performance_score` | metrics.py | 160 | High | 🟡 High Priority |
| `_calculate_change_failure_rate` | metrics.py | 130 | Medium | 🟢 Medium Priority |
| `_collect_repository_metrics_batched` | github_graphql_collector.py | 75 | Medium | 🟢 OK |

**Next Steps**: See refactoring plan in next section.

## Recommended Workflow

### Daily Development

1. Write code as normal
2. Before committing:
   ```bash
   black src/
   isort src/
   ```
3. Commit changes

### Before Pull Request

1. Run full linting:
   ```bash
   pylint src/
   ```
2. Address critical issues (score should stay above 9.0)
3. Run type checking:
   ```bash
   mypy src/
   ```
4. Run tests:
   ```bash
   pytest
   ```

### CI/CD Integration

Add to CI pipeline (`.github/workflows/quality.yml`):

```yaml
- name: Check code quality
  run: |
    pip install black isort pylint mypy
    black --check src/
    isort --check-only src/
    pylint src/ --fail-under=9.0
    mypy src/
```

## Configuration Details

### Black Configuration

```toml
[tool.black]
line-length = 120
target-version = ['py38', 'py39', 'py310', 'py311']
```

**Why 120 chars?** Modern displays support wider lines, and data processing code benefits from longer lines for readability.

### Pylint Configuration

See `pyproject.toml` for full configuration. Key settings:

- **max-line-length**: 120 (matches Black)
- **max-args**: 10 (will reduce during refactoring)
- **max-locals**: 20 (will reduce during refactoring)
- **max-branches**: 15 (currently exceeded in 5 functions)
- **max-statements**: 60 (currently exceeded in 4 functions)

### Mypy Configuration

Starting with permissive settings, will gradually tighten:

- **python_version**: 3.8 (minimum supported)
- **disallow_untyped_defs**: false (start permissive)
- **ignore_missing_imports**: true (many libs lack stubs)
- **no_implicit_optional**: true (enforce explicit Optional)

## Next Steps

### Phase 1: Critical Fixes (1-2 days)

1. **Add type hints to app.py** - 37 functions need hints
2. **Install type stubs** - `pip install types-PyYAML types-requests`
3. **Fix implicit Optional** - Add Optional[] to ~15 function signatures
4. **Refactor `calculate_team_metrics`** - Split into 3-4 helper functions

### Phase 2: Code Cleanup (2-3 days)

5. **Split metrics.py** - Create separate modules:
   - `dora_metrics.py` (DORA calculation logic)
   - `performance_scoring.py` (scoring system)
6. **Fix bare-except** - Specify exception types
7. **Remove unused imports** - Clean up imports
8. **Move imports to top** - Eliminate import-outside-toplevel

### Phase 3: Advanced Improvements (1 week)

9. **Refactor DORA functions** - Extract common patterns
10. **Introduce Flask blueprints** - Split app.py into modules
11. **Increase test coverage** - Target 85%+ coverage
12. **Enable stricter mypy** - Set disallow_untyped_defs=true

## Resources

- **Black**: https://black.readthedocs.io/
- **isort**: https://pycqa.github.io/isort/
- **Pylint**: https://pylint.readthedocs.io/
- **Mypy**: https://mypy.readthedocs.io/
- **Pre-commit**: https://pre-commit.com/

## Questions?

For questions about code quality standards or tooling, see:
- `pyproject.toml` - All tool configurations
- `CLAUDE.md` - Development workflow
- This file - Code quality guidelines
