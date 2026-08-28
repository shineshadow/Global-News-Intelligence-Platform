# Phase 3 Controlled Feed Cutover and Acquisition Health

Status: HISTORICAL IMPLEMENTATION RECORD — DEVELOPMENT UI RETIRED

Date: 2026-08-03

## Current Status

The development-only path/configuration, cutover history, proof state,
runtime-storage state, eligibility reasons, activation, and rollback controls
were removed from Acquisition Health by Owner direction. The cohort-limit
setting and web mutation routes were removed with them. No replacement UI was
introduced.

The Acquisition Health projection now reports feed operational state and poll
activity only. Existing endpoint configurations and immutable historical
cutover records remain stored and are not changed by the UI cleanup. The
remainder of this document records the retired development workflow for
historical context; it is not a current operating procedure.

## Scope

This package provides the operator-controlled transition from the legacy
RSS/Atom poller to the Phase 3 shared acquisition worker. It adds:

- a read-only Acquisition Health projection for every supported feed endpoint
- separate lifecycle, verification, health, temporary-gate, cutover-path, and
  post-cutover proof states
- exact eligibility checks before security preflight or configuration mutation
- a serialized, installation-bounded activation workflow
- rollback to the legacy path when no durable acquisition lease is active
- an immutable database-enforced cutover event ledger with actor and reason
- accepted Artifact, rejection, run, schedule, and cutover evidence in the UI

The migration creates no cutover events and activates no endpoints.

## Eligibility Contract

An endpoint can be activated only when all conditions are true:

```text
Source and SourceEndpoint lifecycle are active
exact tuple is feed/rss|atom/feed_parser
verification is verified or verified_empty
latest legacy IngestionRun succeeded
endpoint health is healthy and not stale
Phase 3 Artifact storage is explicitly configured
feed_parser v1 is active
no active Phase 3 configuration already exists
the installation cutover cohort limit has capacity
mandatory runtime preflight passes
eligibility remains true after preflight
```

An eligibility failure performs no runtime preflight and creates no
configuration or audit event. A preflight failure creates no cutover state.

## Concurrency and Authority

Activation takes a global PostgreSQL advisory transaction lock before checking
the active feed cohort count, then takes the same endpoint advisory authority
used by the acquisition lease service. This prevents concurrent activations
from exceeding the cohort limit and prevents a worker from acquiring the
endpoint while its path changes.

Rollback takes the endpoint advisory lock and refuses while an active durable
lease exists. A task already queued with an older configuration version fails
its dispatch-version check; it cannot silently execute against a different
path. The next scheduler selection carries the newly observed path.

The default `PHASE3_FEED_CUTOVER_LIMIT=1` creates a one-endpoint canary cohort.
Increasing it is an explicit installation decision after evidence review.

## Cutover and Proof States

Path and proof are deliberately different:

```text
legacy       no active Phase 3 endpoint configuration
phase3       active exact Phase 3 endpoint configuration

pending      activated but no successful Phase 3 run yet
passed       latest Phase 3 run succeeded
failed       latest Phase 3 run failed
```

Activation therefore never claims parity by itself. The operator reviews the
first Phase 3 run, accepted/rejected Artifact evidence, resulting Documents,
and schedule behavior before expanding the cohort.

## Health Projection

The UI keeps these dimensions separate:

```text
lifecycle     active | disabled
verification  never_checked | verified | verified_empty | verification_failed
health         unknown | healthy | degraded | failing | stale
temporary gate rate_limited | authentication_failed | adapter_unavailable |
               security_blocked | none
cutover path   legacy | phase3
proof state    not_applicable | pending | passed | failed
```

The projection is derived from canonical SourceEndpoint, IngestionRun,
configuration, Artifact, rejection, and cutover-event records. One Artifact
rejection remains rejection evidence and does not automatically install a
security gate.

## Immutable Audit and Rollback

Every successful activation and rollback appends an
`acquisition_endpoint_cutover_events` row containing the endpoint,
configuration, path transition, actor, reason, structured evidence, and
timestamp. PostgreSQL rejects update and deletion independently of the service.

Rollback retires rather than deletes the active configuration. Configuration,
Artifact, rejection, lease, run, and cutover history remain intact.

## UI Date and Time Boundary

The shared web formatter now converts canonical instants to
`America/New_York` and renders the owner-approved American form: current-year
dates omit the year, other-year dates use two digits, time uses a two-digit
12-hour clock with lowercase `am`/`pm`, and seconds/timezone labels are hidden.
The former `datetime_utc` template name remains only as a compatibility alias
to the corrected formatter; it no longer renders UTC.

## Retired Activation Procedure

The Acquisition Health activation procedure is retired and is no longer
available through the web interface.

## Deliberate Exclusions

The migration and installation defaults do not activate a feed. The retained
live review proves parity only for the exact CISA `feed/rss/feed_parser`
canary; it does not declare parity for every RSS or Atom feed. This candidate
does not remove the legacy poller, change the default cohort limit, expose
security bypasses, or implement the remaining Phase 3 adapters.
Authentication-backed actor identity replaces the current explicit operator
field only when the authentication track is implemented.

## Proof Results

The implemented candidate passed:

- 150 focused acquisition, Artifact, migration, RSS, and web tests, including
  destructive-downgrade refusal once cutover history exists;
- the full repository gate with 12 migration-safety tests and 362
  non-migration tests;
- Alembic upgrade to `a4c2e8f0b6d1 (head)` with zero schema drift;
- scoped lint, Python compilation, and whitespace validation; and
- guarded `/var` inode checks, ending at 48% usage below the 65% refusal
  threshold.

The live CISA RSS canary subsequently passed manual and scheduled Phase 3
acquisition, Artifact acceptance, stable 15-Document parity, live rollback,
legacy polling after rollback, and reactivation as
`feed-parser-v1-cutover-0002`. One accepted Artifact, zero rejections, and
three immutable cutover events remained at review. The non-blocking upstream
warning `no Content-type specified` was retained; exact structural RSS
inspection and all security boundaries still passed. The complete bounded
evidence and decision are recorded in
`PHASE_3_LIVE_FEED_CANARY_PARITY_REVIEW.md`.
