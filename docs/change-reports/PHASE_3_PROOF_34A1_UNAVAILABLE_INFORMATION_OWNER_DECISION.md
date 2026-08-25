# Phase 3 Proof 34A.1 Unavailable Information Owner Decision

**Approver:** GNI Owner  
**Approval date:** 08-25-2026  
**Decision:** Approved  
**Scope:** Robots unavailable-evidence taxonomy, implementation strategy,
internal use, Owner information access, and future Admin UI obligation

## Decision

The Owner approves `unavailable` as an aggregate external robots decision only
when a more useful structured explanation is retained alongside it.
`unavailable` shall not become a catch-all that leaves the Owner, GNI, or an
authorized agent model without a useful reason.

The Owner approves the version-one information tuple:

```text
failure_phase
unavailable_reason
http_status, when applicable
retryable
owner_summary
```

The Owner approves these failure phases:

```text
retrieval
validation
parsing
evaluation
evidence_binding
```

The Owner approves `retryable` values `true`, `false`, and `unknown` and the
closed version-one reason taxonomy recorded in
`../specifications/ROBOTS_ACQUISITION_AND_ENFORCEMENT_STANDARD.md`.

## Information And Access Classification

The complete structured tuple, its evidence linkage, and its history are both:

```text
internal operational information
Owner information
```

Internal services, workers, diagnostics, and authorized agent models may use
the machine-readable values. That internal use does not make the information
internal-only and does not remove the Owner's right to inspect it.

Before the Admin UI exists, implemented operational, API, CLI, and database
surfaces preserve Owner access. Once distinct User and Admin interfaces exist,
the detailed unavailable-evidence information may be omitted from the User UI
but shall be presented in the Admin UI.

Admin-UI placement is not an authority grant. Missing GUI implementation is a
tracked access-surface gap, not permission to discard, hide, stop producing,
or deny the Owner access to this information.

## Presentation And Security

Machine codes remain stable and versioned. Owner labels and summaries are
generated from the same registry. Owner summaries are bounded and sanitized;
they do not contain raw exceptions, response bodies, credentials, cookies,
authorization headers, secrets, or unrestricted URL material.

The unavailable reason states why trustworthy evidence was unavailable. It
does not select the GNI response. The independently resolved Owner policy
`acquisition.robots.unavailable_action` continues to control `allow`, `delay`,
or `deny`.

## Completion Boundary

This decision authorizes the 34A.1 documentation, registry, constrained
persistence, and tests. It does not claim that Proof 34B retrieval, parsing,
evaluation, OwnerOperationResult projection, or the Admin UI is implemented.
