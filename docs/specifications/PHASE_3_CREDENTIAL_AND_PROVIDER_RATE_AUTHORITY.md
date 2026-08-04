# Phase 3 Credential and Provider Rate Authority

**Implementation date:** 2026-08-03  
**Status:** IMPLEMENTED CANDIDATE  
**Reviewed Alembic head:** `d3f5a7b9c1e4`

## Scope

This package completes the composed credential-rate and provider-response
authority for the Phase 3 acquisition worker. It does not activate an endpoint,
change a production rate policy, or broaden the existing live-feed canary.

Secret resolution now returns two deliberately separated products:

- ephemeral secret values supplied only to the selected adapter; and
- sorted, non-secret `SecretReference` identifiers supplied to rate
  reservation.

Every applicable origin, platform, and credential bucket is therefore joined
to the same durable request reservation before retrieval. Credential identity
is represented as `credential:<secret_reference_id>`; neither the resolved
value nor its environment/backend locator is written to rate, run, Artifact,
or adapter provenance.

## Provider Feedback Contract

The feed, direct-listing, and monitored-listing adapters reduce response
headers to bounded, non-secret feedback. The parser recognizes only the exact
`Retry-After`, `RateLimit-Remaining`, `X-RateLimit-Remaining`,
`RateLimit-Reset`, and `X-RateLimit-Reset` fields. It retains normalized
timestamps, integer quota state, HTTP status, and valid/invalid/absent parsing
states rather than raw header values.

Valid retry and exhausted-quota reset times are applied to every bucket in the
original reservation under row locks. A prior longer hold is never shortened.
An HTTP 429 or exhausted quota without a usable reset installs the controlling
policy's bounded exponential retry plus deterministic, nonnegative jitter.
HTTP 429 and a retry-bearing HTTP 503 are treated as provider authority rather
than structural adapter failures.

The same authority-finalization transaction records sanitized observations,
finalizes the reservation, and releases the lease. A rate-controlled attempt
is persisted as `delayed` with `AcquisitionRateLimited`; it advances
`next_poll_at` without incrementing endpoint failures or replacing the last
structural error. Acquisition Health projects `rate_limited` while retaining a
current healthy last success and an already-passed Phase 3 cutover proof.

## Failure and Security Boundaries

- A missing required secret still fails closed before outbound retrieval.
- A denied pre-request reservation performs no retrieval and records a delayed
  run rather than a false endpoint failure.
- Provider feedback is not trusted to exceed the seven-day parser bound.
- Malformed throttling feedback cannot remove or shorten an existing hold.
- Raw response headers and resolved credential values are never placed in
  durable evidence.
- Manual and scheduled executions use the same reservation and feedback path
  by default; exact owner policy can authorize a manual bypass while retaining
  the reservation and audit evidence.
- Feedback remains attached to the reservation even if its policy binding is
  changed after the request was authorized.

## Deliberate Exclusion

This package implements provider response authority and now participates in
the project-wide owner policy layer. It does not retrieve,
parse, persist, or enforce `robots.txt` crawl rules. Consequently formal proof
34 remains open for its robots-policy requirement even though its
`Retry-After` and provider quota/reset portion is now implemented.

## Proof Disposition

This package closes formal proofs 33 and 51:

- proof 33: resolved credential identities participate in shared hierarchical
  quota without secret persistence; and
- proof 51: the composed worker reserves every applicable bucket atomically,
  including credential buckets.

It also supplies the provider-response portion of proof 34 and reinforces
proof 35 by proving that throttling is operational delay, not structural source
failure.

## Verification

```text
focused credential/provider authority collection       29 tests collected
guarded migration-safety suite                                  20 passed
guarded non-migration repository suite                         394 passed
Phase 3 changed-file Ruff lint                                  passed
Phase 3 changed-file Ruff format                                passed
Python compilation                                              passed
whitespace check                                                passed
initial /var inode use                                             12%
post-migration /var inode use                                      14%
final /var inode use                                               51%
```

No schema migration is required. Production services and production database
state were not changed by this implementation package.
