# Worker Design Specification

**Project:** Global News Intelligence Platform  
**Document:** `WORKER_DESIGN_SPECIFICATION.md`  
**Status:** Placeholder / Background Processing Design Index

---

## Purpose

This document should define Celery queues, task ownership, concurrency, idempotency, retry policy, resource constraints, scheduling, and operational observability.

---

## Candidate Worker Families

```text
ingestion-worker
scheduler-worker
feed-worker
web-listing-worker
playwright-worker
youtube-worker
asr-worker
classification-worker
entity-resolution-worker
translation-worker
embedding-worker
cluster-worker
novelty-worker
alert-worker
calendar-discovery-worker
future-event-worker
calendar-validation-worker
event-scheduler-worker
event-correlation-worker
llm-worker
backfill-worker
```

---

## Worker Contract Template

For every worker/task define:

```text
queue
input identifiers
output/state changes
idempotency key
transaction boundary
external I/O
retryable failures
non-retryable failures
max attempts
backoff
rate limit
lock/claim mechanism
timeout
metrics
structured logs
manual replay procedure
```

---

## Resource Isolation

GPU-heavy tasks, browser automation, ordinary network ingestion, and low-latency alert tasks should not compete in the same unconstrained worker pool.

Future routing should distinguish:

```text
CPU/network
browser
GPU inference
high-priority real-time
bulk/backfill
```

---

## Active Step 26 Alert Worker

Step 26 activates the `alerts` queue. Celery Beat asks the scheduler worker to
dispatch due delivery identifiers every
`CELERY_ALERT_DISPATCH_INTERVAL_SECONDS` (15 seconds by default). The
`gni-celery-alerts.service` worker consumes those identifiers.

The task argument contains only the database delivery identifier. The worker:

```text
claims the delivery transactionally
appends a running attempt
commits before external I/O
publishes to the snapshotted ntfy endpoint
finalizes the attempt and delivery in a new transaction
```

Claims expire and are recoverable. Duplicate queued tasks cannot create two
simultaneous active attempts. Retry scheduling is durable in PostgreSQL;
Celery transport retries do not own the business retry policy. Destination
authentication tokens are resolved from the configured environment-variable
name inside the alerts worker and are never Celery arguments.

## Calendar Phase 2 Validation Worker Candidate

`calendar-validation-worker` will own autonomous Calendar corroboration,
source-authority assessment, validation inference, relationship enrichment,
and conflict resolution.

The task carries stable Event/Occurrence and evidence-snapshot identifiers.
It does not carry embedded evidence or model output. The worker commits before
model or network I/O and records each substantive reasoning attempt
independently.

Conflict resolution uses:

```text
Pass 1  internal_agent resolution
Pass 2  materially distinct internal_agent critical review
Pass 3  external_model adjudication for eligible unresolved high/critical
        conflicts when configured and available
```

Infrastructure retries do not consume reasoning-attempt ordinals. Duplicate
tasks with the same conflict, evidence hash, actor, model, and strategy are
idempotent. An unresolved exception does not block unrelated Calendar or
platform work.

The worker uses a provider-neutral `calendar_validation` adapter. It never
calls a model provider directly. Missing internal-agent infrastructure
creates an operational failure and bounded retry, not a fabricated completed
reasoning pass.

`actor_kind` records `internal_agent` or `external_model`; semantic derivation
continues to use the separate GFA-C `internal_autonomous_agent` or
`external_ai_model` assignment method.

The frozen architecture contract is in
`../specifications/INTELLIGENCE_CALENDAR_PHASE_2_ARCHITECTURE.md`.
