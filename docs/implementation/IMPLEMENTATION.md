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
Phase 3 feed adapter/shared acquisition worker       implemented candidate
UI foundation and UX governance                      draft candidate
Phase 3 controlled feed cutover/acquisition health   implemented candidate
Phase 3 live feed canary/parity review                passed
Phase 3 RSSHub/RSS-Bridge adapters                    implemented candidate
Phase 3 direct HTTP/listing extraction                implemented candidate
Phase 3 changedetection/Playwright fallback           implemented candidate
Phase 3 credential/provider rate authority            implemented candidate
Phase 3 formal implementation review                 blocked — remediation required
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
The first exact RSS/Atom adapter, shared worker composition, structural feed
inspection, and fail-closed cutover boundary are recorded in
`../specifications/PHASE_3_FEED_ADAPTER_AND_SHARED_WORKER.md`. Its migration
configures no endpoints; legacy RSS remains active only for endpoints without
an explicit Phase 3 configuration.
The bounded activation, rollback ledger, separate operational-state
projection, Acquisition Health UI, and canary procedure are recorded in
`../specifications/PHASE_3_CONTROLLED_FEED_CUTOVER_AND_ACQUISITION_HEALTH.md`.
Its migration activates no endpoints and the installation cohort limit
defaults to one.
The bounded CISA RSS activation, manual and scheduled Phase 3 acquisition,
stable Document parity, live rollback, legacy recovery poll, and versioned
reactivation proof are recorded in
`../specifications/PHASE_3_LIVE_FEED_CANARY_PARITY_REVIEW.md`. The exact
RSS/feed-parser canary passed; the cohort limit remains one and the result does
not claim parity for unreviewed feeds or remaining adapter types.
The installation-bound RSSHub and RSS-Bridge runtime adapters, exact registry
seeds, internal-service egress identity, and non-activating migration are
recorded in
`../specifications/PHASE_3_RSSHUB_AND_RSS_BRIDGE_ADAPTERS.md`. No generated
feed endpoint or internal service is configured by the repository candidate.
The public direct JSON/API and HTML listing adapters, bounded selector/path
configuration, sandbox-only extraction, and non-activating registry migration
are recorded in
`../specifications/PHASE_3_DIRECT_HTTP_AND_LISTING_EXTRACTION.md`. The package
creates no endpoint configuration or cutover and supports no authenticated API
slot or JavaScript rendering; those remain separate reviewed capabilities.
The installation-owned changedetection snapshot and disposable Playwright
renderer adapter contracts, required API-key secret slots, source/policy
attestation, and non-activating registry migration are recorded in
`../specifications/PHASE_3_CHANGEDETECTION_AND_PLAYWRIGHT_FALLBACK.md`.
The repository does not install either service, create watches/render routes,
or automatically fall back to browser acquisition.
The composed credential quota identity, every-bucket reservation, bounded
provider response parsing, durable retry authority, and rate-delay health
semantics are recorded in
`../specifications/PHASE_3_CREDENTIAL_AND_PROVIDER_RATE_AUTHORITY.md`. This
closes formal proofs 33 and 51 and implements the provider portion of proof 34;
robots acquisition and crawl enforcement remain separate required work.
The formal implementation review is recorded in
`../specifications/PHASE_3_FORMAL_IMPLEMENTATION_REVIEW.md`. The repository,
migration, lint, and live RSS gates pass, but Phase 3 is not frozen: mandatory
archive-tree inspection, robots policy enforcement, object-storage promotion,
later signature-authority updates, and two direct regression proofs remain
open. Existing live RSS approval is retained only for the exact reviewed CISA
endpoint; no unactivated adapter gains live parity from the formal review.

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
