# Clean Architecture Violations Report

**Date:** 2026-01-26
**Status:** Phase 3 - Analysis Complete
**Total Violations:** 7 (3 High, 3 Medium, 1 Low)

---

## Executive Summary

The Team Metrics Dashboard codebase has **7 Clean Architecture violations** across all layers. While Phases 1-2 successfully implemented the Application Factory Pattern and Dependency Injection Container, several layer boundary violations remain from the pre-refactoring codebase.

**Most Critical Issues:**
1. Domain layer has infrastructure dependencies (logging, config)
2. Presentation layer bypasses Application to access Domain directly
3. Infrastructure layer imports from Presentation utilities

**Good News:** The Application layer (`services/`) has **zero violations** - it correctly follows Clean Architecture principles.

---

## Violation Categories

### 🔴 High Severity (3 violations)
Issues that fundamentally violate Clean Architecture principles and should be fixed immediately.

### 🟡 Medium Severity (3 violations)
Issues that create coupling problems but don't break core principles as severely.

### 🟢 Low Severity (1 violation)
Organizational issues that could be improved but don't break architecture.

---

## Detailed Violations

### 1. Domain Layer Violations (🔴 HIGH PRIORITY)

#### Violation 1.1: Domain Imports Infrastructure Logger

**File:** `src/models/metrics.py:7`

```python
from src.utils.logging import get_logger  # ❌ VIOLATION
```

**Why it's a violation:**
Domain layer must be pure business logic with NO external dependencies. Importing infrastructure utilities couples domain logic to implementation details.

**Impact:**
- Cannot test domain logic in isolation
- Domain models depend on logging infrastructure
- Violates Dependency Inversion Principle

**Recommended Fix:**
```python
# Option 1: Inject logger through constructor
class MetricsCalculator:
    def __init__(self, logger=None):
        self.logger = logger or NullLogger()  # Fallback to no-op logger

# Option 2: Remove logging from domain entirely
# Domain should raise exceptions, Application layer logs them
```

**Files Affected:** 1
**Tests Affected:** Potentially all domain tests

---

#### Violation 1.2: Domain Imports Infrastructure Config

**File:** `src/models/performance_scoring.py:42`

```python
def load_performance_weights(weights: Optional[Dict] = None) -> Dict[str, float]:
    if weights is None:
        try:
            from ..config import Config  # ❌ VIOLATION
            config = Config()
            weights = config.performance_weights
```

**Why it's a violation:**
Domain models should never import configuration. Configuration is an infrastructure concern that should be injected.

**Impact:**
- Domain logic depends on config file structure
- Cannot test with different configurations easily
- Violates single responsibility principle

**Recommended Fix:**
```python
# Use hardcoded defaults in domain, inject custom weights from Application layer
DEFAULT_WEIGHTS = {
    "prs": 0.15,
    "reviews": 0.15,
    # ... etc
}

def load_performance_weights(weights: Optional[Dict] = None) -> Dict[str, float]:
    return weights if weights is not None else DEFAULT_WEIGHTS.copy()
```

**Files Affected:** 1
**Tests Affected:** `tests/models/test_performance_scoring.py`

---

### 2. Presentation Layer Violations (🔴 HIGH)

#### Violation 2.1: Presentation Directly Imports Domain

**File:** `src/dashboard/blueprints/dashboard.py:15`

```python
from src.models.metrics import MetricsCalculator  # ❌ VIOLATION
```

**Why it's a violation:**
Presentation layer should ONLY communicate with Application layer. Directly importing Domain models bypasses the service layer and creates tight coupling.

**Expected Flow:**
```
❌ Current:  Blueprint → MetricsCalculator (Domain)
✅ Expected: Blueprint → Service (Application) → MetricsCalculator (Domain)
```

**Impact:**
- UI code directly coupled to business logic
- Changes to domain models require UI changes
- Cannot easily swap domain implementations

**Recommended Fix:**
```python
# Remove direct import
# ❌ from src.models.metrics import MetricsCalculator

# Use service layer instead
def get_team_metrics(team_name: str):
    metrics_service = current_app.container.get("metrics_service")
    return metrics_service.calculate_team_metrics(team_name)
```

**Files Affected:** 1
**Tests Affected:** Blueprint integration tests

---

#### Violation 2.2: Presentation Imports Infrastructure Utilities

**Files:** All blueprint files
- `api.py:13`
- `dashboard.py:16`
- `export.py:15`
- `settings.py:12`

```python
from src.utils.logging import get_logger  # ❌ VIOLATION
```

**Why it's a violation:**
Presentation should not directly import Infrastructure. Even for cross-cutting concerns like logging, dependency injection should be used.

**Impact:**
- Presentation coupled to infrastructure logging
- Cannot easily swap logging implementations
- Violates dependency injection principle

**Recommended Fix:**
```python
# Option 1: Inject logger via container
logger = current_app.container.get("logger")

# Option 2: Use Flask's built-in logging
from flask import current_app
current_app.logger.info("message")
```

**Severity:** 🟡 **MEDIUM** (logging is a cross-cutting concern, less severe than other violations)

**Files Affected:** 4 blueprint files
**Tests Affected:** None (logging is mocked in tests)

---

### 3. Infrastructure Layer Violations (🟡 MEDIUM)

#### Violation 3.1: Infrastructure Imports Presentation Utilities

**Files:**
- `src/collectors/github_graphql_collector.py:17`
- `src/collectors/jira_collector.py:13`

```python
from src.dashboard.utils.performance import timed_api_call, timed_operation  # ❌ VIOLATION
```

**Why it's a violation:**
Infrastructure layer is importing from `src/dashboard/utils/` (Presentation layer utilities). This creates a reverse dependency where inner layers depend on outer layers.

**Dependency Flow:**
```
❌ Current:  collectors/ (Infrastructure) → dashboard/utils/ (Presentation)
✅ Expected: collectors/ (Infrastructure) → utils/ (Infrastructure)
```

**Impact:**
- Risk of circular dependencies
- Violates "dependencies point inward" rule
- Performance monitoring shouldn't be in dashboard utilities

**Recommended Fix:**
```python
# Move performance decorators to infrastructure utilities
# From: src/dashboard/utils/performance.py
# To:   src/utils/performance.py

# Update imports
from src.utils.performance import timed_api_call, timed_operation  # ✅ OK
```

**Files Affected:** 2 collectors
**Tests Affected:** Collector tests with performance monitoring

---

### 4. Organizational Issues (🟢 LOW)

#### Observation 4.1: Dashboard Utils vs Core Utils

**Location:** `src/dashboard/utils/` contains:
- `performance.py` - Used by Infrastructure (collectors)
- `validation.py` - Input validation
- `export.py` - Export helpers
- `error_handling.py` - Error utilities
- `formatting.py` - Display formatting
- `data.py` - Data manipulation
- `data_filtering.py` - Date filtering

**Issue:**
Some utilities (especially `performance.py`) are used by Infrastructure layer, suggesting they don't truly belong in the Presentation layer's utility folder.

**Recommendation:**
Move cross-cutting utilities to `src/utils/`:
- `performance.py` → `src/utils/performance.py` (used by collectors)
- Keep presentation-specific utils in `src/dashboard/utils/`:
  - `export.py` (CSV/JSON formatting)
  - `formatting.py` (display helpers)
  - `validation.py` (request validation)

**Files Affected:** 1 file to move
**Tests Affected:** Update import paths in tests

---

## Summary by Layer

| Layer | Violations | Status |
|-------|-----------|--------|
| **Presentation** (`blueprints/`) | 2 High, 1 Medium | ❌ Needs Refactoring |
| **Application** (`services/`) | 0 | ✅ Clean |
| **Domain** (`models/`) | 2 High | ❌ Critical Fixes Needed |
| **Infrastructure** (`collectors/`, `utils/`) | 2 Medium, 1 Low | ⚠️ Improvements Needed |

---

## Priority Fix Plan

### Phase 3.1: Critical Domain Fixes (2-3 hours)

**Priority 1A: Remove Logging from Domain**

1. **File:** `src/models/metrics.py`
   - Remove `from src.utils.logging import get_logger`
   - Add `logger` parameter to `__init__`
   - Update all method calls to use `self.logger`
   - Make logger optional with null object fallback

2. **Update callers:**
   - Application layer services should inject logger
   - Tests should pass mock logger or None

3. **Tests:** Update `tests/models/test_metrics.py` to work without logging

---

**Priority 1B: Remove Config from Domain**

1. **File:** `src/models/performance_scoring.py`
   - Remove `from ..config import Config` import
   - Change `load_performance_weights()` to use hardcoded defaults
   - Require callers to pass weights explicitly

2. **Update callers:**
   - Application layer loads config and passes weights
   - `MetricsRefreshService` injects performance weights

3. **Tests:** Update to pass weights directly

---

### Phase 3.2: Presentation Layer Decoupling (3-4 hours)

**Priority 2A: Remove Direct Domain Access**

1. **Create MetricsService** (if not exists)
   - Wrap `MetricsCalculator` in Application service
   - Register in ServiceContainer
   - Expose methods needed by blueprints

2. **Update `dashboard.py`:**
   - Remove `from src.models.metrics import MetricsCalculator`
   - Use `metrics_service = current_app.container.get("metrics_service")`

3. **Tests:** Update blueprint tests to mock service

---

**Priority 2B: Inject Logger in Blueprints**

1. **All blueprint files:**
   - Remove `from src.utils.logging import get_logger`
   - Use `logger = current_app.container.get("logger")`
   - Or use Flask's `current_app.logger`

2. **Tests:** No changes needed (already mocked)

---

### Phase 3.3: Infrastructure Reorganization (1-2 hours)

**Priority 3: Move Performance Utilities**

1. **Move file:**
   ```bash
   mv src/dashboard/utils/performance.py src/utils/performance.py
   ```

2. **Update imports:**
   - `src/collectors/github_graphql_collector.py`
   - `src/collectors/jira_collector.py`
   - `tests/collectors/test_*.py`

3. **Tests:** Update import paths

---

## Effort Estimate

| Phase | Tasks | Estimated Time | Risk Level |
|-------|-------|---------------|------------|
| 3.1 Domain Fixes | 2 violations | 2-3 hours | Low (well-isolated) |
| 3.2 Presentation | 2 violations | 3-4 hours | Medium (affects blueprints) |
| 3.3 Infrastructure | 1 violation | 1-2 hours | Low (simple file move) |
| **Total** | **7 violations** | **6-9 hours** | **Low-Medium** |

---

## Benefits of Fixing

### Immediate Benefits
- ✅ Domain layer becomes truly testable in isolation
- ✅ Proper separation of concerns
- ✅ Follows industry best practices
- ✅ Easier to mock dependencies in tests

### Long-term Benefits
- ✅ Easier to refactor domain logic
- ✅ Can swap infrastructure implementations
- ✅ Better onboarding for new developers
- ✅ Enables future architectural evolution
- ✅ Reduces risk of circular dependencies

---

## Risks of NOT Fixing

### Technical Debt
- ❌ Domain models coupled to infrastructure
- ❌ Difficult to test domain logic independently
- ❌ Risk of circular dependencies
- ❌ Violates SOLID principles

### Maintenance Issues
- ❌ Changes to infrastructure affect domain
- ❌ Changes to domain affect presentation
- ❌ Hard to reason about layer boundaries
- ❌ Confusing for new developers

---

## Files Requiring Changes

### High Priority (Domain Layer)
1. ✏️ `src/models/metrics.py` - Remove logging import
2. ✏️ `src/models/performance_scoring.py` - Remove config import
3. ✏️ `src/dashboard/services/metrics_refresh_service.py` - Inject logger to domain
4. ✏️ `tests/models/test_metrics.py` - Update tests

### High Priority (Presentation Layer)
5. ✏️ `src/dashboard/blueprints/dashboard.py` - Remove domain import, use service
6. ✏️ `src/dashboard/services/` - Create metrics service wrapper (if needed)
7. ✏️ All blueprint files - Switch from `get_logger()` to injected logger

### Medium Priority (Infrastructure)
8. 📦 Move `src/dashboard/utils/performance.py` → `src/utils/performance.py`
9. ✏️ `src/collectors/github_graphql_collector.py` - Update import
10. ✏️ `src/collectors/jira_collector.py` - Update import
11. ✏️ Update performance tests

---

## Testing Strategy

### Before Fixing
1. ✅ Run full test suite: `pytest` (current: 903 passing)
2. ✅ Verify coverage: `pytest --cov` (current: 77%)

### During Fixing
1. Fix one violation at a time
2. Run affected tests after each fix
3. Ensure no regressions

### After Fixing
1. ✅ All 903 tests still passing
2. ✅ Coverage maintained at 77%+
3. ✅ No new import-linter violations (Phase 3.4)

---

## Success Criteria

**Phase 3 Complete When:**
- [ ] All 7 violations documented (✅ Done)
- [ ] All High priority violations fixed (7 violations)
- [ ] All tests passing (903 tests)
- [ ] Coverage maintained (77%+)
- [ ] Import linter configured (Phase 3.4)
- [ ] No new violations introduced

---

## Next Steps

1. **Review this document** with team
2. **Get approval** for fix priorities
3. **Start Phase 3.1** (Critical Domain Fixes)
4. **Continue with** Phases 3.2-3.3
5. **Add import-linter** (Phase 3.4) to prevent regressions

---

## References

- [Clean Architecture Guide](CLEAN_ARCHITECTURE.md)
- [ADR-0003: Clean Architecture Layers](adr/0003-clean-architecture-layers.md)
- [Architecture Roadmap](ARCHITECTURE_ROADMAP.md)

---

**Last Updated:** 2026-01-26
**Next Review:** After completing Phase 3 fixes
