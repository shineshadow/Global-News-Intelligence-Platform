# Phase 3 Formal Implementation Review

**Review date:** 2026-08-03  
**Outcome:** BLOCKED — IMPLEMENTATION NOT FROZEN  
**Reviewed Alembic head:** `d3f5a7b9c1e4`

> **Post-review owner-authority amendment (2026-08-03):** The owner rejected
> unapproved non-configurable restrictions in the frozen architecture. The
> governing proof language is now amended by
> `OWNER_AUTHORITY_AND_CONFIGURATION_STANDARD.md`, with implementation head
> `f6a8c2d4e901`. The 50/10 disposition below remains the historical result of
> the `d3f5a7b9c1e4` review and must not be presented as a review of the amended
> matrix. The outcome remains blocked pending a new formal review.

> **Post-review archive remediation candidate (2026-08-04):** Migration
> `a9c1e3f5b7d2` and
> `PHASE_3_ARCHIVE_TREE_INSPECTION_AND_PROMOTION.md` now provide recursive
> sandbox extraction, complete-tree deletion/promotion, archive controls, and
> nested Artifact provenance for proofs 23-26. This is implementation evidence,
> not a retroactive change to the historical disposition below. The proofs and
> review outcome remain blocked until the complete formal review is rerun.

## Decision

Phase 3 does not yet pass its formal implementation freeze. The repository is
stable, the implemented adapters pass their regression gates, and the exact
CISA RSS canary has proven live acquisition and rollback parity. However, 10
of the 60 mandatory proofs in the frozen architecture are not yet complete.

This is a freeze decision, not a rollback decision. Endpoint `47` may remain
on its already-reviewed `feed_parser v1` configuration, and the unactivated
adapter registrations may remain installed. The Phase 3 implementation must
continue to be described as a candidate until every open proof below passes.

## Governing Standard

The review used the 60-item Required Proof Matrix in
`PHASE_3_SHARED_SOURCE_ACQUISITION_ARCHITECTURE.md`. A mandatory proof cannot
be waived because its schema exists, an adjacent component passes, or the
capability has not yet been activated. Catalog recognition and persistence
scaffolding are not implementation proof.

## Evidence Reviewed

The audit covered:

- all Phase 3 migrations through `d3f5a7b9c1e4`;
- Artifact models, signature import, inspection sandbox, scanner, egress,
  lease, secret, rate, worker, dispatch, health, and cutover services;
- RSS/Atom, RSSHub, RSS-Bridge, direct JSON, direct HTML,
  changedetection.io, and Playwright adapter implementations;
- focused migration, model, service, adapter, worker, and web tests;
- every Phase 3 package specification and its deliberate exclusions; and
- the retained live CISA RSS activation, scheduled/manual acquisition,
  rollback, legacy recovery, and versioned reactivation evidence.

## Proof Matrix Disposition

The following 50 obligations have implementation and test or operational
evidence sufficient for this review:

```text
1-11    identity, exact registry compatibility, catalog separation,
        external mappings, bootstrap signatures, and atomic import
13-22   immutable mapping history, acceptance provenance, deletion-first
        mismatch/failure handling, hidden security controls, terminal formats
27-29   durable lease, PostgreSQL replay authority, and early replay return
31-33   HTTP 304 behavior, secret non-persistence/redaction boundaries, and
        credential-scoped quota identity
35-38   rate failure separation, audited cutover mutation, immutable rejection,
        and no transaction held across retrieval/inspection
40-47   catalog honesty, RSS compatibility, repository/live gates, sandbox
        isolation/failure closure, SSRF/internal-service controls, byte limits
49-56   database-enforced secret-slot contracts, fail-closed resolution,
        every-bucket reservation, database request authority, separated health
        dimensions, prospective migration, redaction, and exact
        repository-pinned bootstrap
58-60   no hash bypass, immutable forward Artifact history, and guarded downgrade
```

The grouped disposition is traceable to:

```text
Artifact foundation
  tests/models/test_phase3_artifact_foundation.py
  tests/migrations/test_phase3_artifact_migration.py

Signature, deletion, sandbox, and scanning
  tests/services/test_artifact_signature_service.py
  tests/services/test_artifact_security_service.py
  tests/services/test_artifact_inspection_sandbox.py

Egress, secrets, leases, and rate authority
  tests/services/test_outbound_egress_service.py
  tests/services/test_acquisition_control_services.py

Worker, dispatch, health, and cutover
  tests/services/test_acquisition_worker_service.py
  tests/services/test_acquisition_dispatch_service.py
  tests/services/test_acquisition_health_service.py
  tests/migrations/test_phase3_feed_cutover_migration.py

Adapters and non-activating migrations
  tests/ingestion/test_feed_parser_adapter.py
  tests/ingestion/test_generated_feed_adapters.py
  tests/ingestion/test_direct_listing_adapters.py
  tests/ingestion/test_monitored_listing_adapters.py
  tests/migrations/test_phase3_*_migration.py

Live operation
  PHASE_3_LIVE_FEED_CANARY_PARITY_REVIEW.md
```

## Open Mandatory Proofs

| Proof | Status | Formal-review finding |
|---:|---|---|
| 12 | Blocked | The bootstrap importer is atomic, but there is no later authority-release candidate lifecycle or direct proof that a failed replacement preserves an already-active release. |
| 23 | Blocked | Signatures recognize compression/container envelopes, but there is no container-aware recursive identification of valid compound payloads. |
| 24 | Blocked | There is no complete-tree acceptance transaction that deletes an acquired archive tree when one member is rejected. |
| 25 | Blocked | Traversal, expansion bomb, link, device-file, depth, member-count, and ratio controls are not implemented or tested. |
| 26 | Blocked | The schema can store `parent_artifact_id` and `member_path`, but the runtime does not create accepted nested Artifact provenance. |
| 30 | Proof gap | The ingestion service deliberately retains old validators on a partial item result, but no direct regression test proves that contract. |
| 39 | Proof gap | `verified_empty` projection exists, but no direct test proves that a valid empty endpoint can remain healthy. |
| 48 | Blocked | Filesystem promotion re-hashes and publishes atomically. No object-storage promotion backend implements the frozen opaque-staging, checksum, committed-pointer, and cleanup contract. |
| 57 | Blocked | Only the reviewed repository bootstrap can be imported. The required guarded, scanned, regression-tested lifecycle for later untrusted authority releases is absent. |

The archive gap is explicitly corroborated by the deliberate exclusions in
the signature-runtime, inspection-sandbox, and feed-worker package documents.
The remaining findings come from tracing the composed runtime rather than
judging persistence models in isolation.

## Verification Results

The blocked outcome is not caused by a failing repository gate:

```text
guarded migration-safety suite                         20 passed
guarded non-migration repository suite                394 passed
Alembic current                               d3f5a7b9c1e4 (head)
Alembic schema drift                                      none
Phase 3 branch Python Ruff lint                            passed
Phase 3 branch Python Ruff format                          passed
Python compilation                                        passed
whitespace check                                           passed
initial /var inode use                                        12%
post-migration /var inode use                                 14%
final /var inode use                                          51%
```

The current repository-wide Ruff configuration also reports an older
whole-repository formatting backlog outside the Phase 3 branch scope. That
baseline was not rewritten during this review and is not the cause of the
freeze decision.

## Operational Scope Retained

The live proof remains limited to CISA endpoint `47` using the exact
`feed/rss/feed_parser` tuple. It proves one-endpoint activation, Artifact
acceptance, stable Documents, scheduled/manual execution, rollback, legacy
recovery, and versioned reactivation.

It does not prove live parity for RSSHub, RSS-Bridge, direct JSON, direct HTML,
changedetection.io, or Playwright. Their migrations remain correctly
non-activating, and none should be presented as live-approved by this review.

## Required Remediation Sequence

1. Implement recursive container/archive inspection and all-or-nothing
   Artifact-tree promotion for proofs 23-26. **Implemented candidate at
   `a9c1e3f5b7d2`; formal rerun pending.**
2. Implement the object-storage canonical promotion contract for proof 48.
3. Implement the guarded later-authority release lifecycle and active-release
   preservation tests for proofs 12 and 57.
4. Add direct partial-validator and verified-empty-health regressions for
   proofs 30 and 39.
5. Rerun the complete guarded suite, Alembic head/drift, scoped lint/format,
   operational smokes, and this formal review.

Only the final rerun may change the outcome to `PASS — IMPLEMENTATION FROZEN`.
