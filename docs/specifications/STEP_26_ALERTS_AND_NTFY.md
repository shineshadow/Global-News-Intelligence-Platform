# Step 26 — Alerts and ntfy Delivery

**Status:** FREEZE CANDIDATE
**Depends on:** Step 25 — FROZEN
**Date:** 2026-07-27

## 1. Purpose

Step 26 converts a newly inserted Step 25 Monitor match into durable alert
state and delivers it through configured ntfy destinations:

```text
new monitor_match
        ↓
one immutable content alert
        ↓
zero or more destination deliveries
        ↓
append-only delivery attempts
```

Repeated Monitor observations do not create another alert. Step 26 does not
reinterpret Step 24 criteria or decide whether a document matches.

## 2. Ownership and Scope

```text
alert destination
    installation-level ntfy endpoint configuration

Monitor destination binding
    routing policy for future new matches

alert
    immutable content/news event created from one new Monitor match

alert delivery
    destination-specific mutable delivery state

delivery attempt
    auditable record of one HTTP publication attempt
```

Calendar alerts remain a separate future alert class. Step 26 creates only
`content_monitor_match` alerts.

## 3. Event Idempotency

One `monitor_match` has at most one alert. Alert creation occurs in the same
database transaction and savepoint as insertion of the new Monitor match.

```text
new match inserted       create or recover its one alert
existing match observed  create no alert
```

The alert identifies the Monitor, first matching revision, document, and
Monitor match through database-enforced same-Monitor provenance.

Existing Monitor matches present during migration are backfilled as alerts so
the invariant is complete at the freeze boundary.

## 4. Routing

A Monitor may be bound to zero or more active alert destinations. Bindings are
many-to-many, independently enabled, and may override delivery priority.

Routing is snapshotted when the alert is created:

```text
active enabled binding  one delivery row
inactive destination   no delivery row
binding added later     no implicit historical backfill
```

Historical replay requires an explicit future operation. It is never a side
effect of editing destination configuration.

## 5. Destinations and Secrets

Criteria version 1 supports ntfy destinations only. Each destination stores:

```text
base URL
topic
optional authentication-token environment-variable name
timeout
bounded retry policy
active state
supporting metadata
```

Bearer tokens are not persisted in PostgreSQL, returned by APIs, placed in
Celery arguments, or written to attempt history. A destination may reference
an environment variable containing the token.

The ntfy publication uses its JSON publish API with these fields:

```text
topic
title
message
priority
tags
click, when an absolute document URL exists
sequence_id, deterministically derived from the alert and destination
```

Authenticated requests add `Authorization: Bearer ...`.

Platform priority maps to ntfy priority:

```text
low       2
normal    3
high      4
critical  5
```

## 6. Delivery and Retry Contract

Network I/O never occurs inside ingestion, classification, Monitor evaluation,
or alert-creation transactions.

```text
pending
   ↓
processing
   ├──→ delivered
   ├──→ retry_scheduled ──→ processing
   └──→ permanent_failure
```

Delivery workers use row locking and expiring claim tokens. A stale processing
claim may be reclaimed; its unfinished attempt is closed as a retryable
failure before the next attempt begins.

Retryable outcomes:

```text
network and timeout failures
HTTP 408
HTTP 425
HTTP 429
HTTP 5xx
```

Other HTTP 4xx outcomes and missing token configuration are permanent
failures. Retries use bounded exponential backoff and honor a numeric
`Retry-After` value without exceeding the configured maximum.

Exactly-once external HTTP effects cannot be guaranteed across a process crash
after ntfy accepts a request but before PostgreSQL records success. Step 26
provides durable at-least-once delivery with one logical alert and one logical
delivery per destination.

## 7. Attempt History

An attempt is created and committed before HTTP publication. Completion
records:

```text
succeeded
retryable_failure
permanent_failure
HTTP status when available
bounded response excerpt
sanitized error
started and completed timestamps
```

Attempt history never records authorization headers or token values.

## 8. Operator Surfaces

Step 26 provides:

```text
destination creation, update, listing, and deactivation
Monitor destination routing
alert list and detail
delivery and attempt history
manual retry of retryable or permanently failed delivery
Alerts web page
destination configuration web page
```

A manual retry resets delivery state but does not create another alert or
delivery row.

## 9. Migration and Downgrade

The migration seeds no destination and performs no network request. It
backfills one alert per existing Monitor match without creating deliveries.

Downgrade is allowed only when there are no destinations, bindings, deliveries,
or attempts and no alerts beyond the deterministic migration backfill.
Meaningful operator configuration or delivery history blocks destructive
downgrade.

## 10. Freeze-Candidate Proofs

The freeze candidate must directly prove:

```text
one alert for a newly inserted Monitor match
no alert for repeated match observation
same-Monitor alert provenance
existing-match migration backfill
zero, one, and multiple destination routing
inactive destination and disabled binding exclusion
secret values never persisted or returned
successful ntfy request shape and priority mapping
retryable network, 429, and 5xx outcomes
permanent 4xx and missing-token outcomes
bounded retry exhaustion
stale claim recovery
concurrent delivery dispatch creates one active attempt
manual retry reuses the logical delivery
ingestion durability when alert creation or ntfy is unavailable
API and web operator behavior
clean downgrade/re-upgrade
destructive-downgrade refusal
complete regression and zero Alembic drift
```
