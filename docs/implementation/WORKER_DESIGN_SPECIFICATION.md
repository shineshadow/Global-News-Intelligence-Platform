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
