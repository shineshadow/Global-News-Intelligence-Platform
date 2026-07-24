# Implementation Guide

**Project:** Global News Intelligence Platform  
**Document:** `IMPLEMENTATION.md`  
**Status:** Living Implementation Guide / Placeholder

---

## Purpose

This document should translate architectural specifications into an ordered, testable implementation plan without redefining architecture.

Authoritative design sources:

```text
MASTER_TECHNICAL_SPECIFICATION.md
DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md
INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md
STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md
SOURCE_ACQUISITION_TECHNICAL_SPECIFICATION.md
AI_ROUTING_TECHNICAL_SPECIFICATION.md
```

---

## Required Structure for Future Work

Every implementation step should record:

```text
step number
objective
dependencies
files/modules affected
database migration required?
API changes?
worker changes?
UI changes?
configuration changes?
tests required
acceptance criteria
rollback considerations
operational verification
```

---

## Current Major Implementation Tracks

```text
Core ingestion reliability
Unified classification foundation
Monitoring/rules
Expanded acquisition
YouTube/transcripts
Local AI + routing
Embeddings/search
Story intelligence
Intelligence Calendar
Advanced novelty/event intelligence
```

---

## Implementation Guardrails

- PostgreSQL remains authoritative.
- Migrations are additive and reversible where practical.
- Original documents are preserved.
- New workers/tasks must be idempotent.
- New endpoint types should reuse Source/SourceEndpoint architecture.
- AI output must retain provenance.
- UI should call the service layer directly in server-rendered workflows.
- No major dependency should be introduced without an explicit architecture decision or benchmark.

---

## Definition of Done Template

```text
[ ] migration applied
[ ] models/repositories/services complete
[ ] API or Web routes complete
[ ] workers/tasks complete
[ ] unit tests
[ ] integration tests
[ ] lifecycle/failure tests
[ ] operational metrics
[ ] documentation updated
[ ] rollback/recovery checked
```
