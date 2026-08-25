# Phase 3 Proof 34A.1 Unavailable Information Implementation

**Date:** 08-25-2026  
**Authority:** `PHASE_3_PROOF_34A1_UNAVAILABLE_INFORMATION_OWNER_DECISION.md`  
**Disposition:** Contract and persistence foundation implemented and tested;
Proof 34B runtime and Admin UI remain pending

## Outcome

Proof 34A.1 establishes a closed, versioned unavailable-evidence information
contract before Proof 34B begins producing robots retrieval results.
`unavailable` remains the aggregate external decision, while every unusable
snapshot and unavailable exact evaluation must retain a useful structured
reason tuple.

The code-owned registry defines:

```text
failure_phase
unavailable_reason
retryable
registered Owner label and summary
```

The registry rejects unregistered codes, invalid phase/reason combinations,
invalid HTTP status families, and summaries not generated from registered
definitions. This prevents raw exceptions or secret-bearing text from being
substituted for the bounded Owner summary.

Migration `e5a7c9d1f3b2` revises the Proof 34A head `c2f4a6b8d0e1`. It adds
structured fields to robots snapshots and evaluations, enforces completeness,
closed phases, closed phase/reason combinations, retryability values, bounded
sanitized summaries, and HTTP status families. It refuses upgrade over
unclassified historical unavailable evidence and refuses downgrade when the
new information would be lost.

## Information Access

The governing documents now classify this information as both internal
operational information and Owner information. Workers, GNI services,
diagnostics, and authorized agent models may consume the machine values. The
same facts remain available to the Owner.

The future Admin UI is required to expose the failure phase, Owner label and
stable code, HTTP status when applicable, retryability, sanitized summary,
effective unavailable action, evidence identity, and history. Admin placement
is presentation, not an authority grant. Until that UI exists, its absence is
tracked as an implementation gap and cannot justify hiding or discarding the
information.

## Verification

Verification used an isolated PostgreSQL 17 cluster:

```text
focused 34A.1 and adjacent suite       26 passed
migration safety suite                 38 passed
non-migration repository suite        435 passed
Alembic heads                          e5a7c9d1f3b2 (head)
Alembic schema drift                   none
Ruff and Python compilation            passed
Git whitespace validation              passed
/var inode use before/after             13% / 13%
```

Targeted type checking produced no diagnostics in the changed files. The
repository-wide checker continues to report pre-existing errors outside this
change surface.

## Explicit Exclusions

This target does not implement network retrieval, Protego integration,
runtime reason selection, cache/revalidation, exact runtime evaluation, gate
reconciliation, OwnerOperationResult projection, API/CLI presentation, or the
Admin UI. Those remain Proof 34B and later integration work. Proof 34 remains
incomplete.
