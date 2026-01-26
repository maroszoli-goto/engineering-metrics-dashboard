# ADR-0003: Clean Architecture with Four Layers

**Status:** Accepted
**Date:** 2026-01-26
**Deciders:** Development Team, Claude
**Technical Story:** Phase 3 - Clean Architecture Foundation

---

## Context

As the codebase grew, we needed a clear architectural structure to maintain code quality, testability, and maintainability. Without formal architecture:

**Problems:**
1. **Unclear Boundaries:** No clear separation between HTTP handling, business logic, and data access
2. **Tight Coupling:** Components directly importing from unrelated modules
3. **Hard to Test:** Business logic mixed with I/O operations
4. **Difficult Onboarding:** New developers unsure where to add code
5. **Violations Uncaught:** No automated enforcement of architecture rules

**Current Structure (Before):**
```
src/
├── dashboard/     # Flask routes + templates (mixed concerns)
├── models/        # Some business logic (good)
├── collectors/    # API clients (good)
└── utils/         # Everything else (catch-all)
```

**Goals:**
- Establish clear layer boundaries
- Make dependencies explicit and testable
- Enable parallel development (different layers)
- Support long-term maintainability
- Provide onboarding guide

## Decision

Adopt **Clean Architecture** with four distinct layers, inspired by Robert C. Martin's principles.

### Layer Structure
```
Presentation (blueprints/) → Application (services/) → Domain (models/)
                                ↓
                         Infrastructure (collectors/, utils/)
```

### Layer Definitions

**1. Presentation Layer** (`src/dashboard/blueprints/`, `templates/`, `static/`)
- **Responsibility:** HTTP handling, routing, templates, user input
- **Dependencies:** Can import Application Layer only
- **Examples:** Flask blueprints, Jinja templates, CSS/JS

**2. Application Layer** (`src/dashboard/services/`)
- **Responsibility:** Use cases, orchestration, services, DI
- **Dependencies:** Can import Domain and Infrastructure
- **Examples:** `CacheService`, `MetricsRefreshService`, `ServiceContainer`

**3. Domain Layer** (`src/models/`)
- **Responsibility:** Business logic, calculations, domain rules
- **Dependencies:** NONE (pure Python, standard library only)
- **Examples:** `MetricsCalculator`, `DORAMetrics`, `PerformanceScorer`

**4. Infrastructure Layer** (`src/collectors/`, `src/utils/`, `src/config.py`)
- **Responsibility:** External APIs, file I/O, configuration, utilities
- **Dependencies:** Can import Domain (models only) and external libs
- **Examples:** `GitHubGraphQLCollector`, `JiraCollector`, date utilities

### Dependency Rules

**Allowed:**
- Presentation → Application ✅
- Application → Domain, Infrastructure ✅
- Domain → Nothing ✅
- Infrastructure → Domain (models only) ✅

**Forbidden:**
- Presentation → Infrastructure ❌
- Presentation → Domain ❌
- Domain → Any layer ❌
- Infrastructure → Presentation ❌
- Infrastructure → Application ❌

### Enforcement Strategy

1. **Documentation:** Clear architecture guide (`docs/CLEAN_ARCHITECTURE.md`)
2. **Code Reviews:** Check for violations during PR review
3. **Import Linting:** Automated enforcement via `import-linter` (future)
4. **Examples:** Provide examples of correct patterns

## Consequences

### Positive
- ✅ **Clear Boundaries:** Everyone knows where code belongs
- ✅ **Better Testability:** Domain layer easy to unit test (pure functions)
- ✅ **Easier Onboarding:** New developers have structure to follow
- ✅ **Parallel Development:** Teams can work on different layers
- ✅ **Long-term Maintainability:** Architecture prevents technical debt
- ✅ **Explicit Dependencies:** DI container makes dependencies visible

### Negative
- ⚠️ **Learning Curve:** Developers must understand layer concepts
- ⚠️ **More Discipline:** Requires following rules (not enforced yet)
- ⚠️ **Refactoring Needed:** Some existing code violates layers
- ⚠️ **Indirection:** May require extra classes/interfaces

### Neutral
- Some existing code violates rules (documented, will fix gradually)
- Architecture is guideline, not strict law (pragmatism over purity)
- import-linter will provide automated enforcement (future)

## Alternatives Considered

### Alternative 1: Keep Flat Structure
**Pros:**
- No changes needed
- Simple for small projects

**Cons:**
- Doesn't scale beyond ~5000 lines
- No clear organization
- Hard to test

**Why Not Chosen:** Project already at 15,000+ lines, needs structure.

### Alternative 2: MVC Pattern
**Pros:**
- Familiar pattern
- Simple three-layer model

**Cons:**
- Mixes business logic with controllers (fat controllers)
- No clear infrastructure separation
- Tight coupling common

**Why Not Chosen:** Clean Architecture provides better separation.

### Alternative 3: Hexagonal Architecture
**Pros:**
- Ports and adapters pattern
- Very pure separation

**Cons:**
- More complex (ports/adapters overhead)
- Overkill for web dashboard
- Steeper learning curve

**Why Not Chosen:** Clean Architecture strikes better balance for our needs.

### Alternative 4: Django-Style Apps
**Pros:**
- Feature-based organization
- Self-contained modules

**Cons:**
- Doesn't map to Flask patterns
- Can create duplicate code
- Unclear shared components

**Why Not Chosen:** Layer-based architecture fits Flask better.

## Implementation

**Phase 3.1: Document Architecture** ✅ Complete
- Created `docs/CLEAN_ARCHITECTURE.md`
- Defined four layers with examples
- Documented dependency rules
- Provided migration guide

**Phase 3.2: Create ADRs** ✅ In Progress
- ADR-0001: Application Factory Pattern
- ADR-0002: Two-Tier Caching Strategy
- ADR-0003: Clean Architecture (this document)
- ADR-0004: Time Offset for Both Collectors

**Phase 3.3: Analyze Violations** ⏳ Next
- Scan codebase for layer violations
- Document each violation with impact
- Prioritize fixes by severity
- Create remediation plan

**Phase 3.4: Add Import Linting** ⏳ Future
- Research `import-linter` configuration
- Define layer contracts in `.import-linter.ini`
- Add to pre-commit hooks
- Document usage in README

**Phase 3.5: Fix Violations** ⏳ Gradual
- Fix high-priority violations first
- Update code during feature work
- No "big bang" refactor needed

**Timeline:**
- Phase 3.1-3.2: Completed 2026-01-26
- Phase 3.3: Estimated 2 hours
- Phase 3.4: Estimated 2 hours
- Phase 3.5: Ongoing (fix as we go)

## Migration Strategy

### For New Code
- Follow layer rules from day one
- Use DI container for dependencies
- Write tests at appropriate layer

### For Existing Code
- Document violations (don't hide them)
- Fix gradually during maintenance
- Prioritize high-impact violations
- Don't break working code for purity

### For Developers
- Read `docs/CLEAN_ARCHITECTURE.md` guide
- Ask "which layer?" before adding code
- Use ADRs to understand decisions
- Pragmatism over perfection

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Architecture documented | Yes | Yes | ✅ |
| ADRs created | 4 | 4 | ✅ |
| Violations analyzed | All | Pending | ⏳ |
| Import linter configured | Yes | Future | ⏳ |
| Violations fixed | High priority | Pending | ⏳ |

## References

- Architecture Guide: `docs/CLEAN_ARCHITECTURE.md`
- Related: ADR-0001 (Application Factory Pattern)
- Related: ADR-0002 (Two-Tier Caching Strategy)
- Inspiration: [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- Pattern: [Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture/)

---

**Revision History:**
- 2026-01-26: Initial decision (Accepted)
