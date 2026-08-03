# 05 — UI Acceptance Checklist

**Status:** Draft  
**Permanent result record:** `acceptance/UAR-####-name.yaml`  
**Template:** `templates/ui-acceptance-record.yaml`

Acceptance reviews the complete checklist in the parent governance document
and stores the permanent result using
[`ui-acceptance-record.yaml`](templates/ui-acceptance-record.yaml),
including:

- scope, workflow, permissions, terminology, and domain distinctions;
- desktop/laptop parity, tablet functionality, approved exceptions, and mobile
  minimum workflows;
- component identity, ownership, variants, states, and compatibility;
- preference scope, precedence, persistence, reset, and device behavior;
- forms, validation, retained input, unsaved changes, and duplicate submits;
- dense tables, filtering, sorting, configurable columns, saved views,
  pagination/virtualization, long values, and narrow layouts;
- lazy-loading trigger, progress, failure, retry, caching, deduplication,
  filtering, sorting, and devices;
- Lite/Dark behavior, tokens, typography, semantic states, and icons;
- partial, empty, stale, server-error, permission-error, retry, API validation,
  and identifier behavior;
- automated tests, registry updates, decisions, exceptions, and review closure.

Outcomes are Accepted, Accepted With Follow-Up, or Rejected. Reacceptance is
required after material workflow, device, contract, preference, date/time,
appearance, governing-exception, or implementation changes.
