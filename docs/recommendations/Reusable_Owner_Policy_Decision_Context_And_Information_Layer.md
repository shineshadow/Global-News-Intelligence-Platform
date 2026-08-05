## Consolidated Recommendation

**Status:** Superseded
**Superseded:** 08-04-2026
**Superseded by:** `docs/recommendations/Reusable_Owner_Operation_Information_And_Policy_Decision_Context.md`

Recommendation pertaining to the recommendation and incorperation of a Owner Information Model found in this document: `docs/recommendations/Owner_Information_Model.md`

**Incorporate the capability now, with proof 34 as its first implementation—but make it a reusable Owner Policy Decision Context layer, not a robots-specific override feature.**

The timing is right because the repository already has:

* The governing owner-authority ledger and precedence model.
* Runtime resolution of `acquisition.robots.enforce`.
* Durable rate buckets and generic robots observation support.
* The Acquisition Health UI where the decision information naturally belongs.
* A formal UI component registry and acceptance process.

Proof 34 explicitly requires robots/provider restrictions to be observed and enforced by default while allowing an exact, audited owner decision to produce a different outcome.

The attachment itself was not exposed in the file index available to me, so I could not perform a clause-by-clause review of Codex’s document. The recommendations below are based directly on the current `phase-3-implementation` branch.

## 1. Adopt a General “Decision Context” Contract

I recommend creating:

```text
docs/specifications/OWNER_POLICY_DECISION_CONTEXT_STANDARD.md
```

Proof 34 should reference that standard and become its first complete implementation.

The UI must not independently determine which override wins. It should receive the answer and explanation from the same owner-policy service used by the worker. That preserves the requirement that a future UI may call the existing service but may not create a second authority model.

I would introduce a non-consuming service operation such as:

```python
OwnerPolicyService.explain(...)
```

or a separate service:

```python
OwnerPolicyDecisionContextService
```

The current `EffectiveOwnerPolicy` result contains the effective value, default, selected override ID, scope, actor, and reason. However, the underlying override record also contains priority, validity dates, maximum uses, consumed uses, risk acknowledgement, status, and supersession information that the decision UI needs.

The explanation operation should return:

```text
policy key
registered value type and validation
repository/application default
effective value
whether it is overridden
selected override
all matching scopes considered
why the selected override won
priority
activation and expiration
maximum uses
uses consumed
uses remaining
actor
reason
risk acknowledgement
superseded/revoked history
resolution time
context used for resolution
```

### Critical requirement

A UI explanation or preview must **never consume a bounded-use or single-use override**. Consumption should occur only when the acquisition worker applies that authority to an actual runtime decision.

The current runtime correctly uses `consume=True`; UI inspection should use an explicitly non-consuming path.

## 2. Keep Three Different Things Visibly Separate

The data contract and UI should always distinguish:

### External observation

```text
robots.txt says this path is disallowed
```

### Owner policy

```text
acquisition.robots.enforce resolves to false
because endpoint override 77 was selected
```

### Effective GNI decision

```text
GNI will proceed despite the observed restriction
```

An override must not rewrite the robots observation to “allowed.” The external fact remains visible and historically preserved. This follows the owner standard’s rule that GNI records both the external signal and the owner’s effective decision.

A good UI presentation would say:

```text
External robots decision
Disallowed

Default GNI behavior
Block acquisition until robots evidence is revalidated

Effective owner policy
Do not enforce robots restrictions

Selected scope
Endpoint 47

Effective GNI decision
Acquisition permitted

Important
The robots restriction remains recorded. Revoking or exhausting this
override may cause it to govern subsequent requests again.
```

## 3. Do Not Implement Robots Through the Existing Generic Hold Method Unchanged

This is the most important technical issue I found.

`AcquisitionRateLimitService.observe_hold()` currently iterates through every bucket attached to a reservation and writes the robots hold to each bucket. Those buckets can include:

```text
installation
adapter
platform
credential
origin
Source
endpoint
```

A robots denial is normally specific to a user agent and target path. Writing it to an installation or adapter bucket could delay unrelated endpoints across GNI. Writing it to an origin bucket could block allowed paths on the same site.

I recommend adding robots-specific persistence:

```text
acquisition_robots_snapshots
acquisition_robots_evaluations
```

### `acquisition_robots_snapshots`

One immutable retrieval and parsing result:

```text
origin
robots URL
HTTP status
retrieved time
revalidation time
ETag
Last-Modified
content hash
bounded raw-evidence reference
parser name and version
parse status
warnings
selected cache policy
```

### `acquisition_robots_evaluations`

One evaluation of a target request:

```text
snapshot ID
SourceEndpoint ID
IngestionRun ID
request identity
canonical target URL
target path
selected user agent
matched Allow or Disallow directive
matched pattern
directive line or normalized location
match specificity
crawl-delay observation
external decision
evaluated time
```

The existing `acquisition_rate_limit_observations` row can reference the robots evaluation rather than duplicating the complete evidence into every bucket.

The actual gate should be exact enough for the resource being evaluated:

```text
request path when available
endpoint for fixed feed endpoints
origin only for genuinely origin-wide conditions
```

## 4. Add Replace and Clear Semantics for Robots Holds

The current robots hold field is monotonic in the generic observation method—it can be extended, but there is no robots-specific reconciliation operation that clears or replaces it when a newly fetched file allows access.

Proof 34 should include an operation similar to:

```python
reconcile_robots_gate(
    previous_evaluation,
    current_evaluation,
    valid_until,
)
```

It must support:

```text
new disallow     → install or replace exact gate
changed disallow → replace exact gate
new allow        → clear exact robots gate
expired evidence → revalidate before relying on it
fetch failure    → apply registered unavailable policy
```

A previous robots restriction must not continue blocking because a stale `blocked_until` value survived after the underlying evidence changed.

## 5. Expand the Robots Policy Family

`acquisition.robots.enforce` is already registered and resolved by the worker. That should remain a boolean and should not be replaced with a large incompatible JSON object.

Proof 34 will introduce additional default decisions. Each one needs an owner-control disposition under the standard. I recommend evaluating at least:

```text
acquisition.robots.enforce
  boolean
  existing default: true

acquisition.robots.unavailable_action
  enum: delay | allow | deny
  recommended safe default: delay when no valid cached evidence exists

acquisition.robots.crawl_delay.enforce
  boolean
  only if GNI elects to support Crawl-delay

acquisition.robots.cache.max_age_seconds
  positive integer

acquisition.robots.cache.max_stale_seconds
  nonnegative integer

acquisition.robots.fetch_limits
  bounded JSON object for bytes, redirects, and timeout
```

For every key, document the fields already required by the owner standard:

```text
value type and validation
default
supported scopes
resolution point
restart requirement
external consequences
audit evidence
default-path test
override-path test
```

The lockout inventory already identifies robots retrieval and parsing as the next missing integration.

## 6. Use a Detail View, Not More Columns in the Health Table

The current Acquisition Health table is already dense. It displays lifecycle, verification, health, gate state, evidence counts, activity, and cutover controls. Its service only derives a broad gate label from the latest run; it does not expose the evidence and authority chain necessary for an override decision.

I recommend adding only a compact summary to each row:

```text
Robots: Allowed / Disallowed / Unavailable / Stale / Not checked
Effective enforcement: On / Owner override
Next robots review
Review decision
```

“Review decision” should open a dedicated endpoint detail page containing:

1. **Current effective decision**
2. **External robots evidence**
3. **Policy-resolution chain**
4. **Current gates and next eligibility**
5. **Scope and impact preview**
6. **Override history**
7. **Available owner actions**

A dedicated page will also work better on mobile than a large modal or an expanded table row.

## 7. Register the UI Components

The component registry currently ends with `CMP-0009`.

I recommend registering:

```text
CMP-0010 — Owner Policy Decision Context
CMP-0011 — Owner Override Impact Preview
CMP-0012 — Owner Override Confirmation
```

The implementation should also produce:

```text
a UX decision record
a component registry record
a reusable acceptance record
a proof-34-specific acceptance result
```

All dates and times displayed in this view should use the governed GNI date/time component rather than raw database or ISO representations.

## 8. Build Read-Only UI First

I would **not enable browser-based owner override creation under the current web mutation pattern yet**.

The current Acquisition Health routes accept `actor` directly from a submitted form. The application setup shown on the branch does not install an authentication or owner-capability middleware, and the route has no owner authorization or reauthentication dependency.

For now:

```text
UI
  inspect evidence
  explain effective policy
  preview consequences
  show exact CLI command needed

CLI
  create, supersede, or revoke owner authority
```

When UI mutations are enabled, they should require:

```text
server-derived owner identity
CSRF protection
owner-capability authorization
reason
risk acknowledgement
scope confirmation
expiration or use-limit confirmation
transactional re-evaluation
stale-preview rejection
```

The actor must eventually come from authenticated server context, not an editable text field.

## 9. Add a Hypothetical Impact Preview

Before an override is submitted, GNI should evaluate it without saving it:

```python
preview_override(
    policy_key,
    proposed_value,
    proposed_scope,
    proposed_scope_identity,
    context,
)
```

The result should show:

```text
current effective decision
proposed effective decision
scope precedence
currently affected endpoints
currently affected gates
next scheduled attempts affected
whether an existing override would be superseded
whether a more specific override would still win
expiration/use behavior
external consequences
```

The preview should carry a basis identifier, such as the current winning override public ID and a resolution fingerprint. The mutation should reject the submission if the authority state changed after preview.

That prevents the owner from approving one displayed result while a different override configuration is actually committed.

## 10. Proof 34 Should Directly Prove These Cases

At minimum:

```text
Robots allows the path under default enforcement.

Robots disallows the path and the exact endpoint is delayed.

A robots denial for one path does not block another allowed path.

A robots denial for one endpoint does not contaminate installation,
adapter, Source, or unrelated origin activity.

An endpoint override of false permits acquisition while preserving
the external robots evidence.

A request-scope override defeats an endpoint-scope value.

An endpoint-scope value defeats Source, origin, adapter, and global values.

Priority resolves equal-scope matches.

An expired override does not apply.

A revoked override does not apply.

A one-use override is consumed only by an actual runtime decision.

Viewing or previewing a one-use override does not consume it.

A changed robots file clears or replaces the prior gate.

Unavailable or malformed robots evidence follows the registered
unavailable-action policy.

The runtime observation records the robots evaluation and selected
owner authority.

Revoking an override causes still-valid robots evidence to govern again.

The UI displays the same effective value that the worker resolves.

A stale UI preview cannot create an override without re-evaluation.
```

## Recommended Implementation Order

1. Add the cross-policy decision-context specification.
2. Define the non-consuming explanation and hypothetical-preview DTOs.
3. Add robots snapshot and evaluation persistence.
4. Implement bounded robots retrieval, caching, parsing, and revalidation.
5. Implement exact-path evaluation and exact gate reconciliation.
6. Connect `acquisition.robots.enforce` and the new robots policy keys.
7. Add proof-34 runtime and migration tests.
8. Add the read-only Acquisition Health decision page.
9. Register and review the new UI components.
10. Add UI mutation only after owner authorization and CSRF protection exist.

## Bottom Line

**Codex is correct that this is the appropriate time to incorporate the additional decision information.** Proof 34 is where external robots evidence, owner policy resolution, durable gates, and UI explanation first need to operate together.

My approval would be conditional on these architectural rules:

* One owner-authority ledger.
* One server-side precedence implementation.
* Non-consuming UI explanations.
* External facts preserved separately from owner decisions.
* Exact robots path/evaluation scope.
* No use of the existing all-bucket robots hold behavior unchanged.
* Read-only UI before browser-based override mutation.
* Proof that the UI and worker resolve the same effective decision.

That produces infrastructure that can later explain Retry-After, provider limits, archive limits, scanner behavior, retention decisions, network authorization, and the remaining owner-control families without redesigning the UI for every policy.

