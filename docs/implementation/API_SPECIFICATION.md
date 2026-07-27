# API Specification

**Project:** Global News Intelligence Platform  
**Document:** `API_SPECIFICATION.md`  
**Status:** Placeholder / API Design Index

---

## Purpose

This document should become the implementation-level contract for public/internal FastAPI routes while preserving the service layer as the primary home of business logic.

---

## API Principles

- Version APIs under `/api/v1`.
- Keep Web UI server-rendered flows free to call services directly.
- APIs must enforce authorization and validation independently of the browser.
- Pagination/filter semantics should be consistent across resources.
- Error responses should be structured and machine-readable.
- Write endpoints should be idempotent where the operation naturally supports it.

---

## Resource Areas

```text
health
sources
source-endpoints
ingestion-runs
documents
classification
topics
geographies
entities
document-types
monitors
stories
events
intelligence-calendar
youtube
alerts
ai-jobs
operations
```

---

## Filtering Contract Placeholder

Document/list APIs should eventually support combinations of:

```text
source_id
source_type
geography
topic
entity
document_type
language
published_after
published_before
retrieved_after
retrieved_before
q
semantic_query
classification_confidence
```

---

## Intelligence Calendar Phase 1

Calendar Event creation is separate from Monitor creation. A request may
create a Coverage Profile policy, but only the explicit Monitor endpoints
create or link a Step 25 Monitor.

```text
POST /api/v1/calendar/events
GET  /api/v1/calendar/events
GET  /api/v1/calendar/events/{event_id}
POST /api/v1/calendar/events/{event_id}/aliases
POST /api/v1/calendar/events/{event_id}/revisions
POST /api/v1/calendar/events/{event_id}/materialize
POST /api/v1/calendar/events/{event_id}/evidence
POST /api/v1/calendar/events/{event_id}/state-transitions
POST /api/v1/calendar/events/{event_id}/merge
POST /api/v1/calendar/events/{event_id}/occurrences/{occurrence_id}/schedule-revisions
POST /api/v1/calendar/events/{event_id}/monitors
POST /api/v1/calendar/events/{event_id}/monitors/link
```

The Monitor endpoints reject profile mismatches. Calendar stores only the
normalized link; the Step 25 Monitor revision remains the criteria authority.
Calendar creation, rescheduling, and linking do not create Calendar reminder
or change alerts. Only a new linked Monitor/document match enters the frozen
Step 26 content-alert path.

---

## Endpoint Documentation Template

```text
method + route
purpose
auth requirement
query/path/body schema
response schema
pagination
errors
side effects
idempotency
rate limit
audit event
service method
```
