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
Identity, feedback, and Attention
Semantic Watch
Video intelligence and explicit processing
Intelligence Calendar
Advanced novelty/event intelligence
```

Current Calendar implementation sequence:

```text
Calendar Foundation Audit                           frozen
Calendar Phase 1 — Manual Calendar                  frozen
Calendar Phase 2 architecture                       frozen
Calendar Phase 2 corrective/persistence migrations  frozen
Calendar Phase 2 autonomous services/workers        frozen
Calendar Phase 2 structured extraction adapter      frozen
Calendar Phase 2 Administrative Queue/API/UI         frozen
Calendar Phase 2 occurrence-policy controls          frozen
Calendar Phase 2 formal freeze review                 passed
```

Calendar Phase 2 is governed by
`../specifications/INTELLIGENCE_CALENDAR_PHASE_2_ARCHITECTURE.md`. Normal
validation and enrichment must be autonomous; administrative review is an
exception path only.

The formal review passed all 44 required proofs, 49 focused Calendar tests,
three migration-safety tests, all 243 repository tests, Alembic head and
zero-drift checks, scoped lint, and live operational smoke checks. Normal
Event detail exposes read-only effective-state provenance; advanced evidence,
attempt history, and operator decisions remain in the separate
Administrative Queue.

Current main-track sequence:

```text
Steps 24 through 26                                  frozen
Calendar Foundation through Phase 2                  frozen
Phase 3.1 shared Source Acquisition architecture     frozen
Phase 3 corrective/Artifact foundation               frozen
Phase 3 signature importer/deletion-first runtime    implemented candidate
Phase 3 inspection sandbox/mandatory scanner         implemented candidate
Phase 3 outbound egress guard                         implemented candidate
Phase 3 leases/adapter registry/secrets/rate policy  implemented candidate
UI foundation and UX governance                      draft candidate
Phase 3 adapters and acquisition-health UI           after security boundary
Phase 3 formal implementation review                 final gate
```

Phase 3.1 is governed by
`../specifications/PHASE_3_SHARED_SOURCE_ACQUISITION_ARCHITECTURE.md`.
The narrower foundation freeze and its proof results are recorded in
`../specifications/PHASE_3_ARTIFACT_FOUNDATION_FREEZE_REVIEW.md`.
The repository-pinned signature importer and deletion-first runtime candidate
are recorded in
`../specifications/PHASE_3_SIGNATURE_IMPORTER_AND_DELETION_RUNTIME.md`.
The Bubblewrap/seccomp inspection boundary and mandatory ClamAV integration
candidate are recorded in
`../specifications/PHASE_3_INSPECTION_SANDBOX_AND_MANDATORY_SCANNER.md`.
The IP-pinned outbound HTTP and SSRF boundary candidate is recorded in
`../specifications/PHASE_3_OUTBOUND_EGRESS_GUARD.md`.
The PostgreSQL-authoritative adapter, lease, secret-reference, and
hierarchical rate-control candidate is recorded in
`../specifications/PHASE_3_ACQUISITION_CONTROL_RUNTIME.md`.

---

## Implementation Guardrails

- PostgreSQL remains authoritative.
- Canonical instants remain timezone-aware in storage. Every User-facing UI
  date/time must use the shared User-local American formatter governed by
  `../specifications/AMERICAN_DATE_TIME_DISPLAY_STANDARD.md`; features may not
  introduce private UTC, ISO, 24-hour, or seconds-bearing UI formats.
- Migrations are additive and reversible where practical.
- Accepted canonical originals are preserved. Suspicious or unverifiable
  acquisition bytes are deleted immediately and never become Documents,
  Artifacts, evidence, exports, or backups.
- New workers/tasks must be idempotent.
- New endpoint types should reuse Source/SourceEndpoint architecture.
- Acquisition adapters must use the shared registry, Artifact catalog,
  deletion-first security boundary, secret references, and rate policy.
- Untrusted retrieval and inspection must use the shared outbound egress
  guard, bounded staging, mandatory scanner, and credential-free sandbox.
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
