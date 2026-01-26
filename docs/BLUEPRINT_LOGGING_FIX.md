# Blueprint Logging Fix (2026-01-26)

## Overview

Eliminated the last critical Clean Architecture violation by removing direct infrastructure imports from Presentation layer (blueprints). Replaced custom logging imports with Flask's built-in `current_app.logger`.

## Problem Statement

### Architecture Violation

Blueprints (Presentation layer) were directly importing `get_logger()` from `src.utils.logging` (Infrastructure layer), violating Clean Architecture's dependency rule:

**Dependency Rule**: Presentation → Application → Domain
                                        ↓
                              Infrastructure → Domain

**Violation**: Presentation was directly importing Infrastructure (bypassing Application layer)

### Affected Files

All 4 blueprint files had logging imports:
- `src/dashboard/blueprints/api.py` - 8 logger calls
- `src/dashboard/blueprints/dashboard.py` - 3 logger calls
- `src/dashboard/blueprints/export.py` - 14 logger calls
- `src/dashboard/blueprints/settings.py` - 2 logger calls

### Import Pattern (Before)

```python
from src.utils.logging import get_logger

logger = get_logger("team_metrics.dashboard.api")

@api_bp.route("/refresh")
def refresh_metrics():
    try:
        # ... code ...
        logger.info("Metrics refreshed successfully")
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
```

**Problem**: Direct dependency from Presentation to Infrastructure

## Solution

### Flask's Built-in Logger

Flask provides `current_app.logger` which is:
- Part of the Presentation framework (not Infrastructure)
- Automatically configured with app settings
- Accessible from any request context
- The recommended Flask pattern

### Import Pattern (After)

```python
# No logging import needed!

@api_bp.route("/refresh")
def refresh_metrics():
    try:
        # ... code ...
        current_app.logger.info("Metrics refreshed successfully")
    except Exception as e:
        current_app.logger.error(f"Refresh failed: {e}")
```

**Benefit**: Zero infrastructure imports, uses framework-provided logger

## Implementation Details

### Changes Per File

#### 1. api.py
**Lines removed**: 12, 16 (import and logger initialization)
**Replacements**: 8 occurrences of `logger.` → `current_app.logger.`

```diff
- from src.utils.logging import get_logger
- logger = get_logger("team_metrics.dashboard.api")

- logger.error(f"Metrics refresh failed: {str(e)}")
+ current_app.logger.error(f"Metrics refresh failed: {str(e)}")
```

#### 2. dashboard.py
**Lines removed**: 15, 19 (import and logger initialization)
**Replacements**: 3 occurrences of `logger.` → `current_app.logger.`

```diff
- from src.utils.logging import get_logger
- logger = get_logger("team_metrics.dashboard.views")

- logger.warning(f"Invalid team name in URL: {e}")
+ current_app.logger.warning(f"Invalid team name in URL: {e}")
```

#### 3. export.py
**Lines removed**: 14, 18 (import and logger initialization)
**Replacements**: 14 occurrences of `logger.` → `current_app.logger.`

```diff
- from src.utils.logging import get_logger
- logger = get_logger("team_metrics.dashboard.export")

- logger.error(f"CSV export failed for team {team_name}: {str(e)}")
+ current_app.logger.error(f"CSV export failed for team {team_name}: {str(e)}")
```

#### 4. settings.py
**Lines removed**: 11, 15 (import and logger initialization)
**Replacements**: 2 occurrences of `logger.` → `current_app.logger.`

```diff
- from src.utils.logging import get_logger
- logger = get_logger("team_metrics.dashboard.settings")

- logger.error(f"Settings save failed: {str(e)}")
+ current_app.logger.error(f"Settings save failed: {str(e)}")
```

### setup.cfg Changes

Removed logging ignores from import-linter contract 3:

```diff
 [importlinter:contract:3]
 name = Presentation layer must not import Infrastructure
 ignore_imports =
-    # Temporarily ignore logging imports until fixed (Phase 3.2)
-    src.dashboard.blueprints.api -> src.utils.logging
-    src.dashboard.blueprints.dashboard -> src.utils.logging
-    src.dashboard.blueprints.export -> src.utils.logging
-    src.dashboard.blueprints.settings -> src.utils.logging
     # Performance monitoring (cross-cutting concern for route timing)
+    # Blueprints import @timed_route decorator for performance tracking
     src.dashboard.blueprints.api -> src.utils.performance
     src.dashboard.blueprints.dashboard -> src.utils.performance
     src.dashboard.blueprints.export -> src.utils.performance
     src.dashboard.blueprints.settings -> src.utils.performance
```

## Impact Analysis

### Architecture Metrics

**Before**:
- Total dependencies: 85
- Architecture violations: 4 (logging imports)
- Contracts kept: 6
- Contracts broken: 0 (but 4 ignored)

**After**:
- Total dependencies: 81 (4 fewer)
- Architecture violations: 0
- Contracts kept: 6
- Contracts broken: 0 (no ignores needed)

**Improvement**: 4.7% reduction in cross-layer dependencies

### Test Results

All tests passing with no changes required:
```
903 passed, 30 warnings in 57.78s
Coverage: 77.03%
```

**Why no test changes?** Tests mock Flask's `current_app` context, so logger calls work transparently.

### Runtime Behavior

**No functional changes**:
- Same log messages
- Same log levels (INFO, WARNING, ERROR)
- Same log formatting
- Same log destinations (files, console)

**Why?** Flask's `current_app.logger` uses the same underlying logger configured in `src/utils/logging/config.py` via `app.logger = get_logger("team_metrics")` in `app.py:83`.

## Verification

### Import-Linter Results

```bash
$ lint-imports

Analyzed 45 files, 81 dependencies.

Domain layer must not import from other layers KEPT
Presentation layer must not import Domain directly KEPT
Presentation layer must not import Infrastructure KEPT  ← Fixed!
Infrastructure must not import Presentation KEPT
Infrastructure must not import Application services KEPT
Application layer must not import Presentation KEPT

Contracts: 6 kept, 0 broken.
```

### Manual Testing

```bash
# Start dashboard
python -m src.dashboard.app

# Trigger error (invalid URL)
curl http://localhost:5001/team/invalid%20team

# Check logs show warning
tail -f logs/team_metrics.log | grep "Invalid team name"
# ✅ Output: WARNING - Invalid team name in URL: ...
```

## Best Practices Applied

### 1. Use Framework Conventions
Flask provides `current_app.logger` specifically for this use case. Using framework-provided utilities is preferred over custom infrastructure.

### 2. Minimize Cross-Layer Dependencies
Presentation layer should only depend on:
- Its own framework (Flask)
- Application layer services
- NOT Infrastructure directly

### 3. Follow Clean Architecture
```
✅ Blueprint → Flask → Logger (within framework)
❌ Blueprint → Infrastructure → Logger (violates layering)
```

### 4. Leverage Dependency Injection
Flask's application context is a form of dependency injection - the logger is injected through `current_app` rather than imported directly.

## Remaining Acceptable Violations

One category of Infrastructure imports remains in Presentation layer:

**Performance Monitoring** (`@timed_route` decorator):
```python
from src.utils.performance import timed_route

@api_bp.route("/refresh")
@timed_route
def refresh_metrics():
    # ...
```

**Why acceptable?**:
1. **Decorator pattern**: Applied at function definition, not runtime
2. **Cross-cutting concern**: Performance monitoring spans all layers
3. **No alternative**: Flask doesn't provide built-in route timing
4. **Minimal coupling**: Decorator is pure function, no state dependencies

**Documented in setup.cfg**:
```ini
ignore_imports =
    # Performance monitoring (cross-cutting concern for route timing)
    # Blueprints import @timed_route decorator for performance tracking
    src.dashboard.blueprints.api -> src.utils.performance
    src.dashboard.blueprints.dashboard -> src.utils.performance
    src.dashboard.blueprints.export -> src.utils.performance
    src.dashboard.blueprints.settings -> src.utils.performance
```

## Alternative Approaches Considered

### 1. Dependency Injection via ServiceContainer
**Approach**: Inject logger through ServiceContainer
```python
def get_logger():
    return current_app.container.get("logger")

logger = get_logger()
logger.info("message")
```

**Rejected**: More complex, same result as `current_app.logger`

### 2. Logger Wrapper in Application Layer
**Approach**: Create `LoggingService` in Application layer
```python
class LoggingService:
    def info(self, msg): ...
    def error(self, msg): ...

logging_service = get_logging_service()
logging_service.info("message")
```

**Rejected**: Over-engineering for simple logging needs

### 3. Pass Logger as Function Parameter
**Approach**: Pass logger to every function
```python
def refresh_metrics(logger):
    logger.info("Refreshing...")
```

**Rejected**: Verbose, requires changing all function signatures

## Lessons Learned

1. **Check framework capabilities first**: Flask already provides what we need
2. **Architecture violations can be eliminated**: Don't settle for "acceptable" violations if there's a clean solution
3. **Test coverage helps refactoring**: All tests passed with zero modifications
4. **Import-linter is valuable**: Automated detection prevented new violations
5. **Document trade-offs**: Performance monitoring exception is well-justified

## Related Documentation

- **CI/CD Fixes**: `docs/CI_CD_FIXES.md`
- **Phase 3 Completion**: `docs/PHASE3_COMPLETION.md`
- **Clean Architecture**: `docs/CLEAN_ARCHITECTURE.md`
- **ADR-002**: Layered Architecture Boundaries (`docs/architecture/adr/ADR-002-layered-architecture.md`)

## Commit

**Hash**: `9179bff`
**Message**: "fix: Remove infrastructure logging imports from blueprints"
**Files Changed**: 5 files, +28 insertions, -48 deletions
**Tests**: All 903 passing
**CI/CD**: ✅ All checks passing
