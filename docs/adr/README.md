# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the Team Metrics Dashboard project.

## What are ADRs?

Architecture Decision Records document important architectural decisions made during the project, including:
- The context and problem being solved
- The decision that was made
- The rationale and alternatives considered
- The consequences (positive and negative)

ADRs provide historical context for future developers and help avoid repeating past mistakes.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0000](0000-template.md) | ADR Template | Template | N/A |
| [0001](0001-application-factory-pattern.md) | Application Factory Pattern with Dependency Injection | Accepted | 2026-01-26 |
| [0002](0002-two-tier-caching-strategy.md) | Two-Tier Caching Strategy with Memory Layer | Accepted | 2026-01-26 |
| [0003](0003-clean-architecture-layers.md) | Clean Architecture with Four Layers | Accepted | 2026-01-26 |
| [0004](0004-time-offset-both-collectors.md) | Apply Time Offset to Both GitHub and Jira Collectors | Accepted | 2026-01-26 |

## Quick Links by Topic

### Architecture & Structure
- **[ADR-0003](0003-clean-architecture-layers.md)** - Clean Architecture with Four Layers
- **[ADR-0001](0001-application-factory-pattern.md)** - Application Factory Pattern with Dependency Injection

### Performance & Caching
- **[ADR-0002](0002-two-tier-caching-strategy.md)** - Two-Tier Caching Strategy with Memory Layer

### Data Collection
- **[ADR-0004](0004-time-offset-both-collectors.md)** - Apply Time Offset to Both GitHub and Jira Collectors

## Creating a New ADR

1. **Copy the template:**
   ```bash
   cp docs/adr/0000-template.md docs/adr/XXXX-your-decision.md
   ```

2. **Choose the next ADR number:**
   - Look at the index above
   - Use the next sequential number
   - Format: `0005-your-decision.md`

3. **Fill out the template:**
   - Context: What problem are you solving?
   - Decision: What did you decide?
   - Consequences: What are the tradeoffs?
   - Alternatives: What else did you consider?

4. **Update this README:**
   - Add your ADR to the index table
   - Add to quick links if appropriate
   - Sort by ADR number

5. **Commit and create PR:**
   ```bash
   git add docs/adr/XXXX-your-decision.md docs/adr/README.md
   git commit -m "docs: Add ADR-XXXX: Your Decision"
   ```

## ADR Statuses

- **Proposed:** Under discussion, not yet decided
- **Accepted:** Decision made and active
- **Deprecated:** No longer recommended but not replaced
- **Superseded:** Replaced by a newer ADR

## When to Create an ADR

Create an ADR when making decisions about:
- Architecture or design patterns
- Technology choices (frameworks, libraries)
- Data models or storage strategies
- API design
- Deployment or infrastructure changes
- Security or compliance approaches

Don't create an ADR for:
- Minor implementation details
- Obvious or standard choices
- Temporary workarounds
- Bug fixes (unless they reveal architectural issues)

## Principles

1. **Be Concise:** 1-2 pages maximum
2. **Focus on Why:** Explain the reasoning, not just what
3. **Document Alternatives:** Show what else was considered
4. **Be Honest:** Include negative consequences
5. **Keep It Updated:** Mark as Deprecated/Superseded when appropriate

## Related Documentation

- [Clean Architecture Guide](../CLEAN_ARCHITECTURE.md)
- [Architecture Roadmap](../ARCHITECTURE_ROADMAP.md)
- [Phase 1: Enhanced Cache](../PHASE1_ENHANCED_CACHE.md)
- [Phase 2: Application Factory](../PHASE2_APPLICATION_FACTORY.md)

---

**Last Updated:** 2026-01-26
