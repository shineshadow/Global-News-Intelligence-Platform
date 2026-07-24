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
