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
attention
watches
videos
video-processing
events
intelligence-calendar
youtube
alerts
ai-jobs
operations
```

Future Attention APIs should expose effective decisions, reason summaries,
feedback, manual priority, policy preview/activation, and immutable policy
history. Future Watch APIs should expose seed revisions and match explanations.
Video Processing submission must remain separate from read-only video detail;
opening or fetching detail creates no job.

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

## Intelligence Calendar Phase 2

Normal Phase 1 Calendar reads continue to return effective canonical state.
Event detail includes a read-only `intelligence_summary` containing effective
and active authority layers, confidence/method provenance, inference run and
evidence snapshot, and unresolved-conflict/open-exception counts. Complete
machine state, operator state, evidence, attempts, and conflicts are
inspectable through the separate administrative-exception detail without
making review a prerequisite.

Implemented resource surface:

```text
GET  /api/v1/calendar/administrative-exceptions
GET  /api/v1/calendar/administrative-exceptions/{exception_id}
POST /api/v1/calendar/administrative-exceptions/{exception_id}/resolve
POST /api/v1/calendar/administrative-exceptions/{exception_id}/deny
POST /api/v1/calendar/administrative-exceptions/{exception_id}/withdraw
POST /api/v1/calendar/administrative-exceptions/{exception_id}/close
POST /api/v1/calendar/administrative-exceptions/{exception_id}/reopen
POST /api/v1/calendar/administrative-exceptions/{exception_id}/note
GET  /api/v1/calendar/events/{event_id}/policies/{policy_id}/occurrences/{occurrence_id}
PUT  /api/v1/calendar/events/{event_id}/policies/{policy_id}/occurrences/{occurrence_id}
DELETE /api/v1/calendar/events/{event_id}/policies/{policy_id}/occurrences/{occurrence_id}
```

The list accepts `state`, `severity`, and `assertion_family` filters plus
bounded `offset` and `limit`. Detail returns competing and proposed
assertions, linked evidence, source-authority assessments, every autonomous
attempt with process/model provenance, operator overrides, the operator
assertion ledger, and exception action history.

Resolution accepts exactly one selected competing assertion or an explicit
canonical validation state. Denial leaves the exception unresolved.
Close records an administrative disposition without changing the underlying
conflict or canonical state. Reopen records renewed inspection. Withdrawal
reopens a resolved exception and republishes the preserved machine validation
state. Notes and operator inaction do not change canonical state.

Occurrence-policy writes require an operator reference and reason, enforce
that Event, Coverage Profile policy, and Occurrence share the exact scope,
and append same-transaction history. They change only profile-owned priority,
expected-news importance, and watch behavior. They cannot create, suppress,
or resolve installation-global canonical assertions or conflicts.

Administrative resolution currently accepts validation conflicts only.
Relationship assertions may be autonomously extracted and projected, but an
administrative relationship conflict is rejected until a transactional
canonical relationship-conflict projector is introduced; the API cannot
report a false resolution.

Operator writes append authority history; they do not update or delete
machine assertions in place. Operator silence has no API side effect.
Worker/internal inference endpoints, if needed, must not be exposed as a
normal public approval workflow.

The route and schema contract remains subordinate to
`../specifications/INTELLIGENCE_CALENDAR_PHASE_2_ARCHITECTURE.md`.

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
