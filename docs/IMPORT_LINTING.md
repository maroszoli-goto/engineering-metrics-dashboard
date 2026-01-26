# Import Linting for Clean Architecture

**Tool:** import-linter v2.9+
**Purpose:** Automatically enforce Clean Architecture layer boundaries
**Status:** Active (Phase 3.4 Complete)

---

## Quick Start

### Install
```bash
pip install -r requirements-dev.txt
# or
pip install import-linter
```

### Run
```bash
lint-imports
```

**Expected Output:**
```
Contracts: 5 kept, 1 broken.
```

---

## What It Does

Import-linter enforces architectural rules by analyzing Python import statements. It prevents:
- Domain importing Infrastructure
- Presentation bypassing Application to access Domain
- Infrastructure depending on Presentation
- Circular dependencies between layers

**Benefits:**
- ✅ Catches architecture violations in CI/CD
- ✅ Prevents accidental layer boundary violations
- ✅ Documents architecture rules as code
- ✅ Fast feedback loop (runs in <5 seconds)

---

## Configured Contracts

Our `setup.cfg` defines **6 contracts** (rules):

### Contract 1: Domain Must Be Pure (🔴 Critical)
**Rule:** Domain layer cannot import from ANY other layer

```ini
[importlinter:contract:1]
name = Domain layer must not import from other layers
source_modules = src.models
forbidden_modules = src.dashboard, src.collectors, src.utils, src.config
```

**Why:** Domain contains pure business logic and should have zero dependencies on infrastructure, presentation, or application layers.

**Violations:** 2 (temporarily ignored)
- `src.models.metrics -> src.utils.logging`
- `src.models.performance_scoring -> src.config`

---

### Contract 2: No Direct Domain Access from Presentation
**Rule:** Presentation cannot import Domain models directly

```ini
[importlinter:contract:2]
name = Presentation layer must not import Domain directly
source_modules = src.dashboard.blueprints
forbidden_modules = src.models
```

**Why:** Presentation should access Domain through Application services, not directly. This enables proper separation and testability.

**Expected Flow:**
```
✅ Blueprint → Service → Model
❌ Blueprint → Model (bypasses service layer)
```

**Violations:** 1 (temporarily ignored)
- `src.dashboard.blueprints.dashboard -> src.models.metrics`

---

### Contract 3: No Infrastructure in Presentation
**Rule:** Presentation cannot import Infrastructure utilities

```ini
[importlinter:contract:3]
name = Presentation layer must not import Infrastructure
source_modules = src.dashboard.blueprints
forbidden_modules = src.collectors, src.utils
```

**Why:** Presentation should receive infrastructure services through dependency injection, not import them directly.

**Violations:** 4 (temporarily ignored - logging)
- All blueprint files importing `src.utils.logging`

**Status:** 🔴 **BROKEN** - Indirect violation detected:
```
src.dashboard.blueprints.dashboard -> src.models.metrics
src.models.metrics -> src.utils.logging
```

This is caught because fixing Domain violations (Contract 1) will automatically fix this.

---

### Contract 4: No Presentation in Infrastructure
**Rule:** Infrastructure cannot import Presentation layer

```ini
[importlinter:contract:4]
name = Infrastructure must not import Presentation
source_modules = src.collectors, src.utils
forbidden_modules = src.dashboard.blueprints, src.dashboard.templates
```

**Why:** Infrastructure is an inner layer and should not depend on outer Presentation layer.

**Violations:** 2 (temporarily ignored - performance monitoring)
- Collectors importing `src.dashboard.utils.performance`

---

### Contract 5: No Application in Infrastructure
**Rule:** Infrastructure cannot import Application services

```ini
[importlinter:contract:5]
name = Infrastructure must not import Application services
source_modules = src.collectors, src.utils
forbidden_modules = src.dashboard.services
```

**Why:** Infrastructure and Application are at similar levels; Infrastructure should not depend on Application.

**Status:** ✅ **KEPT** (no violations)

---

### Contract 6: No Presentation in Application
**Rule:** Application cannot import Presentation layer

```ini
[importlinter:contract:6]
name = Application layer must not import Presentation
source_modules = src.dashboard.services
forbidden_modules = src.dashboard.blueprints
```

**Why:** Application orchestrates use cases and should not know about HTTP handling.

**Status:** ✅ **KEPT** (no violations)

---

## Current Status

| Contract | Status | Violations | Ignored |
|----------|--------|-----------|---------|
| 1. Domain Must Be Pure | ✅ KEPT | 2 | ✅ |
| 2. No Direct Domain Access | ✅ KEPT | 1 | ✅ |
| 3. No Infrastructure in Presentation | 🔴 BROKEN | 4 + indirect | ✅ |
| 4. No Presentation in Infrastructure | ✅ KEPT | 2 | ✅ |
| 5. No Application in Infrastructure | ✅ KEPT | 0 | - |
| 6. No Presentation in Application | ✅ KEPT | 0 | - |

**Summary:**
- **5 contracts kept** (honored)
- **1 contract broken** (indirect violation from Domain → Infrastructure)
- **All violations temporarily ignored** during transition period

---

## Temporary Ignores

All known violations are temporarily ignored using `ignore_imports` to allow gradual fixing:

```ini
ignore_imports =
    # Domain violations (Phase 3.1 - to fix)
    src.models.metrics -> src.utils.logging
    src.models.performance_scoring -> src.config

    # Presentation violations (Phase 3.2 - to fix)
    src.dashboard.blueprints.dashboard -> src.models.metrics
    src.dashboard.blueprints.* -> src.utils.logging

    # Infrastructure violations (Phase 3.3 - to fix)
    src.collectors.* -> src.dashboard.utils.performance
```

**When Fixed:**
As violations are resolved, remove corresponding `ignore_imports` entries to enforce the rule.

---

## Integration with CI/CD

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: import-linter
      name: Check architecture boundaries
      entry: lint-imports
      language: system
      pass_filenames: false
      always_run: true
```

### GitHub Actions

Add to `.github/workflows/ci.yml`:
```yaml
- name: Check Architecture
  run: |
    pip install import-linter
    lint-imports
```

### Make Target

Add to `Makefile`:
```makefile
.PHONY: lint-imports
lint-imports:
	lint-imports

.PHONY: lint-all
lint-all: lint-imports
	black --check .
	isort --check .
	mypy src/
```

---

## Interpreting Results

### Success Output
```
Contracts: 6 kept, 0 broken.
```
All architecture rules are followed! 🎉

### Failure Output
```
Contracts: 5 kept, 1 broken.

Broken contracts
----------------

Presentation layer must not import Infrastructure
-------------------------------------------------

src.dashboard.blueprints is not allowed to import src.utils:

-   src.dashboard.blueprints.api -> src.utils.logging (l.13)
    src.dashboard.blueprints.dashboard -> src.utils.logging (l.16)
```

**What This Means:**
- Contract name: Which rule was broken
- Import chain: How the violation occurred
- Line numbers: Where to fix it

---

## Fixing Violations

### Step 1: Identify the Violation
```bash
lint-imports
```

Look for "Broken contracts" section.

### Step 2: Understand the Import Chain
Example:
```
src.dashboard.blueprints.dashboard -> src.models.metrics (l.15)
```

Means: Line 15 of `dashboard.py` imports from `metrics.py`

### Step 3: Fix According to Pattern

**Domain Violation Example:**
```python
# ❌ BEFORE: Domain importing Infrastructure
from src.utils.logging import get_logger

class MetricsCalculator:
    def __init__(self):
        self.logger = get_logger(__name__)

# ✅ AFTER: Inject logger through constructor
class MetricsCalculator:
    def __init__(self, logger=None):
        self.logger = logger or NullLogger()
```

**Presentation Violation Example:**
```python
# ❌ BEFORE: Presentation importing Domain directly
from src.models.metrics import MetricsCalculator

def team_dashboard():
    calculator = MetricsCalculator()
    metrics = calculator.calculate_team_metrics(team_name)

# ✅ AFTER: Use Application service
def team_dashboard():
    metrics_service = current_app.container.get("metrics_service")
    metrics = metrics_service.get_team_metrics(team_name)
```

### Step 4: Remove Ignore Entry
Once fixed, remove from `setup.cfg`:
```ini
# Remove this line:
src.dashboard.blueprints.dashboard -> src.models.metrics
```

### Step 5: Verify
```bash
lint-imports
```

Should now show one fewer violation.

---

## Troubleshooting

### "Module does not exist" Error
```
Module 'src.dashboard.services' does not exist.
```

**Solution:** Add `__init__.py` to make it a package:
```bash
touch src/dashboard/services/__init__.py
```

### False Positives
If the linter flags a legitimate import:

1. **Verify it's not a real violation** - Most "false positives" are actual violations
2. **Check if it's an indirect import** - A → B → C can trigger violations
3. **If truly legitimate**, add to `ignore_imports` with a comment explaining why

### Slow Performance
Import-linter is usually fast (<5 seconds). If slow:
- Check if analyzing too many files
- Exclude irrelevant directories in `root_package`
- Use `include_external_packages = False`

---

## Best Practices

### DO ✅
- Run `lint-imports` before committing
- Fix violations immediately (don't accumulate technical debt)
- Remove ignore entries as violations are fixed
- Use in CI/CD to prevent regressions
- Update contracts when architecture changes

### DON'T ❌
- Don't disable contracts without team discussion
- Don't add blanket ignore patterns like `src.* -> *`
- Don't ignore violations indefinitely
- Don't bypass the linter by moving files between layers

---

## Roadmap

### Phase 3.4 (Current) ✅
- [x] Install import-linter
- [x] Create setup.cfg configuration
- [x] Define 6 contracts
- [x] Add temporary ignores for known violations
- [x] Verify linter works correctly
- [x] Document usage

### Phase 3.5 (Next)
- [ ] Fix Domain violations (remove 2 ignores)
- [ ] Fix Presentation violations (remove 3 ignores)
- [ ] Fix Infrastructure violations (remove 2 ignores)
- [ ] Verify all contracts kept
- [ ] Add to CI/CD pipeline

### Phase 4 (Future)
- [ ] Add custom contract types (if needed)
- [ ] Stricter enforcement (fail builds on violations)
- [ ] Metrics dashboard for architecture health
- [ ] Integration with import-linter reporting tools

---

## Reference Links

- **Tool Documentation:** https://import-linter.readthedocs.io/
- **Our Architecture Guide:** [CLEAN_ARCHITECTURE.md](CLEAN_ARCHITECTURE.md)
- **Violations Report:** [ARCHITECTURE_VIOLATIONS.md](ARCHITECTURE_VIOLATIONS.md)
- **ADR-0003:** [Clean Architecture Layers](adr/0003-clean-architecture-layers.md)

---

## Configuration Files

- **Config:** `setup.cfg` (import-linter contracts)
- **Dependencies:** `requirements-dev.txt` (includes import-linter)
- **Package Markers:** `src/dashboard/services/__init__.py` (required for linter)

---

**Last Updated:** 2026-01-26
**Next Review:** After fixing Phase 3 violations
