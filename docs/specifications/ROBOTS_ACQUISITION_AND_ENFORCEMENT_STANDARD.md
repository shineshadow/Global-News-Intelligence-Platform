# Robots Acquisition and Enforcement Standard

**Owner approvals:** 08-04-2026; version-one defaults, bounds, and parser approved 08-24-2026<br>
**Status:** GOVERNING — PROOF 34 NORMATIVE DESIGN; IMPLEMENTATION REQUIRED  
**Authority:** `../change-reports/OWNER_OPERATION_INFORMATION_AND_POLICY_DECISION_CONTEXT_ADOPTION.md`, `../change-reports/PHASE_3_PROOF_34_OWNER_APPROVAL_DECISIONS.md`, `../change-reports/PHASE_3_PROOF_34_MEDIATED_ROBOTS_AND_UI_OVERRIDE_DECISION.md`<br>
**Parent standards:** `OWNER_AUTHORITY_AND_CONFIGURATION_STANDARD.md`, `OWNER_OPERATION_INFORMATION_MODEL.md`, `OWNER_POLICY_DECISION_CONTEXT_STANDARD.md`  
**Phase:** Main Track Phase 3 — Robots acquisition and enforcement — proof 34

## 1. Purpose

This standard defines how GNI retrieves, validates, caches, parses, evaluates,
records, enforces, overrides, reconciles, and presents robots evidence.

Proof 34 is complete only when:

```text
robots evidence is observed and retained
the exact target request is evaluated
default enforcement governs by default
Owner authority can select a different GNI decision
external robots evidence remains preserved
the installed gate is exact and does not contaminate unrelated work
changed evidence replaces or clears the prior gate
the Owner can see what happened, why, and what an override changes
```

Robots evidence is external operational guidance. It is not authentication,
authorization, legal permission, content ownership, or proof that a server
will return content.

## 2. Core Separation

The implementation shall keep these records distinct:

```text
robots snapshot
    What was retrieved from the origin's robots resource and how it parsed.

robots evaluation
    How one exact user agent and target URL/path matched that snapshot.

Owner policy decision
    Whether and how GNI enforces the external evaluation.

effective runtime decision
    Permit, delay, or block the exact acquisition operation.

operation result
    What happened to the execution and what gate remains.
```

An Owner override shall not alter a `disallowed` robots evaluation to
`allowed`. It changes only the effective GNI enforcement decision.

## 3. Canonical Scope

Robots retrieval is origin-scoped. Robots evaluation is request-target scoped.

A canonical origin consists of:

```text
scheme
normalized host
effective port
```

Only `http` and `https` origins are eligible unless a later approved
specification registers another scheme.

The robots URL is:

```text
<scheme>://<host>[:non-default-port]/robots.txt
```

Fragments are excluded. User information is prohibited. Redirect handling
remains governed by the outbound egress standard and registered fetch limits.

The target evaluation uses the exact canonical target URL and normalized path.
The implementation shall not broaden one path restriction into installation,
adapter, platform, credential, Source, or entire-origin restriction unless the
parsed rule itself matches all paths for the selected user agent.

## 4. Required Persistence

Proof 34 shall add these authoritative tables or equivalent strongly
constrained persistence:

```text
acquisition_robots_snapshots
acquisition_robots_evaluations
acquisition_robots_gates
```

A generic rate-limit observation may reference these records, but shall not
duplicate complete robots evidence into every hierarchical rate bucket.

### 4.1 Robots snapshots

One snapshot represents one retrieval and parse result for one canonical
robots URL.

Required fields:

```text
id
public_id
origin
robots_url
retrieval_identity
ingestion_run_id, nullable
http_status, nullable
retrieval_state
retrieved_at
valid_from
fresh_until
stale_until
etag, nullable
last_modified, nullable
content_hash, nullable
content_bytes, nullable
raw_evidence_reference, nullable
parser_name
parser_version
parse_state
warnings
directives_digest, nullable
provenance
created_at
```

`retrieval_state` is one of:

```text
retrieved
not_modified
not_found
unreachable
rejected
```

`parse_state` is one of:

```text
parsed
empty
malformed
not_applicable
```

The raw body shall be bounded by the registered fetch limits. Retention may use
a bounded evidence reference rather than unrestricted inline content. Secrets,
cookies, authorization headers, and unrelated response headers shall not be
persisted.

Snapshots are immutable. Revalidation appends a new snapshot or an explicit
observation linked to the prior validated snapshot. A 304 response may reuse
the prior parsed directives only when the linkage and cache policy are retained.

### 4.2 Robots evaluations

One evaluation represents one exact decision for one target request.

Required fields:

```text
id
public_id
snapshot_id
source_endpoint_id
ingestion_run_id, nullable
request_identity
canonical_target_url
target_path
target_query, nullable
selected_user_agent
matched_group
matched_directive
matched_pattern
matched_line_or_location, nullable
match_specificity
crawl_delay_seconds, nullable
external_decision
evaluated_at
provenance
details
created_at
```

`matched_directive` is one of:

```text
allow
disallow
none
```

`external_decision` is one of:

```text
allowed
disallowed
unavailable
```

The evaluation shall retain the selected user agent, matched rule, pattern,
specificity, parser identity, and snapshot identity so the result is
explainable and reproducible.

### 4.3 Robots gates

Robots gates shall be stored separately from generic hierarchical rate bucket
holds.

Required fields:

```text
id
public_id
source_endpoint_id
request_scope_identity
canonical_target_url
target_path
selected_user_agent
robots_evaluation_id
gate_state
valid_from
valid_until
status
supersedes_gate_id, nullable
cleared_by_evaluation_id, nullable
created_at
updated_at
```

`gate_state` is one of:

```text
robots_denied
robots_delayed
robots_unavailable
```

`status` is one of:

```text
active
superseded
cleared
expired
```

Only one active gate may exist for the exact endpoint/request scope identity
and selected user agent.

A robots gate does not belong to installation, adapter, platform, credential,
origin, or Source rate buckets. Those dimensions may have independent rate,
provider, or Retry-After gates.

## 5. Retrieval Contract

Robots retrieval shall occur before the target request is authorized when no
usable cached snapshot exists.

Retrieval shall use the shared outbound egress guard, TLS validation, DNS and
redirect controls, response limits, and credential stripping rules.

Robots retrieval shall not send endpoint credentials unless a later exact
Owner-approved policy and destination authorization explicitly permits it. The
default request contains no target-resource credentials.

Conditional requests shall use retained `ETag` and `Last-Modified` values when
available.

The fetch implementation shall identify itself with the registered GNI robots
user agent. The exact user agent used for evaluation shall be retained.

### 5.1 Mediated Publisher Retrieval

For RSSHub, RSS-Bridge, changedetection, and Playwright acquisition, the Owner
supplies publisher target URLs through the GNI GUI. The intermediary retrieves
the exact publisher origin's `robots.txt`, evaluates the supplied publisher
target before content retrieval, and returns bounded versioned evidence to GNI.

The evidence contract must bind retrieval, parsing, exact evaluation, and the
subsequent target fetch. It includes the canonical publisher target and origin,
robots URL, retrieval identity/state/time and bounded digest, parser
provenance, selected user agent, matched rule evidence, external decision,
Crawl-delay observation, warnings, and unavailable reason when applicable.

GNI validates and persists this evidence before applying Owner policy and
authorizing the intermediary's target fetch. Missing, malformed, stale,
mismatched, untrusted, or unregistered evidence is `unavailable` and follows
`acquisition.robots.unavailable_action`.

The intermediary must use the Owner-approved parser and fetch controls or a
GNI-controlled component using those exact controls. Each mediated adapter
requires boundary and target-binding acceptance tests.

## 6. Parsing and Matching Contract

The parser implementation and version shall be registered and pinned.

The Owner-approved version-one parser identity and supply-chain pin are:

```text
distribution: protego==0.6.2
parser_name: protego
parser_version: 0.6.2
source_commit: efe5039d39ee51f117acd0b01ffd8109ae265c22
wheel_sha256: 714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff
```

The installed wheel must match the approved SHA-256 value. Approval of the
distribution does not replace implementation evidence for the decision-trace
adapter, malformed-input behavior, or Crawl-delay capability.

Matching shall be deterministic for the same snapshot, selected user agent,
and canonical target URL.

The parser shall retain enough normalized evidence to explain:

```text
which user-agent group matched
which Allow or Disallow rule matched
the matched pattern
the rule location when available
the match specificity
the final external decision
any parse warnings
```

Malformed lines shall not silently become valid directives. A parse result that
cannot produce a trustworthy evaluation shall be `unavailable`; it shall not
be guessed as allowed or disallowed.

Missing or empty robots resources shall follow registered parser and policy
semantics that are explicitly documented and tested.

## 7. Cache and Revalidation

The policy registry shall define:

```text
acquisition.robots.cache.max_age_seconds
acquisition.robots.cache.max_stale_seconds
```

A snapshot is:

```text
fresh:
    now <= fresh_until

stale but conditionally usable:
    fresh_until < now <= stale_until

expired:
    now > stale_until
```

Fresh snapshots may be evaluated without retrieval.

Stale snapshots may be used only according to the registered unavailable-action
policy while GNI attempts bounded revalidation. The operation result shall
state that stale evidence was used.

Expired snapshots shall not be treated as current robots evidence.

Revalidation produces a new immutable retrieval record or explicit 304
linkage. It never mutates historical evidence.

## 8. Owner Policy Family

### 8.1 `acquisition.robots.enforce`

```text
value type:
    boolean

default:
    true

supported scopes:
    global, adapter, platform, credential, origin, Source, endpoint, request

resolution point:
    after exact robots evaluation and before target request authorization

restart requirement:
    none

external consequence:
    false may cause GNI to request a target that robots evidence disallows;
    it does not force the origin to return content and does not change the
    external robots decision

audit evidence:
    full OwnerPolicyDecisionContext linked to robots evaluation and operation

default-path test:
    disallowed evaluation installs/governs exact gate and prevents request

override-path test:
    exact audited false permits request while preserving external disallow
```

### 8.2 `acquisition.robots.unavailable_action`

```text
value type:
    enum

allowed values:
    delay
    allow
    deny

default:
    delay

supported scopes:
    global, adapter, platform, credential, origin, Source, endpoint, request

resolution point:
    when no trustworthy fresh evaluation exists

restart requirement:
    none

external consequence:
    allow may issue a request without current usable robots evidence;
    deny may prevent acquisition until policy or evidence changes;
    delay schedules revalidation without claiming an external denial

audit evidence:
    selected policy, unavailable reason, prior snapshot when present,
    effective decision, and next eligibility

default-path test:
    unavailable evidence delays the exact request

override-path test:
    exact audited allow or deny produces the selected different decision
```

### 8.3 `acquisition.robots.crawl_delay.enforce`

```text
value type:
    boolean

default:
    true for the approved version-one parser distribution

validation:
    boolean only

supported scopes:
    global, adapter, platform, credential, origin, Source, endpoint, request

resolution point:
    after parsed crawl-delay observation and before reservation

restart requirement:
    none

external consequence:
    false may cause requests sooner than observed crawl-delay guidance

audit evidence:
    observed delay, parser support, selected policy, and effective schedule
```

### 8.4 `acquisition.robots.cache.max_age_seconds`

```text
value type:
    positive integer

default:
    86400

validation:
    integer, excluding boolean; minimum 300; maximum 86400

supported scopes:
    global, adapter, platform, origin, Source, endpoint

resolution point:
    calculating fresh_until

restart requirement:
    none

external consequence:
    larger values reduce retrieval frequency but may retain changed guidance
    longer; smaller values increase robots retrieval traffic
```

### 8.5 `acquisition.robots.cache.max_stale_seconds`

```text
value type:
    nonnegative integer

default:
    604800

validation:
    integer, excluding boolean; minimum 0; maximum 2592000

supported scopes:
    global, adapter, platform, origin, Source, endpoint

resolution point:
    calculating stale_until

restart requirement:
    none
```

### 8.6 `acquisition.robots.fetch_limits`

```text
value type:
    closed versioned JSON object

required fields:
    max_response_bytes
    max_redirects
    connect_timeout_seconds
    read_timeout_seconds

validation:
    all fields are integers and boolean values are rejected;
    max_response_bytes: 524288 through 2097152;
    max_redirects: 5 through 10;
    connect_timeout_seconds: 1 through 30;
    read_timeout_seconds: 1 through 60;
    missing or unknown fields are rejected in v1

default:
    max_response_bytes: 524288
    max_redirects: 5
    connect_timeout_seconds: 10
    read_timeout_seconds: 30

supported scopes:
    global, adapter, platform, origin, Source, endpoint

resolution point:
    before robots retrieval

restart requirement:
    none
```

Scoped cache and fetch-limit values may be more conservative than the approved
defaults. No scoped value may exceed installation-owned egress hard limits.

Any default values not fixed above require explicit Owner approval before this
specification may be marked implemented.

## 9. Effective Decision Matrix

### 9.1 External decision allowed

```text
robots enforce true:
    permit request

robots enforce false:
    permit request

gate:
    clear any exact prior robots gate governed by older evidence
```

### 9.2 External decision disallowed

```text
robots enforce true:
    block or delay exact request
    install or replace exact robots gate

robots enforce false:
    permit exact request
    retain disallowed evaluation
    do not install a governing robots gate for that request
```

The overridden path uses reason:

```text
acquisition.robots_restriction_not_enforced
```

### 9.3 External decision unavailable

The effective action comes from
`acquisition.robots.unavailable_action`.

```text
delay:
    install or replace exact robots_unavailable gate
    schedule bounded revalidation

allow:
    permit exact request
    retain unavailable evidence

deny:
    block exact request
    install or replace exact robots_unavailable gate
```

`deny` is a GNI policy decision, not an external robots denial.

## 10. Gate Reconciliation

The implementation shall provide an exact operation equivalent to:

```python
reconcile_robots_gate(
    previous_gate,
    current_evaluation,
    effective_policy,
    valid_until,
)
```

It shall support:

```text
new disallow:
    install exact active gate

changed disallow:
    supersede prior exact gate and install replacement

new allow:
    clear prior exact gate

unavailable with delay or deny:
    install or replace exact unavailable gate

unavailable with allow:
    clear prior governing gate when policy authorizes proceeding

expired evidence:
    expire gate or require revalidation

Owner override revoked, expired, or exhausted:
    re-evaluate still-valid evidence and install the gate when enforcement
    again controls
```

A previous generic `blocked_until` or `robots_disallow_until` value shall not
survive as hidden robots state after reconciliation.

## 11. Generic Rate-Limit Integration

The existing generic `AcquisitionRateLimitService.observe_hold()` iterates
through every bucket attached to a reservation. Proof 34 shall not use that
method unchanged for robots.

Robots evaluation and gate state shall be resolved before target request
reservation or through a robots-specific exact gate service.

Rate reservation may consult the exact robots gate for the endpoint/request,
but shall not copy it to installation, adapter, platform, credential, origin,
or Source buckets.

A generic observation may retain bounded references:

```text
robots_snapshot_public_id
robots_evaluation_public_id
robots_gate_public_id
owner_policy_decision_fingerprint
```

It shall not become the authoritative robots evidence record.

## 12. Owner Operation Information

Every robots retrieval and evaluation shall produce or support an
`OwnerOperationResult`.

Required operation types:

```text
acquisition.retrieve_robots
acquisition.evaluate_robots
acquisition.retrieve_resource
```

Required reason/detail combinations include:

```text
acquisition.robots_path_allowed
    acquisition.robots_path_allowed.v1

acquisition.robots_path_disallowed
    acquisition.robots_path_disallowed.v1

acquisition.robots_evidence_unavailable
    acquisition.robots_evidence_unavailable.v1

acquisition.robots_evidence_unreachable
    acquisition.robots_evidence_unreachable.v1

acquisition.robots_evidence_stale
    acquisition.robots_evidence_stale.v1

acquisition.robots_restriction_not_enforced
    acquisition.robots_restriction_not_enforced.v1
```

The disallowed detail schema shall include:

```text
canonical_target_url
target_path
robots_url
snapshot_public_id
evaluation_public_id
selected_user_agent
matched_group
matched_directive
matched_pattern
matched_line_or_location
match_specificity
parser_name
parser_version
evaluated_at
external_decision
effective_enforcement
selected_override_public_id, nullable
```

The unavailable detail schema shall include:

```text
robots_url
retrieval_state
parse_state
latest_snapshot_public_id, nullable
fresh_until, nullable
stale_until, nullable
unavailable_reason
effective_unavailable_action
next_eligible_at, nullable
selected_override_public_id, nullable
```

All fields are bounded and sanitized.

## 13. Owner-Facing UI

The Acquisition Health row may add only a compact summary:

```text
Robots:
    Allows | Disallows | Unavailable | Stale | Not checked

Effective enforcement:
    On | Owner override

Next robots review:
    date only by default

Action:
    Override when Disallows | Review decision
```

The dedicated detail view shall show:

1. current effective GNI decision;
2. external robots evaluation;
3. selected user agent and matched rule;
4. snapshot retrieval and parser provenance;
5. policy-resolution chain;
6. exact robots gate and next eligibility;
7. scope and impact preview;
8. override history;
9. snapshot/evaluation/gate history;
10. available Owner action.

For an external `disallowed` result, the compact publisher-relative interface
shows a red `Disallows` badge with an adjacent `Override` button. After an
authenticated Owner override becomes effective, the badge becomes green while
retaining `Disallows`; an accessible `Owner override active` state separately
communicates effective enforcement. The external result remains disallowed.

For an external `allowed` result, the interface shows a green `Allows` badge.
Color never replaces the external-result text or accessible effective-policy
state.

The Override action authorizes an intermediary fetch attempt but cannot force
an external publisher or network to return content. It does not silently alter
other independently resolved GNI policies; each remains subject to Owner
authority under its registered definition. Browser mutation implements the
authentication, authorization, CSRF, reauthentication, confirmation,
stale-preview, transactional, and append-only audit safeguards in the
Owner-policy standard. Time is not displayed by default.

## 14. Concurrency and Transactions

Snapshot selection, evaluation, Owner policy resolution, gate reconciliation,
and target request authorization shall be transactionally coherent.

The implementation shall prevent:

```text
conflicting active gates for the same exact scope
a request proceeding on evidence superseded before reservation
a stale UI preview creating a different override than reviewed
a one-use override consumed without the governed runtime decision
an older evaluation clearing a newer gate
```

## 15. Required Proof-34 Tests

At minimum:

```text
fresh snapshot allows exact path under default enforcement
fresh snapshot disallows exact path under default enforcement
one path denial does not block another allowed path
denial does not contaminate installation buckets
denial does not contaminate adapter buckets
denial does not contaminate Source buckets
one path denial does not become origin-wide
endpoint override false permits acquisition and retains external disallow
request override defeats endpoint value
endpoint value defeats less-specific scopes
priority resolves equal-scope values
expired override does not apply
revoked override does not apply
one-use override consumed only by actual request decision
viewing and previewing do not consume authority
changed disallow to allow clears exact gate
changed disallow replaces older gate
stale, unreachable, and malformed evidence follow unavailable policy
304 revalidation retains prior parsed evidence with explicit linkage
expired evidence is not treated as current
override revocation causes still-valid disallow to govern again
observation references exact snapshot and evaluation
UI and worker show the same effective decision
missing or invalid target-bound robots evidence remains unavailable and the Owner-controlled unavailable action governs
missing, stale, mismatched, or untrusted intermediary evidence follows unavailable policy
allowed evidence renders green Allows relative to the publisher
enforced disallowed evidence renders red Disallows with Override action
effective Owner override renders green Disallows and preserves the external disallow
Override mutation satisfies authentication, confirmation, stale-preview, and audit controls
stale UI preview is rejected
secret headers and credentials are absent from evidence
oversized body is rejected according to fetch limits
redirect and egress controls remain enforced
downgrade refuses when robots history would be lost
schema drift is zero
```

## 16. Completion Criteria

Proof 34 may be marked complete only when:

```text
policy keys and approved defaults are registered
database migrations and constraints are present
retrieval, caching, parsing, and revalidation are implemented
exact evaluations are persisted
exact gates reconcile without generic bucket contamination
Owner policy context is linked and non-consuming explanations work
OwnerOperationResult projections are implemented
owner-facing detail UI and approved exact Override action are implemented
all focused and repository tests pass
runtime proof demonstrates allow, deny, unavailable, override, reconciliation
change report records exact evidence and remaining exclusions
```

## 17. Current Implementation Status

```text
acquisition.robots.enforce registration            implemented foundation
worker resolution of robots enforcement             implemented foundation
generic robots bucket field                         implemented but not adequate
robots retrieval                                    not implemented
robots parser                                       not implemented
robots snapshots                                    persistence foundation implemented
robots evaluations                                  persistence foundation implemented
exact robots gates                                  persistence foundation implemented
gate reconciliation                                 not implemented
remaining robots policy keys                        registered; runtime use pending
OwnerOperationResult integration                    not implemented
Owner policy explain/preview                        service foundation implemented
proof-34 detail UI                                  not implemented
proof 34                                           incomplete
```

The existing generic all-bucket robots hold behavior shall not be treated as
proof-34 conformance.
