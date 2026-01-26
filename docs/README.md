# Team Metrics Dashboard - Documentation Index

Complete documentation for the Team Metrics Dashboard project.

## Quick Start

- **Project Overview**: See main `../CLAUDE.md` for development commands and setup
- **Configuration**: See `../config/config.example.yaml` for template
- **Testing**: Run `pytest` (903 tests) and `lint-imports` (architecture validation)

## Architecture Documentation

### Clean Architecture (Phase 3 - Completed 2026-01-26)

**Core Documents**:
- **[Clean Architecture Guide](CLEAN_ARCHITECTURE.md)** ⭐
  - Four-layer architecture explained
  - Layer responsibilities and boundaries
  - Current implementation mapping
  - Refactoring guidelines
  - 417 lines of comprehensive documentation

- **[Phase 3 Completion Summary](PHASE3_COMPLETION.md)** ⭐
  - Complete timeline of Phase 3 work
  - All violations resolved (21 → 0)
  - Test results and metrics
  - Commits summary and impact analysis

**Recent Fixes (2026-01-26)**:
- **[CI/CD Fixes](CI_CD_FIXES.md)** - Fixed GitHub Actions pipeline
  - Problem 1: Missing test dependencies (requirements-dev.txt)
  - Problem 2: Python 3.9 compatibility (import-linter version constraints)
  - Result: All tests passing on CI across Python 3.9-3.13

- **[Blueprint Logging Fix](BLUEPRINT_LOGGING_FIX.md)** - Removed infrastructure imports
  - Replaced `get_logger()` with Flask's `current_app.logger`
  - Eliminated 4 architecture violations
  - Zero functional changes, 903 tests still passing

**Architecture Decision Records (ADRs)**:
Located in `architecture/adr/`:
1. **[ADR-001](architecture/adr/ADR-001-application-factory-pattern.md)** - Application Factory Pattern
2. **[ADR-002](architecture/adr/ADR-002-layered-architecture.md)** - Layered Architecture Boundaries
3. **[ADR-003](architecture/adr/ADR-003-blueprint-modular-presentation.md)** - Blueprint-Based Modular Presentation
4. **[ADR-004](architecture/adr/ADR-004-service-layer-business-logic.md)** - Service Layer for Business Logic

**Violation Analysis**:
- **[Architecture Violations](ARCHITECTURE_VIOLATIONS.md)** - Original analysis (now resolved)
  - Critical: 8 violations (ALL FIXED ✅)
  - Recommended: 8 violations (ALL FIXED ✅)
  - Acceptable: 4 violations (performance monitoring decorator)

## Feature Documentation

### Week 7-8 Refactoring
- **[Refactoring Summary](WEEKS7-8_REFACTORING_SUMMARY.md)**
  - Blueprint architecture (4 blueprints, 21 routes)
  - Service layer extraction (5 services)
  - Utility modules (7 modules)
  - 86% size reduction in app.py (1,676 → 228 lines)

### Data Collection
- **[Collection Changes](COLLECTION_CHANGES.md)** - Simplified date ranges
  - Reduced from 15+ ranges to 6 essential ranges
  - 2-4 minute automated collection
  - Multi-environment support (prod, uat)

### Authentication
- **[Authentication Guide](AUTHENTICATION.md)**
  - HTTP Basic Authentication setup
  - Password hashing with PBKDF2-SHA256
  - Multiple user support
  - 21 routes protected

### Performance Monitoring
- **[Performance Monitoring](PERFORMANCE.md)**
  - Route timing with `@timed_route` decorator
  - API call tracking
  - Analysis tools (`analyze_performance.py`)
  - Bottleneck identification

## Implementation Documentation

### DORA Metrics
- **[Lead Time Fix Results](LEAD_TIME_FIX_RESULTS.md)**
  - Four-tier filtering for accurate lead time
  - Cross-team filtering implementation
  - Before/after comparison

### Jira Integration
- **[Jira Pagination Fix](JIRA_PAGINATION_FIX.md)**
  - Smart adaptive pagination
  - 504 timeout resolution
  - Batch size optimization
  - Changelog trade-offs

- **[Jira Fix Version Troubleshooting](JIRA_FIX_VERSION_TROUBLESHOOTING.md)**
  - Release detection and filtering
  - Pattern matching for version names
  - Team member filtering

- **[Incident Filtering Change](INCIDENT_FILTERING_CHANGE.md)**
  - Updated to issue-type based filtering
  - Removed label-based detection
  - Migration guide for Jira filters

### Time Offset (UAT Environments)
- **[Time Offset Fix](TIME_OFFSET_FIX.md)** - Planned fix (see plan file)
  - Align GitHub and Jira time windows
  - UAT database snapshot handling
  - DORA metrics alignment

- **[UAT Test Results](UAT_TEST_RESULTS.md)**
  - Verification of time offset fix
  - Expected DORA metric values
  - Troubleshooting guide

## Analysis and Tools

### Analysis Commands
- **[Analysis Commands](ANALYSIS_COMMANDS.md)**
  - Python snippets for cache inspection
  - Log analysis with grep/jq
  - Manual verification checklist
  - Post-collection workflow

### Tools Directory
- **[Tools README](../tools/README.md)**
  - `verify_collection.sh` - Collection verification
  - `analyze_releases.py` - Release analysis with DORA metrics
  - `analyze_performance.py` - Performance bottleneck detection
  - `generate_password_hash.py` - Password hashing utility

## Testing Documentation

### Test Organization
```
tests/
├── unit/               # Pure logic tests (90%+ coverage target)
│   ├── test_jira_metrics.py (26 tests)
│   ├── test_dora_metrics.py (39 tests)
│   ├── test_dora_trends.py (13 tests)
│   ├── test_performance_score.py (19 tests)
│   ├── test_config.py (27 tests)
│   └── test_metrics_calculator.py (44 tests)
├── integration/        # End-to-end workflow tests (52 tests)
│   ├── test_dora_lead_time_mapping.py (19 tests)
│   ├── test_github_collection_workflows.py (21 tests)
│   ├── test_jira_collection_workflows.py (17 tests)
│   └── test_metrics_orchestration.py (14 tests)
├── collectors/         # API response parsing (35%+ coverage target)
│   ├── test_github_graphql_collector.py (27 tests)
│   ├── test_github_graphql_simple.py (15 tests)
│   ├── test_jira_collector.py (27 tests)
│   ├── test_jira_pagination.py (14 tests)
│   └── test_jira_fix_versions.py (6 tests)
├── fixtures/           # Mock data generators
└── conftest.py         # Shared pytest fixtures
```

**Test Metrics**:
- **Total Tests**: 903 (all passing)
- **Overall Coverage**: 77.03%
- **Execution Time**: ~58 seconds
- **Python Versions**: 3.9, 3.10, 3.11, 3.12, 3.13

### Running Tests
```bash
# All tests with coverage
pytest --cov

# Architecture validation
lint-imports

# Performance analysis
python tools/analyze_performance.py logs/team_metrics.log
```

## CI/CD Documentation

### GitHub Actions Workflows
Located in `.github/workflows/`:
- **code-quality.yml** - Quality checks (903 tests across 5 Python versions)
- **codeql.yml** - Security scanning (CodeQL analysis)
- **dependency-submission.yml** - Dependency tracking

**Status** (as of 2026-01-26):
- ✅ All quality checks passing
- ✅ 903 tests passing on CI
- ✅ Python 3.9-3.13 supported
- ✅ Security scan passing (Bandit)

## Configuration Documentation

### Configuration Files
- **`config/config.example.yaml`** - Template with all options
- **`config/logging.yaml`** - Logging configuration (JSON format, 10MB rotation)
- **`setup.cfg`** - Import-linter architecture contracts (6 contracts)
- **`requirements.txt`** - Production dependencies
- **`requirements-dev.txt`** - Development/testing dependencies
  - Note: Uses version constraints for Python 3.9 compatibility

### Validation
```bash
# Validate configuration
python validate_config.py

# Check architecture contracts
lint-imports
```

## Maintenance and Operations

### Daily Operations
```bash
# Collect metrics (all 6 ranges)
./scripts/collect_data.sh

# Start dashboard
python -m src.dashboard.app

# View logs
tail -f logs/team_metrics.log
```

### Weekly Maintenance
- Run `lint-imports` to verify architecture
- Review new code for violations
- Check test coverage trends

### Monthly Review
- Review ADRs for outdated decisions
- Assess new violations and update ignores
- Check performance metrics

## Status Summary (2026-01-26)

### Phase 3 Completion ✅
- ✅ All critical architecture violations resolved (21 → 0)
- ✅ 6 architecture contracts enforced via import-linter
- ✅ Comprehensive documentation (8 files, 4 ADRs)
- ✅ All 903 tests passing across Python 3.9-3.13
- ✅ CI/CD pipeline fully functional
- ✅ 77% test coverage maintained

### Recent Improvements
- **2026-01-26**: Removed logging imports from blueprints (4 violations eliminated)
- **2026-01-26**: Fixed CI/CD pipeline (requirements-dev.txt, Python 3.9 compatibility)
- **2026-01-26**: Updated documentation with Phase 3 completion details

### Architecture Metrics
| Metric | Value |
|--------|-------|
| Total Dependencies | 81 |
| Architecture Violations | 0 critical |
| Contracts Enforced | 6 |
| Acceptable Exceptions | 4 (performance decorator) |
| Test Coverage | 77.03% |
| Tests Passing | 903/903 |
| Python Versions Supported | 3.9-3.13 |

## Contributing

When making changes:

1. **Follow Clean Architecture**: Use `lint-imports` to validate
2. **Maintain Test Coverage**: Add tests for new features (target 75%+)
3. **Document Decisions**: Create ADRs for architectural changes
4. **Update Documentation**: Keep README and CLAUDE.md current
5. **Run Full Test Suite**: Ensure all 903 tests pass before committing

## Getting Help

- **Architecture Questions**: See `CLEAN_ARCHITECTURE.md` and ADRs
- **Setup Issues**: See main `CLAUDE.md` "Development Commands" section
- **Testing**: See "Testing" section in `CLAUDE.md`
- **Analysis Tools**: See `tools/README.md`
- **CI/CD Issues**: See `CI_CD_FIXES.md`

## License

See main project README for license information.
