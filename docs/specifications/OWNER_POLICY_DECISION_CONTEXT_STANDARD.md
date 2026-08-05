# Owner Policy Decision Context Standard

**Owner approval:** 08-04-2026  
**Status:** GOVERNING — NORMATIVE DESIGN; IMPLEMENTATION REQUIRED  
**Authority:** `../change-reports/OWNER_OPERATION_INFORMATION_AND_POLICY_DECISION_CONTEXT_ADOPTION.md`  
**Parent authority:** `OWNER_AUTHORITY_AND_CONFIGURATION_STANDARD.md`  
**Related information model:** `OWNER_OPERATION_INFORMATION_MODEL.md`

## 1. Purpose

This standard defines the reusable server-side explanation, preview, and audit
contract for every GNI decision controlled by the Owner policy ledger.

The Owner shall be able to determine:

```text
which policy key was resolved
what the registered default was
which contexts and scopes were considered
which matching overrides existed
which override won and why
what effective value governed runtime behavior
whether the decision consumed bounded-use authority
what external observation remained true
what a proposed override would change
what records or operations would be affected
```

The UI, CLI, API, and workers shall not implement separate policy precedence.
They shall call the same owner-policy service and receive the same controlling
decision.

## 2. Governing Authority

`OWNER_AUTHORITY_AND_CONFIGURATION_STANDARD.md` remains the governing owner
authority. The PostgreSQL-backed `owner_policy_overrides` ledger remains the
single authority surface.

This standard does not create another policy store, another precedence model,
or a UI-owned override mechanism.

The controlling precedence remains:

```text
exact request
endpoint
Source
origin
credential
platform
adapter
global
repository/application default
```

Priority resolves multiple active matches at the same exact scope. If scope and
priority are equal, deterministic ordering by activation time and stable record
identity controls unless a later approved specification changes that ordering.

## 3. Required Contracts

GNI shall implement three related service operations:

```python
resolve(...)
explain(...)
preview_override(...)
```

### 3.1 Runtime resolution

`resolve(...)` returns the effective value used by runtime code.

Runtime resolution may consume bounded-use or single-use authority only when
the selected policy is applied to an actual runtime decision.

### 3.2 Non-consuming explanation

`explain(...)` returns the current effective decision and complete resolution
context without consuming, applying, superseding, revoking, or otherwise
mutating Owner authority.

Calling `explain(...)` from UI, CLI, API, health projection, test inspection,
or administrative reporting shall never increment `uses_consumed` or append an
`applied` or `consumed` event.

### 3.3 Hypothetical preview

`preview_override(...)` evaluates a proposed policy value and scope without
persisting it.

The preview shall show the exact current decision and the exact proposed
decision, including where the proposal would not win because a more specific
or higher-priority override still controls.

A preview shall not consume current authority and shall not create, supersede,
revoke, or modify an override.

## 4. Policy Registration

Every owner-controllable policy key shall be registered with:

```text
policy_key
value_type
validation_schema
repository_or_application_default
supported_scopes
resolution_point
restart_requirement
external_consequences
audit_evidence
default_path_test
override_path_test
display_metadata
risk_summary
```

A policy key shall not be resolved solely from an arbitrary caller-provided
default. The caller may pass the expected registered default for defensive
verification, but the service shall reject a mismatch.

Registered value types include:

```text
boolean
integer
number
string
enum
object
array
```

Object and array policies require closed, versioned validation schemas with
bounded size and field constraints.

Unregistered policy keys shall fail explicitly.

## 5. Normative Decision Context DTO

The canonical DTO shall be named `OwnerPolicyDecisionContext` or an
equivalently explicit name.

It shall include:

```text
schema_version
policy_key
policy_definition_version
value_type
registered_default
effective_value
overridden
selected_override
matching_candidates
resolution_context
resolution_rule
resolution_time
uses_would_be_consumed
external_consequences
effective_runtime_decision
external_observations
basis_fingerprint
```

The initial schema version is:

```text
owner-policy-decision-context.v1
```

### 5.1 Selected override

When an override controls, `selected_override` shall include:

```text
override_public_id
scope_type
scope_identity
priority
status
valid_from
valid_until
max_uses
uses_consumed
uses_remaining
actor
reason
risk_acknowledgement
supersedes_override_public_id
created_at
updated_at
```

When the repository/application default controls, `selected_override` is null.

### 5.2 Matching candidates

`matching_candidates` shall include every active, temporally valid,
non-exhausted override that matched the resolution context.

Each candidate shall state:

```text
override_public_id
scope_type
scope_identity
scope_rank
priority
validity
uses_remaining
selected
selection_or_rejection_reason
```

Expired, revoked, superseded, and exhausted records belong in bounded related
history rather than the active candidate list.

### 5.3 Resolution context

`resolution_context` shall include the exact non-secret values used:

```text
adapter
platform
credential_ids
origin
source_id
endpoint_id
request_identity
```

Absent dimensions remain null or empty. Scope shall not be inferred from
publisher country, Document geography, entity ancestry, display name, or
unrelated metadata.

### 5.4 Resolution rule

`resolution_rule` shall identify why the value won:

```text
repository_default
most_specific_scope
higher_priority_same_scope
later_activation_same_scope_priority
stable_identity_tiebreak
```

### 5.5 Bounded-use information

`uses_would_be_consumed` states whether applying the decision at runtime would
consume one use.

`uses_remaining` is null for unlimited authority and otherwise equals
`max_uses - uses_consumed`.

Explanation and preview return the calculation without changing it.

## 6. External Observation and Effective Decision Separation

The context shall keep three concepts separate:

```text
external observation
    What an external system, file, provider, scanner, model, or other source
    of evidence reported.

owner policy
    The registered default and effective value selected through the ledger.

effective runtime decision
    What GNI did or will do after applying the effective policy.
```

Example:

```text
external observation:
    robots.txt disallows /news/private

registered default:
    enforce robots restrictions = true

effective owner policy:
    false from endpoint override

effective runtime decision:
    permit acquisition

external fact retained:
    the robots restriction remains recorded and may govern later requests if
    the override expires, is revoked, is exhausted, or no longer matches
```

An override shall never rewrite external evidence.

## 7. Preview Contract

`preview_override(...)` shall accept:

```text
policy_key
proposed_value
scope_type
scope_identity
priority
valid_from
valid_until
max_uses
resolution_context
```

It shall return:

```text
current_decision_context
proposed_decision_context
proposal_would_win
proposal_selection_reason
affected_current_subjects
affected_current_gates
affected_scheduled_operations
superseded_override
more_specific_overrides_that_still_win
external_consequences
risk_summary
basis_fingerprint
```

### 7.1 Impact boundaries

Impact preview shall use authoritative current records and exact scope
matching.

```text
endpoint scope:
    exact SourceEndpoint only

Source scope:
    endpoints currently belonging to the exact Source

origin scope:
    requests whose canonical origin exactly matches

credential scope:
    requests bound to the exact secret reference identity

request scope:
    exact request identity only
```

The preview shall state when future impact cannot yet be known.

### 7.2 Basis fingerprint and stale-preview rejection

Every preview shall include a deterministic `basis_fingerprint` derived from:

```text
policy definition version
resolution context
selected override identity
matching active candidate identities and versions
relevant subject and gate versions
```

A mutation based on a preview shall re-resolve transactionally and reject the
request when the fingerprint changed.

The stable reason code shall be:

```text
owner_policy.preview_stale
```

The Owner shall review a new preview before mutation.

## 8. Runtime Consumption

Bounded-use or single-use authority is consumed only when:

1. the override is selected;
2. runtime reaches the governed decision point;
3. the effective value is applied to an actual operation or gate decision; and
4. the transaction appends the matching `applied` or `consumed` event.

Opening a page, listing policies, rendering health, producing a preview,
validating a form, or checking eligibility shall not consume authority.

Where several policies are resolved early, consumption shall occur at the exact
application point or the transaction shall guarantee that a consumed use cannot
commit unless the governed decision also commits.

## 9. Audit and History

The append-only override event ledger remains authoritative for creation,
supersession, application, consumption, revocation, and expiration evidence.

The implementation shall expose enough information to reconstruct:

```text
policy definition version
exact resolution context
selected override
effective value
runtime decision
external observation references
operation or gate affected
basis fingerprint
```

History shall retain superseded, revoked, exhausted, and expired records.

## 10. UI and API Requirements

The first owner-facing UI implementation shall be read-only for policy
mutation.

It shall display:

```text
policy key and purpose
registered default
effective value
whether overridden
selected scope and identity
actor and reason
risk acknowledgement
validity period
remaining uses
matching policy chain
why the selected value won
external observations
effective runtime decision
next eligibility
history
```

UI time display follows `AMERICAN_DATE_TIME_DISPLAY_STANDARD.md`.

Browser-based creation, supersession, or revocation shall not be enabled until:

```text
server-derived authenticated Owner identity
Owner-capability authorization
CSRF protection
reauthentication for sensitive changes
reason
risk acknowledgement
scope confirmation
validity and use-limit confirmation
transactional re-resolution
stale-preview rejection
append-only audit
```

An editable `actor` field is not authenticated identity.

## 11. Service and Security Invariants

1. There is one owner-policy ledger.
2. There is one precedence implementation.
3. UI, CLI, API, and workers use the same service.
4. `explain(...)` and `preview_override(...)` are non-consuming.
5. External observations remain separate from policy and runtime decision.
6. Unregistered keys and invalid values fail explicitly.
7. Scope identities are exact and non-secret.
8. Secret values never enter decision-context details.
9. Preview does not persist or mutate authority.
10. Mutation rejects a stale basis fingerprint.
11. Actor identity for UI mutation is server-derived.
12. History remains retained and linkable.
13. `OwnerOperationResult` references this context rather than duplicating a
    conflicting policy explanation.

## 12. Required Tests

The implementation shall prove:

```text
repository default controls with no matching override
global override controls
adapter override defeats global
platform override defeats adapter
credential override defeats platform
origin override defeats credential
Source override defeats origin
endpoint override defeats Source
request override defeats endpoint
priority resolves equal-scope matches
expired override does not apply
revoked override does not apply
superseded override does not apply
exhausted override does not apply
one-use override is consumed by one actual runtime decision
explain does not consume one-use authority
preview does not consume one-use authority
matching candidate chain explains selection
external evidence remains unchanged beside overridden runtime behavior
preview shows when proposal would not win
stale preview is rejected
UI and worker resolve the same effective value for the same context
invalid registered value is rejected
unregistered policy key is rejected
secret-bearing details are rejected
```

## 13. Initial Proof-34 Integration

Proof 34 shall use this standard for:

```text
acquisition.robots.enforce
acquisition.robots.unavailable_action
acquisition.robots.crawl_delay.enforce
acquisition.robots.cache.max_age_seconds
acquisition.robots.cache.max_stale_seconds
acquisition.robots.fetch_limits
```

Only `acquisition.robots.enforce` is currently registered and connected to the
worker. The other keys remain pending until registered and implemented under
`ROBOTS_ACQUISITION_AND_ENFORCEMENT_STANDARD.md`.

## 14. Current Implementation Status

```text
owner_policy_overrides ledger                       implemented
owner_policy_override_events                        implemented
scope precedence and priority                       implemented
runtime resolve and bounded-use consumption         implemented foundation
complete registered policy-definition catalog       not implemented
non-consuming explain DTO/service                   not implemented
hypothetical preview DTO/service                    not implemented
basis fingerprint and stale-preview rejection       not implemented
authenticated UI mutation                           not implemented
proof-34 full policy family                         not implemented
```

This standard governs the pending implementation and does not claim those
items are complete.
