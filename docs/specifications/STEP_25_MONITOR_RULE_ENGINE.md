# Step 25 — Monitor Rule Engine

**Status:** FREEZE CANDIDATE  
**Depends on:** Step 24 — FROZEN  
**Date:** 2026-07-27

## 1. Purpose

Step 25 persists and continuously evaluates the matching semantics frozen by
Step 24:

```text
DocumentMatchCriteria
        ↓
immutable Monitor revision
        ↓
active evaluation
        ↓
idempotent Monitor match
```

Step 25 does not send notifications. Step 26 owns alerts, delivery attempts,
destinations, and ntfy integration.

## 2. Ownership

A Monitor is installation-level operator configuration owned by exactly one
Coverage Profile. Identity and authorization remain deferred, so Step 25 does
not invent user or tenant ownership.

```text
coverage profile
    owns operational monitoring scope

monitor
    owns identity, lifecycle, activation, and expiration policy

monitor revision
    owns one immutable versioned matching definition

monitor match
    records that a document satisfied a monitor at least once

evaluation run
    records one auditable execution
```

Canonical topics, geographies, entities, semantic document types, content
formats, languages, sources, and source types remain globally owned.

## 3. Criteria Version 1

Criteria version 1 is the frozen Step 24 contract:

```text
coverage profile
geography IDs with explicit descendant inclusion
topic IDs with explicit descendant inclusion
entity IDs and entity roles
semantic document-type IDs with explicit descendant inclusion
content-format slugs
source IDs
source-type slugs with explicit descendant inclusion
effective language tags
minimum assertion confidence
timezone-aware effective-document cutoff
one literal case-insensitive keyword or phrase
```

Normalized selector tables preserve reference integrity. Selector JSON in
Monitor metadata is prohibited.

Boolean expressions and regular expressions require a separately reviewed,
versioned rule language with complexity limits and deterministic semantics.
They are not silently interpreted by criteria version 1.

## 4. Selection Algebra

The Step 24 algebra remains frozen:

```text
within one dimension                 OR
across constrained dimensions       AND
profile scope and Monitor criteria  AND
```

Hierarchy expansion is explicit and read-time. Classification predicates
match active assertions only. A confidence threshold applies to the assertion
that satisfies its dimension.

A Monitor with no explicit criteria would match every document in its
Coverage Profile. Activation therefore requires an explicit
`match_all_in_profile` acknowledgement.

## 5. Revision Policy

Monitor revisions are immutable:

```text
create Monitor       revision 1
edit draft/paused    create revision N + 1
activate             execute current revision
```

An active Monitor cannot be edited in place. It must be paused first. Prior
revisions and matches remain auditable.

The Monitor row records the current revision number through a deferred
composite foreign key. A transaction cannot commit with a nonexistent current
revision.

## 6. Lifecycle

```text
draft ──────→ active ──────→ paused
  │             │              │
  │             ├──→ expired   └──→ active
  │             │
  └─────────────┴──────────────→ archived
```

Rules:

```text
only active, unexpired Monitors execute
inactive Coverage Profiles cannot activate or execute Monitors
expiration is timezone-aware
archived is terminal
deletion is not a normal lifecycle operation
criteria edits require draft or paused status
```

An expired Monitor may be reactivated only after its expiration policy is
changed to a future time or removed.

## 7. Evaluation

Step 25 supports:

```text
activation backfill when explicitly enabled
single-document ingestion evaluation
post-classification/enrichment reevaluation
manual Monitor backfill
manual single-document evaluation
```

Evaluation calls `build_document_match_plan`; no second matcher is allowed.

Ingestion durability remains stronger than Monitor evaluation. Monitor
evaluation failure is recorded and logged but must not discard a valid raw
document or successful classification.

## 8. Match Idempotency

One Monitor and document pair has at most one `monitor_matches` row.

Repeated matching evaluations:

```text
preserve first match time and first revision
update last match time and last revision
increment observation count
never create a second logical match
```

Step 26 may create an alert candidate only when Step 25 reports a newly
inserted Monitor match. Repeated evaluation alone does not create repeated
alerts.

Matches remain historical if later revisions no longer match. Step 25 does
not rewrite history or claim that a past match never occurred.

## 9. Migration and Downgrade

The migration creates no seeded Monitor. Downgrade is permitted only when all
Monitor, revision, evaluation, and match tables are empty. Meaningful operator
configuration or history blocks destructive downgrade.

## 10. Freeze-Candidate Proofs

The freeze candidate must directly prove:

```text
normalized canonical references and immutable revisions
database-valid current revision
profile ownership and inactive-profile rejection
explicit profile-wide activation acknowledgement
legal and illegal lifecycle transitions
active expiration behavior
active Monitor edit rejection and paused revision creation
Step 24 criteria reconstruction without semantic loss
document-only matcher reuse
activation backfill opt-in behavior
new and enriched document evaluation
one logical match under repeated and concurrent evaluation
first/last revision and time accumulation
failed evaluation history without ingestion rollback
archive terminal behavior
API and saved Monitor UI behavior
lossless empty downgrade and destructive-downgrade rejection
complete repository regression and zero Alembic drift
```

Candidate validation on PostgreSQL 17.10:

```text
Step 25 schema verification                              passed
13 expected Monitor tables                              present
invalid current-revision references                          0
duplicate logical matches                                    0
selector JSON columns                                        0
premature Step 26 tables                                     0
repository tests                                    175 passed
Alembic drift operations                                     0
empty downgrade and re-upgrade                          passed
destructive-downgrade refusal                           passed
```

This status is not a freeze declaration. Step 25 remains subject to a separate
formal freeze review.
