# Migration Plan

**Project:** Global News Intelligence Platform  
**Document:** `MIGRATION_PLAN.md`  
**Status:** Placeholder / Migration Procedure

---

## Purpose

This document defines how schema and data migrations should be planned, tested, deployed, verified, and rolled back.

---

## Migration Principles

- Use Alembic for schema changes.
- Prefer additive migrations before destructive cleanup.
- Preserve compatibility during staged deployments where practical.
- Separate schema creation from large historical backfills.
- Backfills should be resumable and idempotent.
- Never infer document geography solely from publisher country during classification backfill.
- Significant taxonomy migrations must preserve old classification history.

---

## Migration Template

```text
migration name
purpose
preconditions
schema changes
data backfill
expected row counts
indexes
estimated lock behavior
application compatibility
verification SQL
rollback strategy
post-deploy monitoring
```

---

## Classification Migration Seed Plan

1. Create canonical `geographies` and `document_geographies`.
2. Expand `document_topics` with confidence/provenance fields or replace through an additive migration.
3. Expand `document_entities` with roles/confidence/provenance.
4. Create `document_types` and `document_type_assignments`.
5. Create `classification_runs`.
6. Seed canonical topic/geography/document-type data.
7. Backfill deterministic classifications in batches.
8. Introduce UI/API filters.
9. Run AI backfill only after benchmark thresholds are approved.
10. Retire legacy classification fields only after usage audit.

## Calendar Phase 2 Frozen Migrations

**Candidate revisions:** `a7c3e9f1b204`, `b8d4f0a2c315`

The corrective and persistence migrations are frozen with Calendar Phase 2.
Clean downgrade/re-upgrade, guarded downgrade, ambiguous historical
`ai_job` refusal, regression, head, and zero-drift checks passed the formal
freeze review.

Calendar Phase 2 begins with the actor-kind correction defined in
`../specifications/INTELLIGENCE_CALENDAR_PHASE_2_ARCHITECTURE.md`.

Preflight must enumerate `actor_kind` counts across every Calendar table.
The current unapproved `ai_job` value may be replaced only when durable
provenance proves the truthful target:

```text
internal_agent
external_model
```

Any ambiguous historical `ai_job` row blocks automatic upgrade. The migration
must never guess or collapse both meanings into one value.

Recommended migration order:

1. preflight actor-kind data and refuse ambiguity;
2. replace Calendar actor constraints and schemas;
3. add inference-run, assertion-ledger, evidence-link, authority-assessment,
   authority-evidence, conflict, attempt, exception, operator-override, and
   occurrence-policy-history tables;
4. require assertion and assessment derivation methods to reference the
   frozen `semantic_assignment_methods` table;
5. add immutable same-scope assertion supersession and normalized resolution
   references;
6. add effective-projection and legal-transition enforcement;
7. deploy compatible read paths before activating the validation worker;
8. activate autonomous inference only after verification;
9. enable the Administrative Queue after exception invariants pass.

Downgrade must refuse to collapse `internal_agent` or `external_model` history
back into `ai_job`. Phase 2-owned intelligence state must be empty or
explicitly preserved by an approved forward recovery before destructive
schema removal.

## Phase 3 Corrective and Artifact Foundation — Frozen

The governing architecture in
`../specifications/PHASE_3_SHARED_SOURCE_ACQUISITION_ARCHITECTURE.md` is
frozen. The migration package is frozen after its schema, data, downgrade, and
zero-drift proofs passed formal review.

**Frozen revisions:** `c9a2f4e6b801`, `d1b3e5f7a902`

The formal foundation review passed on 2026-07-30: 11 focused model/schema/data
tests and three migration-safety tests passed, including clean
downgrade/re-upgrade, guarded refusal paths, and zero Alembic drift. The
complete repository regression also passed with 263 tests. The authoritative
review record is
`../specifications/PHASE_3_ARTIFACT_FOUNDATION_FREEZE_REVIEW.md`.

The corrective and Artifact-foundation package now includes:

```text
versioned endpoint-type, acquisition-method, and platform catalog additions
guarded prospective inactivation of podcast/IMAP/POP3/FTP/SFTP values
authority-backed Artifact Format catalogs and external mappings
empty versioned signature-release and signature persistence
content-addressed payloads, immutable Acquisition Artifact versions,
observations, and post-deletion Artifact Rejections
```

The seed installs 74 canonical format identities with authority labels. Broad
family and fallback values are non-terminal and cannot back an accepted
payload. Exact external identifiers, media types, extensions, aliases,
relationships, and detector signatures are deliberately empty until the
repository-pinned authority importer populates them; the migration does not
invent mappings or imply that extensions establish identity.

No existing Document becomes an Artifact. A referenced legacy endpoint value
blocks prospective inactivation, and any accepted/rejected Artifact,
signature/mapping history, custom format, or changed seed blocks destructive
downgrade. Accepted payloads, logical resource versions, and repeated
observations are separate immutable records.

Later Phase 3 packages add:

```text
repository-pinned signature release importer and detection corpus
mandatory scanner and deletion-first identification runtime
outbound egress/SSRF policy and isolated inspection-sandbox configuration
expanded endpoint health and history
```

The importer, deletion-first runtime, scanner/sandbox, outbound egress guard,
adapter registry, durable leases, global secret references, and hierarchical
rate authority are now implemented candidates. They remain subject to the
formal Phase 3 implementation review.

Historical catalog references must remain valid. Security-rejected bytes are
never migration inputs, stored Artifacts, or Documents. Downgrade is blocked
while any Phase 3-owned accepted bytes, history, configuration, policy, or
custom mapping exists.
