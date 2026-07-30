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
video-metadata-worker
subtitle-worker
asr-worker
classification-worker
entity-resolution-worker
attention-worker
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

Attention evaluation is durable derived-state work. High and Critical content
may use distinct scheduling lanes, but priority-lane failure never discards
acquired evidence. Story floors are applied transactionally with membership
changes before optional AI enrichment is dispatched.

Video discovery and subtitle acquisition do not dispatch video download or
ASR. ASR receives a stable, operator-requested Video Processing job identifier.
Opening the Video Processing page creates no worker task.

## Phase 3 Shared Acquisition Worker Architecture

The frozen Phase 3 architecture defines an acquisition orchestrator and a
separate disposable inspection sandbox. The acquisition task carries stable
SourceEndpoint, configuration-version, schedule-window/manual-idempotency,
and lease identifiers only.

The orchestrator owns:

```text
durable PostgreSQL lease and IngestionRun
exact adapter configuration
outbound SSRF/egress validation
atomic hierarchical rate reservation
just-in-time secret resolution
bounded isolated staging
accepted-byte promotion
Artifact/Document ownership transactions
health, metrics, and finalization
```

The inspection sandbox owns:

```text
authority-backed format/signature detection
mandatory malware/security scan
container and archive inspection
exact safe-parser verification
bounded structured verdict
```

The sandbox has no network, secrets, database, Redis, canonical-storage
write, or downstream authority. A crash, timeout, invalid verdict, or policy
violation deletes staged bytes. Suspicious payloads are deleted before
rejection metadata is appended, and no security bypass is exposed through
UI, API, SQLAdmin, environment, or adapter configuration.

No transaction remains open during retrieval, browser execution, scanning,
parsing, extraction, or promotion I/O. The frozen contract and its complete
proof matrix live in
`../specifications/PHASE_3_SHARED_SOURCE_ACQUISITION_ARCHITECTURE.md`.

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

## Calendar Phase 2 Validation Worker

`calendar-validation-worker` owns autonomous Calendar corroboration,
source-authority assessment, validation inference, structured relationship
enrichment, and conflict resolution.

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

The frozen implementation uses the Celery queue `calendar-validation` and
the systemd unit `gni-celery-calendar-validation.service`. Celery Beat
discovers Event/Occurrence evidence snapshots that do not have a current
completed run and queues stable database identifiers only.

The provider-neutral internal adapter implements two versioned strategies:

```text
evidence-reconciliation:1
adversarial-canonical-review:1
```

The default external router records an installation-level ineligible result
because no production external provider is configured. It performs no direct
provider call. A future LLM Router implementation may be injected through the
same contract.

### Structured relationship extraction

The provider-neutral extraction adapter returns controlled candidates for:

```text
Event → Geography
Event → Topic
Event → Entity
Event → Source
```

Every candidate carries a canonical target ID, frozen per-family role,
confidence, actor kind, semantic assignment method, normalized evidence
uses, strategy/adapter provenance, and full router provenance for direct
external-model output. The relationship service rejects missing or inactive
targets, invalid roles, actor/method mismatches, evidence outside the exact
snapshot, duplicate logical candidates, and stale results.

The repository adapter promotes only relationships already supported by
normalized records:

```text
Calendar evidence Source      → Event Source / reference
active Document Topic         → Event Topic / secondary
```

It deliberately does not promote publisher country, Document Geography,
Entity ancestry, or a merely mentioned Document Entity into an Event
relationship. Geography and Entity relationships require an adapter to
return an explicit canonical target and frozen Calendar role.
