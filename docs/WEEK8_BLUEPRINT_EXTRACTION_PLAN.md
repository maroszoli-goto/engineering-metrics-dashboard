# Week 8: Blueprint Extraction - Implementation Plan

## Overview

Extract 21 routes from the monolithic 1,190-line `app.py` into 4 well-organized Flask blueprints, reducing `app.py` to ~350-400 lines (67% reduction) while maintaining 100% backward compatibility.

**Goal**: Improve code organization, route modularity, and team collaboration through Flask's standard blueprint pattern.

**Success Criteria**:
- All 774 tests pass (zero regressions)
- app.py reduced by ~800 lines (67% reduction)
- 4 new blueprints with clear responsibilities
- 100% route coverage maintained
- Zero breaking changes to existing URLs

---

## Current State Analysis

### Routes by Category (21 total)

**Dashboard Routes (5 routes)**:
- `/` - Main teams overview
- `/team/<team_name>` - Team dashboard
- `/person/<username>` - Person dashboard
- `/team/<team_name>/compare` - Team member comparison
- `/comparison` - Cross-team comparison

**API Routes (4 routes)**:
- `/api/metrics` - Get cached metrics
- `/api/refresh` - Force metrics refresh
- `/api/reload-cache` - Reload cache from disk
- `/collect` - Trigger collection (redirects to dashboard)

**Export Routes (8 routes)**:
- `/api/export/team/<team_name>/csv`
- `/api/export/team/<team_name>/json`
- `/api/export/person/<username>/csv`
- `/api/export/person/<username>/json`
- `/api/export/comparison/csv`
- `/api/export/comparison/json`
- `/api/export/team-members/<team_name>/csv`
- `/api/export/team-members/<team_name>/json`

**Settings Routes (3 routes)**:
- `/settings` - Settings page
- `/settings/save` - Save settings
- `/settings/reset` - Reset settings

**Other Routes (1 route)**:
- `/documentation` - Documentation page

---

## Blueprint Structure

### Proposed Organization

```
src/dashboard/
├── blueprints/
│   ├── __init__.py           # Blueprint registration helper
│   ├── api.py                # API routes (4 routes, ~150 lines)
│   ├── dashboard.py          # Dashboard routes (5 routes, ~350 lines)
│   ├── export.py             # Export routes (8 routes, ~300 lines)
│   └── settings.py           # Settings routes (3 routes, ~100 lines)
└── app.py                    # App factory (~350 lines after extraction)

tests/dashboard/blueprints/
├── test_api.py               # API blueprint tests
├── test_dashboard.py         # Dashboard blueprint tests
├── test_export.py            # Export blueprint tests
└── test_settings.py          # Settings blueprint tests
```

---

## Implementation Phases (4 Phases)

### Phase 1: Create Blueprint Infrastructure (2 hours)

**Goal**: Set up blueprint structure and helper utilities

#### Step 1.1: Create Blueprint Base Module
- Create `src/dashboard/blueprints/__init__.py`
- Add blueprint registration helper function
- Add URL prefix configuration

#### Step 1.2: Create Test Infrastructure
- Create `tests/dashboard/blueprints/` directory
- Set up test fixtures for Flask app with blueprints
- Create shared test utilities

**Verification**:
- Directory structure created
- Helper functions tested
- No impact on existing functionality

---

### Phase 2: Extract API Blueprint (3 hours)

**Goal**: Move all API routes to dedicated blueprint

#### Step 2.1: Create API Blueprint
Create `src/dashboard/blueprints/api.py`:
- Move `/api/metrics` route
- Move `/api/refresh` route
- Move `/api/reload-cache` route
- Move `/collect` route

**Dependencies**:
- `refresh_metrics()` function (keep in app.py or move to service)
- `metrics_cache` (pass as dependency or use Flask.g)
- `cache_service`
- `config`

#### Step 2.2: Update app.py
- Register API blueprint
- Remove extracted routes
- Update imports

#### Step 2.3: Create Tests
Create `tests/dashboard/blueprints/test_api.py`:
- Test each API endpoint
- Test authentication
- Test error handling
- Test cache refresh logic

**Lines Extracted**: ~150 lines

**Verification**:
- All API routes work at same URLs
- Authentication still enforced
- All tests pass

---

### Phase 3: Extract Export Blueprint (3 hours)

**Goal**: Move all export routes to dedicated blueprint

#### Step 3.1: Create Export Blueprint
Create `src/dashboard/blueprints/export.py`:
- Move 8 export routes (team, person, comparison, team-members)
- Import `create_csv_response`, `create_json_response` from utils
- Import `validate_identifier` from utils

**Dependencies**:
- `metrics_cache`
- Export utility functions (already extracted in Week 7)
- Validation utilities

#### Step 3.2: Update app.py
- Register export blueprint with `/api/export` prefix
- Remove extracted routes

#### Step 3.3: Create Tests
Create `tests/dashboard/blueprints/test_export.py`:
- Test all 8 export endpoints
- Test CSV format
- Test JSON format
- Test error cases (missing data, invalid names)

**Lines Extracted**: ~300 lines

**Verification**:
- All export URLs unchanged
- CSV/JSON downloads work
- Authentication enforced
- All tests pass

---

### Phase 4: Extract Dashboard and Settings Blueprints (4 hours)

**Goal**: Move remaining routes to appropriate blueprints

#### Step 4.1: Create Dashboard Blueprint
Create `src/dashboard/blueprints/dashboard.py`:
- Move `/` (index) route
- Move `/team/<team_name>` route
- Move `/person/<username>` route
- Move `/team/<team_name>/compare` route
- Move `/comparison` route
- Move `/documentation` route (6 routes total)

**Dependencies**:
- `metrics_cache`
- `cache_service`
- `get_config()`
- `get_display_name()`
- Template rendering

#### Step 4.2: Create Settings Blueprint
Create `src/dashboard/blueprints/settings.py`:
- Move `/settings` route
- Move `/settings/save` route
- Move `/settings/reset` route

**Dependencies**:
- `config`
- Performance scoring utilities
- YAML file operations

#### Step 4.3: Update app.py
- Register both blueprints
- Remove all extracted routes
- Keep only initialization, config, and context processors

#### Step 4.4: Create Tests
Create `tests/dashboard/blueprints/test_dashboard.py`:
- Test all dashboard routes
- Test template rendering
- Test date range switching
- Test environment switching

Create `tests/dashboard/blueprints/test_settings.py`:
- Test settings page
- Test save functionality
- Test reset functionality

**Lines Extracted**: ~450 lines

**Verification**:
- All dashboard pages work
- Settings functionality preserved
- All tests pass
- URL structure unchanged

---

## Final app.py Structure (~350 lines)

After extraction, `app.py` should contain:

1. **Imports** (~30 lines)
2. **Logger and Service Initialization** (~20 lines)
3. **Flask App Creation** (~10 lines)
4. **Context Processors** (~40 lines)
5. **Global Cache and Helper Functions** (~50 lines)
6. **Blueprint Registration** (~20 lines)
7. **Authentication Setup** (~10 lines)
8. **Error Handlers** (~50 lines)
9. **Main Guard** (~10 lines)

Total: ~350 lines (down from 1,190 lines)

---

## Blueprint Design Patterns

### Dependency Injection Pattern

**Before (in app.py)**:
```python
@app.route("/api/metrics")
def api_metrics():
    config = get_config()  # Global function
    # Uses global metrics_cache
    return jsonify(metrics_cache["data"])
```

**After (in blueprint)**:
```python
from flask import current_app, Blueprint

api_bp = Blueprint('api', __name__)

@api_bp.route("/metrics")
def api_metrics():
    config = current_app.config['APP_CONFIG']
    cache = current_app.extensions['metrics_cache']
    return jsonify(cache["data"])
```

### Blueprint Registration

**In app.py**:
```python
from src.dashboard.blueprints import register_blueprints

app = Flask(__name__)

# Store dependencies in app context
app.config['APP_CONFIG'] = config
app.extensions['metrics_cache'] = metrics_cache
app.extensions['cache_service'] = cache_service

# Register all blueprints
register_blueprints(app)
```

**In blueprints/__init__.py**:
```python
def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    from .api import api_bp
    from .dashboard import dashboard_bp
    from .export import export_bp
    from .settings import settings_bp

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    app.register_blueprint(dashboard_bp)  # No prefix (root level)
    app.register_blueprint(settings_bp, url_prefix='/settings')
```

---

## Testing Strategy

### Unit Tests (per blueprint)

Each blueprint test file should verify:
1. **Route accessibility** - All routes respond
2. **Authentication** - Protected routes require auth
3. **Template rendering** - Correct templates used
4. **Data handling** - Proper data passed to templates
5. **Error handling** - 404s, 500s handled correctly

### Integration Tests

Verify:
1. **Blueprint registration** - All blueprints loaded
2. **URL generation** - `url_for()` works correctly
3. **Cross-blueprint navigation** - Links between pages work
4. **Shared context** - Context processors available in all blueprints

### Regression Tests

Run existing test suite to ensure:
- All 774 existing tests pass
- No URL changes (backward compatibility)
- Authentication still works
- Export functionality preserved

---

## Risk Mitigation

### Circular Import Prevention

**Problem**: Blueprints might need functions from app.py

**Solution**:
- Keep shared utilities in separate modules (already done in Week 7)
- Use Flask's `current_app` for accessing config/extensions
- Pass dependencies via blueprint registration

### Global State Management

**Problem**: `metrics_cache` is global variable in app.py

**Solutions**:
1. **Short-term**: Store in `app.extensions`
2. **Long-term** (Week 11): Use app factory with dependency injection

### URL Compatibility

**Problem**: Blueprint URL prefixes might break existing URLs

**Solution**:
- Carefully choose prefixes that match existing patterns
- `/api` routes stay under `/api`
- Dashboard routes stay at root
- Test all URLs before/after migration

---

## Success Metrics

### Code Organization
- **app.py**: 1,190 → ~350 lines (**-840 lines**, -71% reduction)
- **New blueprints**: 4 files (~900 lines total)
- **Blueprint tests**: 4 test files (~400 lines)

### Test Coverage
- **All 774+ tests passing** (no regressions)
- **40+ new blueprint tests** (10 per blueprint)
- **Route coverage**: 100% (all 21 routes tested)

### Quality Improvements
- ✅ **Better code organization** - Routes grouped by function
- ✅ **Enhanced modularity** - Independent blueprint development
- ✅ **Improved testability** - Isolated blueprint testing
- ✅ **Team collaboration** - Multiple developers per blueprint
- ✅ **Cleaner app.py** - 71% smaller, just initialization

---

## Estimated Effort: 12-14 hours (~2 days)

| Phase | Hours | Complexity | Lines Extracted |
|-------|-------|------------|-----------------|
| Phase 1: Infrastructure | 2h | Low | 0 (setup) |
| Phase 2: API Blueprint | 3h | Medium | ~150 |
| Phase 3: Export Blueprint | 3h | Medium | ~300 |
| Phase 4: Dashboard + Settings | 4h | High | ~450 |
| Testing/verification | 2-3h | Medium | N/A |

**Note**: Based on Week 7 efficiency (completed 16-19 hour estimate in actual implementation), actual time may be lower.

---

## Rollback Plan

1. **Git strategy**: Work in branch `week8-blueprint-extraction`
2. **Commit strategy**: Commit after each phase
3. **Tags**: `week8-phase1`, `week8-phase2`, etc.
4. **Rollback**: Revert to previous commit if tests fail

---

## Dependencies

**From Week 7** (already available):
- ✅ CacheService
- ✅ MetricsRefreshService
- ✅ Export utilities (create_csv_response, create_json_response)
- ✅ Validation utilities (validate_identifier)
- ✅ Error handling utilities (handle_api_error)

**New dependencies** (to be created):
- Blueprint registration helper
- Blueprint test fixtures
- Dependency injection helpers

---

## Post-Week 8 Benefits

### Immediate Benefits
1. **71% smaller app.py** - Easier to understand and maintain
2. **Modular routes** - Independent development and testing
3. **Clear boundaries** - Separation of concerns enforced
4. **Better testing** - Isolated blueprint tests

### Foundation for Future Weeks
- **Week 9**: Enhanced blueprint features (error handlers, context processors per blueprint)
- **Week 10**: API versioning using blueprints
- **Week 11**: App factory pattern with blueprint registration
- **Week 12**: Micro-frontend architecture (blueprints as separate apps)

---

## Acceptance Criteria

Before marking Week 8 complete:

- [ ] All 4 blueprints created and registered
- [ ] app.py reduced to ~350 lines (71% reduction)
- [ ] All 21 routes working at original URLs
- [ ] All 774+ tests passing (no regressions)
- [ ] 40+ new blueprint tests added
- [ ] Authentication working on all protected routes
- [ ] Export functionality preserved
- [ ] Settings functionality preserved
- [ ] CI/CD pipeline passing (all checks green)
- [ ] Documentation updated (CLAUDE.md)

---

## Next Steps After Week 8

With blueprints established:

1. **Week 9**: Blueprint enhancement (per-blueprint error handlers, middleware)
2. **Week 10**: API versioning (v1/v2 blueprints)
3. **Week 11**: App factory pattern (testable configuration)
4. **Week 12**: Production deployment optimization

---

**Week 8 Objective**: Transform monolithic `app.py` into modular, maintainable blueprints while maintaining 100% backward compatibility and achieving 71% size reduction.
