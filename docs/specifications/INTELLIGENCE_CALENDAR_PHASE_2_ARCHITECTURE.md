# Intelligence Calendar Phase 2 Architecture

**Status:** ARCHITECTURE FROZEN
**Date:** 2026-07-28
**Phase:** Calendar Phase 2 — Validation Automation and Relationship Enrichment
**Depends on:** Calendar Phase 1 frozen at `f29b6d8e3c10`
**Authority:** Owner-approved autonomous-operation directive
**Implementation status:** CORRECTIVE MIGRATIONS, PERSISTENCE, SERVICES, AND
WORKERS IMPLEMENTED AS AN UNFROZEN CANDIDATE

## 1. Purpose and Fixed Requirement

Calendar Phase 2 adds autonomous evidence corroboration, contextual
source-authority assessment, validation inference, canonical relationship
enrichment, conflict resolution, occurrence-specific policy controls, and
advanced evidence/history interfaces.

The following requirement is fixed:

> GNI must remain autonomous during normal operation. Operator participation
> must be optional and exceptional. Explicit operator actions have canonical
> authority when exercised, but normal validation, enrichment, relationship
> inference, story processing, Calendar processing, and downstream
> intelligence output must never depend on operator participation.

The ordinary path is:

```text
evidence
    ↓
corroboration and source-authority assessment
    ↓
validation and relationship inference
    ↓
machine-derived assertions
    ↓
effective enriched intelligence
```

No approval queue is present in that path.

## 2. Phase 1 Actor-Kind Erratum

Calendar Phase 1 currently implements:

```text
operator | system | import | ai_job
```

`ai_job` was not an approved actor kind. It loses the required distinction
between GNI-controlled local inference and an externally hosted fallback
model. Phase 2 must begin with an explicit corrective migration to:

```text
operator
system
import
internal_agent
external_model
```

The meanings are:

| Actor kind | Meaning |
|---|---|
| `operator` | An explicit human action. |
| `system` | Deterministic application or worker behavior without model inference. |
| `import` | Structured ingestion from an external calendar or other source. |
| `internal_agent` | GNI's internal agent or a locally routed model. |
| `external_model` | An externally hosted fallback model reached through the LLM Router. |

`internal_agent` and `external_model` are both machine-controlled for
effective-state precedence. An external model has no authority to supersede
an active operator assertion.

The correction must be truthful:

1. inspect every Calendar table containing `actor_kind`;
2. refuse automatic migration if an `ai_job` row cannot be classified from
   durable provenance;
3. map no ambiguous row silently;
4. replace every database, ORM, schema, API, and documentation constraint;
5. prove that new `ai_job` writes are rejected.

Generic `ai_jobs` infrastructure may continue to exist in AI-routing or other
subsystems. This erratum concerns the Calendar `actor_kind` vocabulary, not
the name of a generic job table.

### 2.1 Actor Kind Versus Semantic Derivation Method

`actor_kind` answers **who or what executed the Calendar action**. It must not
replace GFA-C's frozen `semantic_assignment_methods` vocabulary, which answers
**how the semantic conclusion was derived**.

Phase 2 assertion and authority-assessment rows reuse:

```text
manual
rule
external_mapping
internal_autonomous_agent
external_ai_model
import
```

as their semantic derivation method through a foreign key to
`semantic_assignment_methods.slug`.

Examples:

```text
actor_kind = system
assignment_method = rule
    deterministic Calendar constraints produced the decision

actor_kind = internal_agent
assignment_method = external_mapping
    the agent applied an explicit stored ontology crosswalk

actor_kind = internal_agent
assignment_method = internal_autonomous_agent
    the GNI agent evaluated evidence and owned the semantic decision,
    even if it called a model as one tool

actor_kind = external_model
assignment_method = external_ai_model
    an external model directly produced the accepted machine conclusion
```

An external provider call made and independently adjudicated by a GNI agent
does not automatically change the derivation method to `external_ai_model`.
Provider/model provenance remains mandatory regardless of the method.

## 3. Machine State, Operator State, and Effective State

Phase 2 separates:

```text
machine-derived state
operator-controlled state
effective state
```

Machine-derived state is maintained autonomously from evidence. Operator state
exists only after an explicit operator action.

Authority layer is derived without a second mutable source of truth:

```text
actor_kind = operator
    → operator-controlled

actor_kind = system | import | internal_agent | external_model
    → machine-controlled
```

Operator-controlled semantic assertions use
`assignment_method = manual`. Database enforcement must reject an operator
override that points to a non-operator assertion or a machine assertion
misrepresented as manual authority.

The resolver is:

```text
effective state =
    active operator-controlled assertion, if present
    otherwise the current defensible machine-derived assertion
    otherwise no effective assertion
```

An operator override does not delete, mutate, or stop machine inference.
Machine evidence and conclusions continue accumulating beneath the override.
Withdrawing an override exposes the newest defensible machine-derived state,
not the stale machine state that existed when the override was created.

The effective-state service is the only supported read path for consumers
that need the authoritative current answer. Administrative diagnostics may
read the underlying assertion and conflict ledgers directly.

## 4. Machine-Derived Assertions

Ordinary automated output is a **machine-derived assertion**, not a
suggestion. It is immediately usable when it satisfies canonical constraints
and the confidence/resolution policy.

Examples aligned with frozen repository vocabularies include:

```text
Document → Entity with entity_role = mentioned

Entity → Geography with relationship_type =
    located_in | headquartered_in | based_in | jurisdiction_in |
    operates_in | incorporated_in | founded_in | born_in |
    resident_in | citizen_of

Calendar Event → Geography with role =
    venue | jurisdiction | affected_area | participant_location

Calendar Event → Topic with role =
    primary | secondary

Calendar Event → Entity with role =
    organizer | participant | subject | speaker | host

Calendar Event → Source with role =
    official | expected | reference
```

`associated_with`, `mentions`, and `related_to` are not introduced as broad
replacement slugs. Story-to-Topic enrichment and Source-to-Entity ownership
semantics remain outside Calendar Phase 2 until their owning foundations
exist.

Every machine assertion retains:

```text
actor_kind
assignment_method
confidence
inference run
resolution decision
supporting and contradictory evidence
provenance
validity
model/provider identity when used
ruleset, prompt, or strategy version
input and output hashes
```

Canonical targets use real foreign keys. Target identity, relationship role,
validation state, or assertion polarity must not exist only inside JSON.

## 5. Contextual Source-Authority Assessment

Source authority is an assessment, not a permanent universal reliability
score on `sources`.

An authority assessment is contextual to:

```text
the claim or assertion being evaluated
the Calendar Event and optional Occurrence
the source or document
the relevant time interval
the assessment method and ruleset
the evidence available at that time
```

An official source may be authoritative for its own schedule while being only
one interested party for a disputed interpretation. A publisher's country is
not Event geography, and Source authority must not imply geography,
document type, entity ancestry, or topic.

Authority assessments are append-only and versioned. Later evidence may
supersede an assessment without erasing the earlier basis.
Phase 1 `intelligence_calendar_event_evidence.authority_score` remains the
immutable assessment snapshot recorded with that evidence item. Phase 2
assessment history explains and versions authority decisions; it does not
rewrite the Phase 1 evidence row.

An authority assessment stores two distinct numeric values:

```text
authority_score
    assessed authority of the source for the specific claim and context

assessment_confidence
    confidence in that authority assessment
```

Neither value is assertion confidence. Confidence fusion and validation-state
mapping use a versioned policy; they must not be implemented as an
installation-global unversioned threshold or a naive maximum/average that
discards contradictory evidence.

## 6. Autonomous Conflict Resolution

Normal corroboration may resolve differences without invoking a model.
When incompatible assertions remain, GNI opens a machine conflict and
attempts autonomous resolution.

The required sequence is:

```text
initial inference
        ↓
conflict detected
        ↓
Pass 1 — internal_agent resolution
        ↓ unresolved
Pass 2 — internal_agent critical re-evaluation
        ↓ unresolved and high/critical
Pass 3 — external_model adjudication when configured and eligible
        ↓ unresolved
administrative exception
```

### 6.1 Pass 1 — Internal Resolution

The internal agent receives all competing assertions, supporting and
contradictory evidence, contextual authority assessments, canonical
constraints, temporal context, confidence calculations, and relevant
historical state.

### 6.2 Pass 2 — Internal Critical Re-evaluation

Pass 2 must be materially distinct from Pass 1. It must use a different
strategy or prompt version and explicitly:

- challenge the first conclusion;
- search for overlooked contradictory evidence;
- test alternative identity and relationship interpretations;
- reapply canonical domain, range, taxonomy, temporal, and cardinality rules;
- explain why each assertion should be accepted, superseded, denied, or left
  unresolved.

Repeating the same model request with the same strategy is not a second
reasoning pass.

### 6.3 Pass 3 — External Adjudication

An unresolved high-risk or critical conflict should receive an
`external_model` adjudication when an external provider is configured,
eligible under routing and egress policy, and operationally available.

Only the minimum necessary evidence is sent externally. The run records the
provider, model, model version when available, router decision, request
strategy, input hash, output hash, and redaction/egress policy.

An external result remains machine-derived. It may not override active
operator-controlled state.

### 6.4 Attempts Versus Infrastructure Retries

A transport retry, timeout, malformed response, or provider failure is not a
reasoning pass. A completed resolution attempt must produce a structurally
valid decision or an explicit valid `unresolved` conclusion.

Each attempt records:

```text
attempt number
actor kind
resolution strategy and version
provider, model, and model version
router decision
evidence/input snapshot hash
structured conclusion
confidence
conflict outcome
start and completion timestamps
failure information
process/run identity
```

The same conflict, evidence hash, actor, model, and strategy is idempotent.
Worker replay must not consume the resolution budget twice.

### 6.5 Resolver and Roadmap Dependency Boundary

Calendar Phase 2 owns the `calendar_validation` orchestration contract, not a
provider-specific model client. It requires a provider-neutral internal-agent
adapter capable of completing the two distinct strategies:

```text
evidence reconciliation
adversarial canonical-constraint review
```

The internal agent may orchestrate deterministic tools, retrieval, and a
locally routed model. Any model request passes through the LLM Router or its
provider-neutral service abstraction.

The later main-roadmap Local AI phase still owns general vLLM deployment,
model selection, batching, and broad AI workloads. The later OpenAI
Integration phase still owns production provider rollout, budgets, and
general fallback policy. Calendar Phase 2 must not call ChatGPT, OpenAI, or
another provider directly to bypass those owners.

Phase 2 implementation may proceed in layers:

```text
persistence and deterministic normal inference
        ↓
provider-neutral internal resolution adapter
        ↓
optional external provider activated only when the LLM Router reports it
configured, eligible, within budget, and healthy
```

Formal Phase 2 freeze requires direct proof of two real, materially distinct
internal-agent strategies. A test provider may prove external routing and
failure behavior; production external escalation remains inactive until a
real provider is explicitly configured.

If internal-agent infrastructure is temporarily unavailable, GNI records an
operational failure and retries under a bounded infrastructure policy. It
does not fabricate a completed reasoning pass. The conflict remains
unresolved without blocking unrelated processing, and no administrative
inference exception is created until the required internal attempts complete.

## 7. Conflict and Exception State Machines

A machine conflict uses:

```text
detected
resolving
resolved
unresolved
superseded
```

`unresolved_conflict` is not a Calendar validation-state slug. When a conflict
prevents a defensible validation conclusion, the effective Calendar
validation may be `disputed`; otherwise the system may retain the last
defensible effective assertion with explicit conflict metadata and adjusted
confidence.

An administrative exception uses:

```text
open
resolved
closed
```

There is deliberately no implicit `accepted`, `rejected`, or `deferred`
state. Operator inaction does not create an action.

`open → resolved` requires a recorded machine or operator resolution of the
underlying conflict. `open → closed` requires an explicit operator action and
does not itself resolve the conflict or change effective canonical state.
Later evidence may supersede a conflict and its exception, but no exception,
attempt, evidence, or action history is deleted.

Only genuinely exceptional high-risk or critical conflicts enter the
Administrative Queue. Low or normal ambiguity remains machine-managed and
may result in lower confidence or no effective assertion.

Queue admission uses installation-global, versioned epistemic/integrity risk,
not Coverage Profile monitoring priority or expected news importance.
Profile-specific policy may rank or filter an exception for operational
attention, but it cannot create, suppress, or resolve the canonical conflict.

An exception may be created only after:

1. at least two completed, materially distinct internal resolution attempts;
2. a third external attempt for eligible high/critical conflicts when an
   external model is configured and available; or
3. a durable record that the external attempt was ineligible or unavailable.

The affected assertion may remain unresolved. Unrelated ingestion,
classification, Monitor evaluation, alerts, Calendar processing, and
downstream intelligence continue.

## 8. Operator Overrides

Permitted explicit operator actions include:

```text
assert a canonical resolution
select one competing assertion
deny a proposed resolution
withdraw an earlier override
leave the exception unresolved
```

Operator assertions are append-only. Correction, withdrawal, and
supersession create new history rather than overwriting the original action.
Every action records actor reference, reason, time, affected resources, and
supporting evidence when supplied.

Operator authority applies to the exact controlled assertion scope. It does
not silently grant authority over unrelated relationships, Events,
Occurrences, Coverage Profiles, or future observed Events.

No timeout or operator silence is interpreted as a decision.

## 9. Coverage Profile Boundary

Canonical Event facts remain installation-global. Coverage Profile policy is
profile-specific operational configuration.

Coverage Profile policy may govern:

```text
profile-specific display or operational urgency for an existing conflict
whether external-model escalation is permitted for separately profile-owned processing
monitoring and expected-news-importance policy
watch behavior and occurrence-specific policy
polling or YouTube escalation permission in later phases
```

It may not change an installation-global machine or operator assertion merely
because one profile values the Event differently. Any policy-dependent
effective result must be explicitly profile-scoped.

Installation-global Calendar inference uses installation-level LLM Router
egress, privacy, provider, health, and budget policy. Coverage Profile policy
does not authorize external transmission of installation-global evidence and
does not select which canonical assertion is true.

Phase 1 already created
`intelligence_calendar_occurrence_policy_overrides`. Phase 2 adds the
service, API, UI, validation, provenance, and history needed to use that table
safely; it does not create a duplicate policy-override store.

## 10. Proposed Persistence Package

The Phase 2 migration should add the following normalized records. Exact
column sizing and index names remain implementation details, but the
ownership and foreign-key boundaries are normative.

### 10.1 `intelligence_calendar_inference_runs`

One auditable inference execution:

```text
Event and optional Occurrence
trigger and pipeline version
status
evidence snapshot hash
ruleset and strategy versions
start/completion
error
provenance
```

### 10.2 `intelligence_calendar_assertion_ledger`

Append-only machine or operator assertions. The row identifies exactly one
supported assertion family:

```text
Event/Occurrence validation state
Event → Geography and role
Event → Topic and role
Event → Entity and role
Event → Source and role
```

Controlled columns hold target foreign keys, role, state, polarity,
confidence, assignment method, actor kind, validity, inference run, immutable
assertion action, and an optional
`supersedes_assertion_id` carried by the newer row. Database checks require
the exact fields appropriate to the assertion family.

Assertion actions use:

```text
affirm
deny
withdraw
```

Supersession must remain within the same normalized logical assertion scope
and authority layer. A unique forward-only supersession edge makes each
machine or operator history linear and acyclic. The current head is derived
from the immutable chain; an old assertion row is never updated merely to mark
it non-current.

### 10.3 `intelligence_calendar_assertion_evidence`

Many-to-many links from assertion-ledger rows to Phase 1 Calendar evidence.
Links identify supporting, contradicting, or correcting use without copying
evidence into JSON.

### 10.4 `intelligence_calendar_source_authority_assessments`

Contextual, versioned source/document authority assessments linked to the
Event, optional Occurrence, inference run, `authority_score`,
`assessment_confidence`, assignment method, validity, and provenance.

### 10.5 `intelligence_calendar_source_authority_evidence`

Many-to-many links from authority assessments to the evidence used to
calculate them. New corroboration appends links or a superseding assessment;
it does not replace earlier evidence.

### 10.6 `intelligence_calendar_inference_conflicts`

One durable conflict identity with affected assertion scope, severity,
reason, state, evidence snapshot, detection run, normalized selected-assertion
reference when resolved, decision provenance, and timestamps. A selected
canonical assertion must not exist only in diagnostic JSON.

### 10.7 `intelligence_calendar_conflict_assertions`

Normalized membership linking every competing assertion to the conflict.
No competing conclusion is discarded when a winner is selected.

### 10.8 `intelligence_calendar_resolution_attempts`

Append-only attempts with ordinal, actor kind, strategy, model/router
provenance, hashes, normalized selected-assertion reference when one is
chosen, structured rationale, outcome, timing, and failure data. A uniqueness
key enforces idempotency for a substantive attempt.

### 10.9 `intelligence_calendar_administrative_exceptions`

At most one active exception per unresolved conflict. It stores high/critical
severity, reason autonomous resolution failed, proposed resolution when one
exists, a normalized proposed-assertion reference, queue state, and
timestamps.

### 10.10 `intelligence_calendar_operator_overrides`

An immutable operator authority/action record referencing the operator
assertion, the affected conflict when applicable, action kind, reason, actor
provenance, activation, and optional `supersedes_override_id`. Withdrawal and
replacement append new rows; they do not update the earlier override.

### 10.11 `intelligence_calendar_occurrence_policy_override_history`

Append-only history for changes to the existing Phase 1 effective
`intelligence_calendar_occurrence_policy_overrides` row. The history records
old and new values, actor, reason, and timestamp in the same transaction as
the effective policy change.

### 10.12 Effective Projection

The Phase 1 validation columns and canonical relationship tables remain the
compatibility-facing effective projection. A single transactional resolver
publishes changes from the assertion ledger while preserving the underlying
machine and operator histories.

The implementation must not create two competing effective read paths.
Projection changes and their Phase 1 state/relationship histories commit in
the same transaction.

Validation projection must traverse the legal Phase 1 validation state
machine. When the effective result requires more than one legal edge, every
intermediate transition is explicit and historied; Phase 2 may not bypass the
frozen state machine with a direct column update.

## 11. Worker and Transaction Boundaries

`calendar-validation-worker` owns Phase 2 autonomous processing.

Its task input contains stable database identifiers, not embedded evidence or
model output. A logical run:

1. claims an Event/Occurrence and evidence snapshot idempotently;
2. records or reuses the inference run;
3. calculates contextual source authority;
4. writes candidate assertions and conflicts;
5. commits before optional model I/O;
6. records each resolution attempt independently;
7. transactionally publishes effective assertions or creates an exception;
8. emits metrics and structured logs.

No database transaction remains open during model or network I/O.
Infrastructure retries and reasoning attempts have separate budgets.

The worker must tolerate:

```text
duplicate tasks
late evidence
model timeout or invalid output
internal-agent infrastructure unavailable
external provider unavailability
operator override arriving during inference
conflict supersession while a pass is running
```

Row locks or compare-and-swap version checks prevent a stale attempt from
overwriting a newer operator action or evidence snapshot.

## 12. API and Administrative UI Boundary

Normal Calendar APIs return effective state with summary provenance. Detail
interfaces may expose machine state, active operator state, confidence,
evidence, and unresolved-conflict indicators.

The Administrative Queue is a separate exception view. It includes:

```text
exception type and severity
affected resources
competing assertions
all autonomous attempts
model and process identities
confidence and authority assessments
supporting and contradictory evidence
reason autonomous resolution failed
proposed resolution when available
operator action history
```

The queue must support filtering and inspection without implying that every
row requires action. It must never be placed in the normal ingestion or
Calendar completion path.

## 13. Deliberately Deferred

Calendar Phase 2 does not add:

```text
Story-to-Topic assertions
Source-to-Entity ownership semantics
official-calendar ingestion
AI future-event candidate discovery
temporary Monitor scheduling
source-polling or YouTube escalation
observed real-world Event correlation
post-event analysis
```

Those remain owned by later main-track or Calendar phases.

## 14. Required Proof Matrix

The Phase 2 freeze candidate must directly prove:

| # | Required proof |
|---:|---|
| 1 | Calendar accepts `internal_agent` and `external_model` actor kinds. |
| 2 | Calendar rejects new `ai_job` actor values. |
| 3 | Migration refuses to guess when a historical `ai_job` row is ambiguous. |
| 4 | A normal machine assertion becomes effective without operator review. |
| 5 | Machine inference continues while an operator override is active. |
| 6 | An active operator assertion wins the effective-state resolver. |
| 7 | Withdrawing an override exposes the newest defensible machine state. |
| 8 | Machine and operator histories remain append-only and lossless. |
| 9 | Supporting and contradictory evidence both survive resolution. |
| 10 | Exact evidence and worker replay are idempotent. |
| 11 | A conflict cannot create an exception after only one internal attempt. |
| 12 | Two internal attempts use materially distinct strategy versions. |
| 13 | An eligible unresolved high/critical conflict receives an external pass. |
| 14 | External-model unavailability is recorded and does not block the pipeline. |
| 15 | Transport retries do not consume reasoning-attempt ordinals. |
| 16 | A stale model result cannot overwrite a newer operator action. |
| 17 | External-model output remains machine-controlled. |
| 18 | Inaction creates no acceptance, rejection, deferral, or confirmation. |
| 19 | Only high/critical unresolved conflicts enter the Administrative Queue. |
| 20 | An unresolved exception does not block unrelated processing. |
| 21 | `unresolved_conflict` is rejected as a Calendar validation state. |
| 22 | Contextual authority assessment does not become global Source reliability. |
| 23 | Source country does not generate Event geography. |
| 24 | Entity ancestry does not generate Event geography. |
| 25 | Canonical GFA-C relationship slugs and domain/range rules are enforced. |
| 26 | Calendar relationship roles use their frozen per-table vocabularies. |
| 27 | Coverage Profile policy cannot rewrite installation-global assertions. |
| 28 | Occurrence policy override belongs to the same Event/Profile policy scope. |
| 29 | Occurrence policy changes preserve append-only same-transaction history. |
| 30 | Effective publication and Phase 1 history commit atomically. |
| 31 | Model, router, strategy, run, confidence, evidence, and provenance survive. |
| 32 | The current Phase 1 Calendar API remains compatible through effective projection. |
| 33 | Clean migration, guarded downgrade, regression, and zero-drift checks pass. |
| 34 | Actor kind and semantic assignment method remain separate controlled dimensions. |
| 35 | Internal-agent model/tool use retains `internal_autonomous_agent` when the agent owns the decision. |
| 36 | Direct external-model acceptance uses `external_ai_model` and full provider provenance. |
| 37 | Missing internal infrastructure creates no fake completed resolution attempt. |
| 38 | Calendar code performs no direct provider call outside the routing abstraction. |
| 39 | Installation-level egress policy, not Coverage Profile policy, controls global evidence transmission. |
| 40 | Profile priority cannot create, suppress, or resolve a canonical conflict. |
| 41 | Source authority score, assessment confidence, and assertion confidence remain distinct. |
| 42 | Supersession is forward-only, same-scope, linear, and leaves immutable rows unchanged. |
| 43 | Resolved decisions and proposed resolutions reference normalized assertions. |
| 44 | Effective validation changes preserve every legal intermediate Phase 1 transition. |

## 15. Implementation Sequence

```text
Phase 2 architecture review
        ↓
actor-kind corrective migration
        ↓
inference, assertion, authority, and conflict persistence
        ↓
provider-neutral internal resolution adapter, service, and worker
        ↓
effective-state and operator-override service
        ↓
Administrative Queue and advanced evidence/history UI
        ↓
formal Calendar Phase 2 freeze review
```

No Calendar Phase 2 implementation is frozen by this document alone. The
schema, services, worker, APIs, UI, operations, migration safety, and complete
proof matrix must pass formal review.

## 16. Formal Architecture Freeze Review

The formal architecture review found and corrected three blockers:

```text
Calendar actor kinds were not explicitly separated from GFA-C's frozen
semantic derivation methods

the two-pass internal-agent and third-pass external-model contract did not
define an implementable boundary with the later Local AI, AI Routing, and
OpenAI Integration roadmap phases

Coverage Profile operational priority could be misread as controlling
installation-global conflict severity or external evidence egress
```

Review hardening also requires distinct authority/assessment/assertion
confidence, immutable same-scope assertion chains, normalized selected and
proposed assertion references, provider-neutral model routing, bounded
operational failure handling, and legal Phase 1 transition paths for every
effective validation change.

The reconciled architecture:

```text
preserves autonomous normal operation
requires two materially distinct internal-agent attempts
uses an eligible third external-model pass without direct provider coupling
keeps operator participation optional and authoritative when exercised
keeps Administrative Queue exceptions rare and nonblocking
preserves all machine, operator, evidence, attempt, and decision history
reuses GFA-C semantic methods and canonical relationship vocabularies
preserves the GFA-E canonical-versus-profile boundary
```

All 44 required implementation proofs are explicit. Documentation
consistency, Markdown structure, obsolete review-gate wording, whitespace,
and repository-scope checks passed. The local isolated project database was
confirmed at Calendar Phase 1 head `f29b6d8e3c10`; no migration or runtime
change was made during this review. A read-only actor preflight found zero
Calendar actor rows and therefore zero existing `ai_job` rows in that
isolated database; the corrective migration must still retain its ambiguity
guard for every target deployment.

Calendar Phase 2 architecture is frozen. The next work is the guarded
actor-kind corrective migration and Phase 2 persistence foundation. Calendar
Phase 2 implementation remains unfrozen until all 44 proofs and the complete
regression, migration, operational, and zero-drift review pass.
