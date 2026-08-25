# Owner Operation Information Model

**Owner approval:** 08-04-2026  
**Status:** GOVERNING — NORMATIVE DESIGN; IMPLEMENTATION REQUIRED  
**Authority:** `../change-reports/OWNER_OPERATION_INFORMATION_AND_POLICY_DECISION_CONTEXT_ADOPTION.md`  
**Controlling recommendation:** `../recommendations/Reusable_Owner_Operation_Information_And_Policy_Decision_Context.md`

## 1. Purpose

GNI shall tell the Owner what the system attempted, what happened, what result
was produced, what currently prevents progress, precisely why that state
exists, what evidence supports it, and whether Owner authority changed or may
change the effective behavior.

A generic success, error, or failure label is not sufficient when structured
information exists that can explain the result or support an Owner decision.
This standard establishes one stable cross-GNI owner-facing information
contract while allowing each domain to retain its own constrained persistence,
reason vocabulary, evidence, and runtime rules.

The central relationship is:

```text
execution status = what happened to execution
outcome code     = what domain result was produced
gate state       = what currently prevents progress
reason code      = precisely why
details          = versioned evidence needed to understand and decide
```

These dimensions are independent. A successful execution can produce
`not_modified`, `verified_empty`, `unchanged`, or another meaningful outcome.
A failed execution does not necessarily install a continuing gate. An external
restriction can remain true even when Owner authority permits a different GNI
decision.

## 2. Scope

This standard applies to owner-facing operation information for:

```text
acquisition
inspection
inference
classification
monitoring
alerting
calendar
```

A future domain may join the contract only by registering its domain,
operation types, outcome codes, reason codes, permitted gate states, detail
schemas, provenance requirements, and tests. A domain does not gain authority
to invent unregistered result strings in workers, database rows, APIs, logs,
or templates.

This standard does not require one enormous polymorphic result table. Domain
tables may remain authoritative where they provide stronger constraints and
specialized evidence. The common contract is a service/DTO and rendering
boundary, with optional indexing only when a demonstrated cross-domain query
requires it.

## 3. Governing Principles

1. **No Owner inference requirement.** The UI and API shall receive explicit
   result meaning from a server-side projection. They shall not infer a reason
   by combining unrelated status fields, error strings, or timestamps.
2. **Independent dimensions.** Execution status, outcome, gate, reason, and
   policy decision context shall not be collapsed into one overloaded slug.
3. **Stable machine vocabulary.** Operation, outcome, gate, reason, and detail
   schema identifiers are stable registered values.
4. **Append-only history.** Complete result and decision history is retained.
   A latest-state view is a projection and never replaces history.
5. **Domain ownership.** Each domain owns its valid operation, outcome, reason,
   gate, and evidence combinations under this common envelope.
6. **Evidence before advice.** Recommended actions may guide the Owner, but
   they never replace the underlying evidence or controlling policy context.
7. **External facts remain factual.** An Owner override may change GNI behavior
   without rewriting the observed provider, robots, scanner, model, or other
   external signal.
8. **Secrets remain secret.** Owner-facing details are sanitized and bounded.
   Secret values, credentials, raw rejected bytes, and unrestricted response
   bodies shall not enter the common envelope.

## 4. Normative Operation-Result Envelope

The canonical DTO shall be named `OwnerOperationResult` or an equivalently
explicit name. Its serialized representation shall include:

```text
schema_version
result_public_id
operation_domain
operation_type
operation_identity
subject
execution_status
outcome_code
gate_state
reason_code
message
details_schema
details
severity
retryable
next_eligible_at
provenance
recommended_action
policy_decision_context
external_observations
started_at
finished_at
recorded_at
```

### 4.1 Identity

`schema_version`
: Version of the common envelope. The initial version is
  `owner-operation-result.v1`.

`result_public_id`
: Stable non-secret public identifier for the result projection or durable
  result record.

`operation_domain`
: Registered domain slug such as `acquisition` or `inspection`.

`operation_type`
: Registered action such as `acquisition.retrieve_resource`.

`operation_identity`
: Stable idempotency, run, request, evaluation, delivery, or other exact
  operation identity. It shall not contain a secret.

`subject`
: Typed references to the records acted upon. The subject shall identify
  reference type and stable identity rather than depend on display text.

### 4.2 Execution and outcome

`execution_status` is one of:

```text
queued
running
succeeded
partial
failed
delayed
blocked
skipped
cancelled
```

The status describes execution only.

`outcome_code` is a required stable namespaced domain-owned code for a terminal
operation, including successful operations. Examples:

```text
acquisition.retrieved
acquisition.not_modified
acquisition.verified_empty
acquisition.unchanged
acquisition.request_deferred
inspection.accepted
inspection.rejected
classification.no_applicable_label
monitoring.no_match
alerting.delivery_rejected
```

A changed meaning requires a new code or versioned definition.

### 4.3 Gate and reason

`gate_state` identifies what currently prevents progress. `none` means no
continuing gate is installed by the result.

Initial shared gate vocabulary:

```text
none
rate_limited
robots_denied
robots_delayed
robots_unavailable
policy_unavailable
authentication_failed
egress_blocked
artifact_rejected
inspection_unavailable
storage_unavailable
adapter_unavailable
configuration_invalid
```

A failure may have `gate_state = none`. A successful operation may coexist with
a separate gate affecting later work.

`reason_code` is a required stable namespaced explanation. Examples:

```text
acquisition.robots_path_disallowed
acquisition.http_not_modified
inspection.archive_traversal_detected
inference.insufficient_evidence
classification.no_applicable_label
monitoring.no_match
alerting.delivery_rejected
```

`message` is a sanitized Owner-facing summary generated from the registered
reason and validated details. Templates shall not reconstruct reasons from raw
exceptions.

### 4.4 Details and provenance

`details_schema` is a required versioned identifier such as:

```text
acquisition.robots_path_disallowed.v1
acquisition.http_not_modified.v1
inspection.archive_traversal_detected.v1
```

Each `details` schema shall declare:

```text
required fields
optional fields
data types and bounds
reference identities
redaction rules
Owner-visible fields
log-safe fields
compatibility and versioning behavior
```

Unversioned arbitrary JSON is prohibited at the common contract boundary.

`provenance` identifies the policy, adapter, model, ruleset, detector, parser,
signature release, configuration version, or other implementation that
produced the result.

`external_observations` contains typed references to durable external evidence.
The envelope references authoritative evidence instead of duplicating
unrestricted payloads.

`policy_decision_context` contains or references the exact result defined by
`OWNER_POLICY_DECISION_CONTEXT_STANDARD.md` whenever an Owner-controlled policy
governed or could change the decision.

### 4.5 Severity, retry, and time

`severity` is one of:

```text
info
warning
error
critical
```

`retryable` states whether GNI has a valid automated or Owner-authorized path
to attempt the operation again under current information.

`next_eligible_at` is the earliest known time at which retry or policy
reevaluation may occur. It is nullable when unknown, not planned, or dependent
on Owner action.

Canonical timestamps remain timezone-aware in persistence and APIs. UI display
is governed by `AMERICAN_DATE_TIME_DISPLAY_STANDARD.md`; time is not displayed
by default.

`recommended_action` is optional bounded guidance supported by the evidence.

## 5. Registry Contract

Each domain shall maintain a code-owned or authority-backed registry binding
valid combinations. A definition shall include:

```text
identifier
display label
description
permitted execution statuses
permitted outcome codes or gate states
default severity
default retryable value
details schema
required provenance
recommended-action rule
active, deprecated, or superseded state
```

Identifiers use lowercase dotted names. Superseded identifiers remain readable
for history.

Runtime code shall fail explicitly when asked to emit an unregistered domain,
operation, outcome, gate, reason, or details schema. A generic unknown reason
is permitted only when it is itself registered and preserves the bounded
original exception class and stage.

## 6. Persistence and History

Authoritative evidence remains in the owning domain, including:

```text
ingestion_runs
artifact_rejections
acquisition_rate_limit_observations
owner_policy_overrides
owner_policy_override_events
acquisition_robots_snapshots
acquisition_robots_evaluations
alert delivery attempts
monitor evaluations
```

A bounded cross-domain index may be added when needed, but it shall contain
common fields and references rather than become a second mutable domain truth.

Terminal results are append-only. Corrections append a correcting or
superseding result with explicit linkage.

A `latest` projection is selected deterministically by recorded time and a
stable tie-breaker and exposes the selected result identity.

## 7. Service Boundary

GNI shall provide one common projection service, for example:

```python
OwnerOperationInformationService.describe(...)
OwnerOperationInformationService.history(...)
OwnerOperationInformationService.latest(...)
```

Domain adapters may expose typed methods such as:

```python
describe_acquisition_run(...)
describe_robots_evaluation(...)
describe_artifact_rejection(...)
describe_monitor_evaluation(...)
describe_alert_delivery(...)
```

Every method returns the common DTO after registry and details validation. The
service shall not mutate authoritative evidence, consume bounded-use Owner
authority, or create an override.

Workers, APIs, CLI output, and UI shall use the same registry definitions and
projection rules.

## 8. Required Owner-Facing Presentation

A detail view shall answer:

```text
What was GNI trying to do?
What happened?
What result was produced?
What currently blocks progress?
Why exactly did that happen?
What evidence produced that conclusion?
Which adapter, policy, ruleset, parser, detector, or model was used?
Will GNI try again, and when?
Did Owner authority affect the decision?
What external fact remains true despite an override?
What action is available?
What is the complete history?
```

A compact health row may show operation, status, outcome, gate, severity, next
eligibility, and `Review decision`. Details belong in a dedicated view.

UI implementation state does not define Owner authority. Missing UI mutation
controls are implementation gaps, not Owner lockouts. Browser mutation uses
the shared Owner-policy service and implements the safeguards in
`OWNER_POLICY_DECISION_CONTEXT_STANDARD.md`.

### 8.1 Internal And Owner Information

Information may serve both internal operation and Owner explanation. A field
used by workers, diagnostics, or authorized agent models is not therefore
internal-only. When a domain standard marks information as Owner information:

```text
the authoritative structured value must be retained
the implemented operational/API/CLI surface must preserve Owner access
the future Admin UI must expose the registered Owner-visible projection
the User UI may omit administrative diagnostic detail
Admin-UI placement does not create or limit the Owner's information right
missing UI presentation remains an explicit implementation gap
```

The Owner-facing projection shall use the same registered codes and evidence
as internal consumers. It may translate labels and messages for readability,
but it shall not hide, merge, or reinterpret distinct reasons.

## 9. Initial Acquisition Vocabulary

Proof 34 shall register at least these operation types:

```text
acquisition.evaluate_robots
acquisition.retrieve_robots
acquisition.reserve_rate_capacity
acquisition.retrieve_resource
acquisition.inspect_artifact
acquisition.promote_artifact
acquisition.normalize_resource
```

At least these outcomes:

```text
acquisition.retrieved
acquisition.not_modified
acquisition.verified_empty
acquisition.unchanged
acquisition.request_deferred
acquisition.request_blocked
acquisition.retrieval_permitted_by_owner
acquisition.artifact_rejected
acquisition.failed
```

At least these reasons:

```text
acquisition.robots_path_allowed
acquisition.robots_path_disallowed
acquisition.robots_evidence_unavailable
acquisition.robots_evidence_unreachable
acquisition.robots_evidence_stale
acquisition.robots_restriction_not_enforced
acquisition.retry_after_active
acquisition.provider_limit_active
acquisition.rate_budget_exhausted
acquisition.http_not_modified
acquisition.artifact_rejected
acquisition.adapter_configuration_invalid
acquisition.secret_resolution_failed
```

Robots detail schemas are governed by
`ROBOTS_ACQUISITION_AND_ENFORCEMENT_STANDARD.md`.

## 10. Invariants

1. Every terminal result has an outcome code and reason code.
2. Every reason code has exactly one emitted details-schema version.
3. `gate_state = none` never hides a known active gate.
4. `next_eligible_at` is supported by durable evidence or registered policy.
5. An override never changes an external observation.
6. Viewing information never consumes or mutates Owner authority.
7. Latest views are reconstructable from history.
8. Secret material and unrestricted payloads never enter the envelope.
9. UI and worker produce the same effective policy and reason for the same
   context and evidence.
10. Domain persistence remains authoritative over a common index or cache.

## 11. Verification

The implementation shall prove:

```text
successful operation with nontrivial outcome such as not_modified
failed operation with no continuing gate
delayed operation with exact gate and next eligibility
partial operation with validated details
external restriction preserved beside a different Owner decision
registered reason and details-schema validation
unregistered code rejection
secret and oversized-detail rejection
append-only result history
deterministic latest projection
same semantics in worker, API, CLI, and UI
UI inspection performs no authority consumption or domain mutation
```

Proof 34 is the first complete acceptance of this standard.

## 12. Current Implementation Status

```text
owner-policy ledger and precedence                    implemented foundation
acquisition run and domain evidence                   implemented foundation
common OwnerOperationResult DTO/service               not implemented
robots unavailable reason/details registry             implemented foundation
other domain result/reason/details registries           not implemented
cross-domain history projection                        not implemented
robots snapshots and evaluations                       persistence foundation implemented
proof-34 owner-facing detail view                      not implemented
```

This document governs the design and does not claim pending items are complete.
