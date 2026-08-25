# Phase 3 Proof 34 Requirements and Compliance Matrix

## 1. Purpose and Authority

This document is the controlling pre-implementation requirements and compliance record for **Phase 3 Proof 34 — Robots Acquisition and Enforcement**.

It was produced from the complete restart review of the `phase-3-implementation` branch at repository commit:

`6355a32c4a9e322ddd726b93dc51baebd49a7888`

The corresponding recovery database/Alembic head is:

`a9c1e3f5b7d2`

This document exists to:

- Translate the governing Owner-authority specifications into explicit Proof 34 implementation requirements.
- Record the state of the repository before new Proof 34 implementation begins.
- Identify existing foundations that may be extended.
- Identify existing behavior that must not be reused unchanged.
- Identify missing implementation requirements.
- Identify decisions that require explicit Owner approval.
- Identify every Proof 34 runtime decision that must remain Owner-overridable.
- Define the evidence required to prove each requirement.
- Prevent removed or invalid Proof 34 implementation work from becoming an implicit design baseline.
- Provide durable requirement identifiers that can be referenced by implementation commits, tests, reviews, change reports, and final acceptance.

### Governing Authority

The following documents govern Proof 34 and take precedence over implementation convenience, historical code behavior, removed Proof 34 work, or assumptions derived from existing runtime behavior:

- `OWNER_AUTHORITY_AND_CONFIGURATION_STANDARD.md`
- `OWNER_CONFIGURATION_LOCKOUT_INVENTORY.md`
- `OWNER_OPERATION_INFORMATION_MODEL.md`
- `OWNER_POLICY_DECISION_CONTEXT_STANDARD.md`
- `ROBOTS_ACQUISITION_AND_ENFORCEMENT_STANDARD.md`
- Applicable Phase 3 acquisition, egress, credential, rate-authority, worker, migration, and UI-governance standards
- Approved UI governance records and Owner decisions applicable to the modified surfaces

The controlling principle is:

> **THE OWNER-AUTHORITY SPECIFICATIONS GOVERN THE CODE. THE CODE NEVER GOVERNS OR NARROWS THE OWNER-AUTHORITY SPECIFICATIONS.**

The removed Proof 34A/B/C implementation, invalid Proof 34D artifact, removed migration, and implementation choices contained within them are historical evidence only. They are not authoritative requirements, approved defaults, or a design baseline for the restarted implementation.

---

## 2. Proof 34 Acceptance Rule

Proof 34 is accepted only when every applicable requirement in this document has been resolved and supported by implementation evidence.

A requirement may reach final acceptance only when its applicable implementation, persistence, runtime, policy, UI, migration, and test obligations have been proven.

### Requirement Statuses

Each requirement uses one of the following states:

- **FOUNDATION PASS** — Existing repository behavior already satisfies the requirement and does not require substantive Proof 34 implementation.
- **FOUNDATION — EXTEND** — A valid existing foundation exists but must be extended to satisfy Proof 34.
- **REQUIRED** — The requirement governs the implementation and must remain true throughout Proof 34.
- **GAP** — Required capability is absent and must be implemented.
- **OPEN DESIGN** — The governing requirement exists but an implementation design decision remains unresolved.
- **OWNER APPROVAL REQUIRED** — Implementation cannot proceed on the affected decision until the Owner explicitly approves it.
- **ACCEPTANCE REQUIRED** — Implementation alone is insufficient; test, runtime, migration, UI, or other evidence must be produced.
- **IMPLEMENTED — TEST PENDING** — Code exists but acceptance evidence is incomplete.
- **IMPLEMENTED — VERIFIED** — Implementation and required evidence are complete.
- **PASS** — Final requirement acceptance has been established.

### Proof-Level Acceptance Conditions

Proof 34 must not be declared complete while any requirement remains in:

- `GAP`
- `OPEN DESIGN`
- `OWNER APPROVAL REQUIRED`
- `IMPLEMENTED — TEST PENDING`
- `ACCEPTANCE REQUIRED`

Any intentionally excluded requirement must have an explicit Owner-approved exclusion or governing exception record. Silence, implementation difficulty, existing code behavior, or test absence does not constitute an exception.

### Evidence Rule

Final acceptance must be traceable from requirement ID to evidence.

Evidence may include:

- source implementation
- migration
- database constraint
- registered policy definition
- automated test
- runtime proof
- UI acceptance record
- Owner approval
- governance decision
- change report
- exact persisted operation/evidence records

A generic statement such as “tests pass” is not sufficient when the requirement calls for a specific runtime, scope, authority, or reconciliation behavior.

---

## 3. Owner Decisions Required Before Implementation

The restart review identified **six concrete values plus two architectural
decisions that must not be invented during implementation**. The Owner's
08-24-2026 decision record approves all six concrete values, the parser
selection and provenance pin, the associated closed validation bounds, and the
version-one Crawl-delay enforcement default. The Owner's separate 08-24-2026
mediated robots and UI override decision resolves the final architecture
decision.

| Decision                                                                                   | Current authoritative state                                                                                                | Required before implementation                                          |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `acquisition.robots.cache.max_age_seconds` default                                         | `86400`; closed range `300..86400`; integer excluding boolean                                                              | **OWNER APPROVED — 08-24-2026**                                         |
| `acquisition.robots.cache.max_stale_seconds` default                                       | `604800`; closed range `0..2592000`; integer excluding boolean                                                             | **OWNER APPROVED — 08-24-2026**                                         |
| `fetch_limits.max_response_bytes` default                                                  | `524288`; closed range `524288..2097152`; integer excluding boolean                                                        | **OWNER APPROVED — 08-24-2026**                                         |
| `fetch_limits.max_redirects` default                                                       | `5`; closed range `5..10`; integer excluding boolean                                                                       | **OWNER APPROVED — 08-24-2026**                                         |
| `fetch_limits.connect_timeout_seconds` default                                             | `10`; closed range `1..30`; integer excluding boolean                                                                      | **OWNER APPROVED — 08-24-2026**                                         |
| `fetch_limits.read_timeout_seconds` default                                                | `30`; closed range `1..60`; integer excluding boolean                                                                      | **OWNER APPROVED — 08-24-2026**                                         |
| Robots parser + exact version/supply-chain pin                                             | `protego==0.6.2`; source `efe5039d39ee51f117acd0b01ffd8109ae265c22`; wheel SHA-256 `714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff` | **OWNER APPROVED — 08-24-2026 / VERIFICATION PENDING**                  |
| Mediated adapters — RSSHub/RSS-Bridge/changedetection/Playwright publisher-robots boundary | Owner supplies publisher URLs in GNI; intermediary retrieves and evaluates publisher robots before fetch and returns exact evidence; GNI persists evidence and applies Owner policy | **OWNER APPROVED — 08-24-2026 / IMPLEMENTATION PENDING**                |
| Unavailable-evidence information taxonomy and access contract                              | Closed v1 phase/reason/retryability/summary taxonomy; both internal and Owner information; future Admin UI presentation required | **OWNER APPROVED — 08-25-2026 / FOUNDATION IMPLEMENTED**                |

---

## 4. Owner-Controlled Robots Policy Matrix

These are the exact Proof 34 policy controls the governing standard requires:

| Policy                                       | Value                                   | Required scopes                                                          | Resolution point                                        |
| -------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------- |
| `acquisition.robots.enforce`                 | boolean; default `true`                 | global, adapter, platform, credential, origin, Source, endpoint, request | Before target acquisition                               |
| `acquisition.robots.unavailable_action`      | `delay / allow / deny`; default `delay` | global, adapter, platform, credential, origin, Source, endpoint, request | When trustworthy current robots evidence is unavailable |
| `acquisition.robots.crawl_delay.enforce`     | boolean; approved v1 default `true`     | global, adapter, platform, credential, origin, Source, endpoint, request | Scheduling after robots evaluation                      |
| `acquisition.robots.cache.max_age_seconds`   | bounded positive integer                | global, adapter, platform, credential, origin, Source, endpoint, request | Calculating `fresh_until`                               |
| `acquisition.robots.cache.max_stale_seconds` | bounded nonnegative integer              | global, adapter, platform, credential, origin, Source, endpoint, request | Calculating `stale_until`                               |
| `acquisition.robots.fetch_limits`            | closed versioned object                 | global, adapter, platform, credential, origin, Source, endpoint, request | Before robots retrieval                                 |

The exact approved defaults and validation bounds are authoritative in
`../change-reports/PHASE_3_PROOF_34_OWNER_APPROVAL_DECISIONS.md`. All numeric
values reject booleans. The version-one fetch-limits object rejects missing or
unknown fields. Scoped values may be more conservative than the defaults and
may not exceed installation-owned egress hard limits.

---

## 5. Requirements And Compliance Matrix

|  # | Area                  | Governing requirement                                                                                                                                                                                              | Baseline at `6355a32c…`                                                                                                                                                    | Proof 34 requirement / acceptance proof                                                                                                                                                                                                                                                 | Status                                                  |
|:- | --------- | -------------------------------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| R34-001 | Recovery              | Work only from reset commit; do not reuse removed 34A/B/C or invalid 34D artifact.                                                                                                                                 | Correct branch/commit verified. Removed implementation absent from tree.                                                                                                   | New implementation must be designed from governing standards, not reconstructed from removed commits.                                                                                                                                                                                   | **PASS / FOUNDATION**                                   |
| R34-002 | Recovery              | DB implementation must begin from Alembic `a9c1e3f5b7d2`; no additional rollback.                                                                                                                                  | Repository migration head corresponding to restart is `a9c1e3f5b7d2`; no robots migration exists in reset tree.                                                            | New Proof 34 migration revises `a9c1e3f5b7d2`. Runtime DB head must be reverified before applying it.                                                                                                                                                                                   | **PASS / FOUNDATION**                                   |
| R34-003 | Owner authority       | Owner authority governs code. Runtime defaults/limits cannot become permanent restrictions merely because code contains them.                                                                                      | Owner-authority standard is present and governing. Existing older Phase 3 code still contains fixed implementation defaults.                                               | Every Proof 34 runtime policy/default must be registered and Owner-overridable unless the Owner approved that exact restriction as invariant.                                                                                                                                           | **MANDATORY**                                           |
| R34-004 | Lockouts              | Do not invent non-bypassable acquisition/security limits outside approved permanent invariants.                                                                                                                    | Lockout inventory identifies multiple acquisition/egress/parser limits as pending policy wiring rather than Owner lockouts.                                                | Proof 34 must not turn cache, fetch, parser, timeout, retry, redirect, or similar choices into hidden permanent restrictions.                                                                                                                                                           | **MANDATORY**                                           |
| R34-005 | Policy authority      | One PostgreSQL Owner-policy ledger.                                                                                                                                                                                | `owner_policy_overrides` and append-only override events already exist.                                                                                                    | Retain this ledger; do not create a robots-specific competing policy store.                                                                                                                                                                                                             | **PASS / FOUNDATION**                                   |
| R34-006 | Policy precedence     | One precedence implementation shared by worker, CLI, API and UI: request → endpoint → Source → origin → credential → platform → adapter → global → repository default.                                             | Current `OwnerPolicyService` already implements a foundation of this precedence.                                                                                           | Registry, explanation, preview and workers must all use the same service/ordering.                                                                                                                                                                                                      | **FOUNDATION — EXTEND**                                 |
| R34-007 | Policy registration   | Every Owner-controllable key requires a registered definition, type, validation schema, default, scopes, resolution point, restart requirement, consequences, evidence and tests.                                  | No complete registered-definition catalog exists. Current service accepts policy key/value/default from callers.                                                           | Authoritative registry added for every current ledger key; arbitrary keys and caller-default mismatches fail; robots definitions preserve all eight Owner scopes.                                                                                                                        | **IMPLEMENTED / FOCUSED TEST PASS**                     |
| R34-008 | Policy service        | `resolve(...)` must provide actual runtime value.                                                                                                                                                                  | Exists as foundation.                                                                                                                                                      | Runtime resolution now derives from registered definitions while retaining one precedence implementation.                                                                                                                                                                               | **IMPLEMENTED / FOCUSED TEST PASS**                     |
| R34-009 | Policy service        | `explain(...)` must expose the complete decision without consuming authority.                                                                                                                                      | Not implemented.                                                                                                                                                           | Non-consuming explanation DTO/service and bounded-use non-consumption test added; API/UI consumers remain pending.                                                                                                                                                                      | **SERVICE IMPLEMENTED / CONSUMERS PENDING**             |
| R34-010 | Policy service        | `preview_override(...)` must evaluate hypothetical authority without persistence/consumption.                                                                                                                      | Not implemented.                                                                                                                                                           | Non-persisting current/proposed preview, winning/rejected scope, authority chain and consequences added; affected live subjects/gates/operations remain empty until those consumers exist.                                                                                                | **FOUNDATION IMPLEMENTED / EXTEND**                     |
| R34-011 | Stale preview         | Preview requires deterministic `basis_fingerprint`; mutation must transactionally reject stale basis.                                                                                                              | Not implemented.                                                                                                                                                           | Deterministic basis fingerprint, policy-key transaction lock and stable `owner_policy.preview_stale` rejection implemented and tested.                                                                                                                                                   | **IMPLEMENTED / FOCUSED TEST PASS**                     |
| R34-012 | Bounded authority     | One-use/bounded authority is consumed only when selected **and actually applied** at the governed runtime decision.                                                                                                | Current service can consume; worker currently resolves robots enforcement early with `consume=False`.                                                                      | Consumption must occur atomically at actual robots authorization/gate decision, never merely because policy was inspected/resolved early.                                                                                                                                               | **GAP / TRANSACTIONAL CHANGE**                          |
| R34-013 | Robots policies       | `acquisition.robots.enforce` registered boolean default `true`.                                                                                                                                                    | Existing foundation/default `true`; worker resolves it.                                                                                                                    | Full definition and complete scope family registered; existing worker resolution remains a foundation pending exact evidence/gate integration.                                                                                                                                          | **REGISTRATION PASS / RUNTIME EXTEND**                  |
| R34-014 | Robots policies       | `acquisition.robots.unavailable_action` enum `delay/allow/deny`, default `delay`.                                                                                                                                  | Absent.                                                                                                                                                                    | Full enum/default/scope definition is registered and all three Owner choices are tested; unavailable-evidence runtime decision point remains pending.                                                                                                                                    | **REGISTRATION PASS / RUNTIME PENDING**                 |
| R34-015 | Robots policies       | `acquisition.robots.crawl_delay.enforce` default `true` **if the selected registered parser supports Crawl-delay**.                                                                                                | Owner approved default `true` with `protego==0.6.2`; runtime registration and capability proof are absent.                                                                 | Approved default is registered and validated; parser capability/runtime separation proof remains pending.                                                                                                                                                                                | **REGISTRATION PASS / RUNTIME PENDING**                 |
| R34-016 | Robots policies       | `acquisition.robots.cache.max_age_seconds`.                                                                                                                                                                        | Owner approved default `86400` and closed integer range `300..86400`; policy registration is absent.                                                                       | Approved default, closed bounds, boolean rejection and complete scope family are registered and focused-tested.                                                                                                                                                                          | **IMPLEMENTED / FOCUSED TEST PASS**                     |
| R34-017 | Robots policies       | `acquisition.robots.cache.max_stale_seconds`.                                                                                                                                                                      | Owner approved default `604800` and closed integer range `0..2592000`; policy registration is absent.                                                                       | Approved default, closed bounds, boolean rejection and complete scope family are registered and focused-tested.                                                                                                                                                                          | **IMPLEMENTED / FOCUSED TEST PASS**                     |
| R34-018 | Robots policies       | `acquisition.robots.fetch_limits` closed versioned object with response bytes, redirects, connect timeout and read timeout.                                                                                        | Owner approved all four defaults and closed ranges; policy registration is absent.                                                                                          | Exact closed object, approved bounds, missing/unknown/type rejection and complete scopes are tested; runtime installation-egress reconciliation remains pending.                                                                                                                         | **REGISTRATION PASS / RUNTIME PENDING**                 |
| R34-019 | Robots scope          | Retrieval is canonical-origin scoped; evaluation is exact target/user-agent/path scoped.                                                                                                                           | No robots retrieval/evaluation service exists.                                                                                                                             | Implement canonical `http/https` origin, `/robots.txt` URL, canonical target and normalized path. Do not broaden a path restriction to unrelated work.                                                                                                                                  | **GAP**                                                 |
| R34-020 | External evidence     | External robots observation, Owner policy, effective runtime decision and operation result must remain different facts.                                                                                            | Current system has no durable robots evidence.                                                                                                                             | A retained external `disallowed` evaluation must remain `disallowed` even when Owner policy permits acquisition.                                                                                                                                                                        | **GAP — CORE INVARIANT**                                |
| R34-021 | Persistence           | Authoritative immutable robots snapshots.                                                                                                                                                                          | No `acquisition_robots_snapshots` table/model.                                                                                                                             | Constrained snapshot model/table, retrieval/cache/parser provenance fields and database immutability trigger added and tested.                                                                                                                                                           | **FOUNDATION IMPLEMENTED / TEST PASS**                  |
| R34-022 | Persistence           | Authoritative immutable exact robots evaluations.                                                                                                                                                                  | No `acquisition_robots_evaluations`.                                                                                                                                       | Exact snapshot + endpoint/request/user-agent/path/matched-rule evidence model/table and database immutability added and tested.                                                                                                                                                          | **FOUNDATION IMPLEMENTED / TEST PASS**                  |
| R34-023 | Persistence           | Exact robots gates.                                                                                                                                                                                                | No `acquisition_robots_gates`. Generic rate buckets contain `robots_disallow_until`.                                                                                       | Separate exact gate/history model/table with evaluation-scope triggers added and tested; runtime reconciliation remains pending.                                                                                                                                                         | **PERSISTENCE PASS / RUNTIME PENDING**                  |
| R34-024 | Retrieval             | Robots fetch must use guarded outbound boundary, bounded retrieval and redacted provenance.                                                                                                                        | Existing direct/feed adapters already use shared `GuardedHTTPClient`; robots does not.                                                                                     | Reuse shared outbound guard rather than create an independent unrestricted HTTP client.                                                                                                                                                                                                 | **FOUNDATION AVAILABLE / GAP**                          |
| R34-025 | Redirect/egress       | Redirect and egress controls remain effective during robots retrieval.                                                                                                                                             | Shared egress guard already validates URL/DNS/redirect/peer/TLS and strips sensitive cross-origin material.                                                                | Robots tests must prove effective fetch limits **and** egress guard coexist.                                                                                                                                                                                                            | **FOUNDATION AVAILABLE / TEST REQUIRED**                |
| R34-026 | Secrets               | Secret values must never enter decision context, robots evidence or OwnerOperationResult.                                                                                                                          | Secret service already separates stable reference IDs from ephemeral values.                                                                                               | Use only non-secret credential identities where policy resolution requires them; reject secret-bearing details.                                                                                                                                                                         | **FOUNDATION AVAILABLE / INTEGRATE**                    |
| R34-027 | Cache                 | Fresh/stale windows and conditional ETag/Last-Modified revalidation.                                                                                                                                               | Existing feed adapters demonstrate conditional HTTP behavior; no robots cache.                                                                                             | Implement registered freshness/staleness calculation, conditional fetch, and exact 304 linkage to previous parsed evidence.                                                                                                                                                             | **GAP**                                                 |
| R34-028 | Cache                 | Expired evidence cannot silently remain current.                                                                                                                                                                   | No robots evidence lifecycle.                                                                                                                                              | Expired evidence must revalidate or follow unavailable policy; stale/current state must be explicit.                                                                                                                                                                                    | **GAP**                                                 |
| R34-029 | Parser                | Parser must be deliberately selected, pinned/versioned and have decision-trace provenance.                                                                                                                         | Owner approved `protego==0.6.2`, source commit `efe5039d39ee51f117acd0b01ffd8109ae265c22`, and wheel SHA-256 `714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff`. | Pin and hash-verify the approved distribution; implement trace provenance and fail unavailable when parser/trace results cannot be reconciled.                                                                                                                                           | **OWNER APPROVED / IMPLEMENTATION AND VERIFICATION GAP** |
| R34-030 | Crawl-delay           | Valid observed Crawl-delay may govern scheduling; malformed Crawl-delay must not corrupt otherwise valid Allow/Disallow evidence.                                                                                  | Parser and default are Owner-approved; capability integration and runtime behavior are not implemented.                                                                    | Verify approved parser capability and combine effective delay with other independent eligibility controls.                                                                                                                                                                               | **IMPLEMENTATION AND VERIFICATION GAP**                 |
| R34-031 | Allowed result        | External robots allows exact target.                                                                                                                                                                               | No exact evaluation.                                                                                                                                                       | Permit request regardless of `robots.enforce`; clear obsolete exact robots gate.                                                                                                                                                                                                        | **GAP**                                                 |
| R34-032 | Disallowed + enforce  | External disallow + effective enforce `true`.                                                                                                                                                                      | Existing generic bucket approach does not represent exact evidence.                                                                                                        | Block/delay exact acquisition and install/replace exact robots gate.                                                                                                                                                                                                                    | **GAP**                                                 |
| R34-033 | Disallowed + override | External disallow + effective enforce `false`.                                                                                                                                                                     | Existing code only passes enforcement boolean into rate service.                                                                                                           | Permit exact request, retain external disallow, do not install governing robots restriction, emit `acquisition.robots_restriction_not_enforced`.                                                                                                                                        | **GAP**                                                 |
| R34-034 | Unavailable           | Trustworthy robots evidence unavailable.                                                                                                                                                                           | No explicit robots unavailable model.                                                                                                                                      | Closed phase/reason/retryability/summary information foundation is implemented. Runtime `delay` installs an exact unavailable gate; `allow` retains unavailable evidence; `deny` blocks as a GNI policy decision, not an external denial.                                                                                                               | **INFORMATION FOUNDATION PASS / RUNTIME GAP**           |
| R34-035 | Reconciliation        | Changed evidence must replace or clear previous gate; expired/revoked/exhausted overrides must re-evaluate current evidence.                                                                                       | Generic `robots_disallow_until` is monotonic-style bucket state and lacks exact reconciliation.                                                                            | Implement transactional `reconcile_robots_gate` equivalent including allow-clear, changed-disallow replace, unavailable action, expiration and override-removal behavior.                                                                                                               | **GAP**                                                 |
| R34-036 | Rate integration      | A robots denial must not contaminate installation, adapter, platform, credential, origin or Source rate buckets.                                                                                                   | **Current `observe_hold()` loops across reservation buckets and can write robots hold to all of them.**                                                                    | Proof 34 must **not use this path unchanged**. Exact robots authorization/gate must occur before target reservation or through an exact robots gate service.                                                                                                                            | **CURRENT BASELINE NONCONFORMING — REPLACE FOR ROBOTS** |
| R34-037 | Worker ordering       | Robots authorization must govern before target request reservation/retrieval.                                                                                                                                      | Worker currently resolves enforcement → reserves generic rate capacity → calls adapter.                                                                                    | Insert coherent robots evidence/evaluation/authorization before target acquisition; preserve independent rate/provider/Retry-After controls.                                                                                                                                            | **GAP / WORKER CHANGE**                                 |
| R34-038 | Transactions          | Snapshot selection, evaluation, policy resolution/consumption, gate reconciliation and target authorization must be coherent.                                                                                      | No combined robots transaction.                                                                                                                                            | Prevent conflicting exact gates, stale evidence authorization, older evaluation clearing newer gate, and one-use consumption without decision.                                                                                                                                          | **GAP**                                                 |
| R34-039 | Direct adapters       | Native feed and direct listing paths contact publisher through GNI guarded HTTP.                                                                                                                                   | Existing shared direct HTTP boundary is clear.                                                                                                                             | Direct publisher URL provides a clear Proof 34 robots target/origin. Integrate before adapter target fetch.                                                                                                                                                                             | **ARCHITECTURE CLEAR / GAP**                            |
| R34-040 | Mediated adapters     | Robots evidence must describe the exact publisher request.                                                                                                                                                         | Owner approved GUI-supplied publisher targets and intermediary retrieval/evaluation with a bounded exact evidence return contract.                                        | Implement target-bound evidence validation and persistence before GNI applies policy and authorizes RSSHub, RSS-Bridge, changedetection, or Playwright target fetches. Missing, stale, mismatched, or untrusted evidence follows unavailable policy.                                                                                                  | **ARCHITECTURE APPROVED / IMPLEMENTATION GAP**          |
| R34-041 | Production path       | Scheduled/manual Phase 3 acquisition must converge on same robots authority.                                                                                                                                       | Both converge through dispatch into `Phase3AcquisitionWorker`; legacy endpoints intentionally retain legacy poller.                                                        | Integrate once in shared Phase 3 worker composition and test every Phase 3 adapter path. Do not silently claim legacy polling as Proof 34 coverage.                                                                                                                                     | **FOUNDATION AVAILABLE / GAP**                          |
| R34-042 | OwnerOperationResult  | Common structured operation result service/DTO and registries.                                                                                                                                                     | Not implemented at reset.                                                                                                                                                  | Implement registered domain/operation/outcome/gate/reason/details vocabulary and server-generated messages. Proof 34 is first complete acceptance.                                                                                                                                      | **GAP**                                                 |
| R34-043 | OwnerOperationResult  | Required robots operation types.                                                                                                                                                                                   | Absent.                                                                                                                                                                    | Support at least `acquisition.retrieve_robots`, `acquisition.evaluate_robots`, and `acquisition.retrieve_resource`.                                                                                                                                                                     | **GAP**                                                 |
| R34-044 | OwnerOperationResult  | Required robot outcomes/reasons/versioned detail schemas.                                                                                                                                                          | Absent.                                                                                                                                                                    | Unavailable subreason registry and bounded Owner-summary foundation implemented; complete allowed/disallowed/stale/not-enforced OwnerOperationResult registry remains pending.                                                                                                           | **UNAVAILABLE FOUNDATION PASS / EXTEND**                |
| R34-045 | History               | Complete result/decision/evidence history append-only; “latest” is projection only.                                                                                                                                | Owner override history foundation exists; no robot operation/evidence history.                                                                                             | Retain snapshots/evaluations/gates/results/history sufficient to reconstruct decisions.                                                                                                                                                                                                 | **GAP**                                                 |
| R34-046 | Health read model     | UI/API cannot infer robots reason by combining unrelated run statuses, exceptions and timestamps.                                                                                                                  | Current Acquisition Health read model derives broad gate state heuristically from latest run/error.                                                                        | Robots health state must come from explicit server-side operation/evidence/policy projection.                                                                                                                                                                                           | **CURRENT ROBOTS UI PATTERN NONCONFORMING**             |
| R34-047 | Health UI             | Compact robots summary relative to the publisher.                                                                                                                                                                  | Not present.                                                                                                                                                               | Show green `Allows`; red `Disallows` plus `Override`; or green `Disallows` plus accessible `Owner override active`. Admin UI must also expose unavailable phase, reason/code, HTTP status, retryability, sanitized summary, evidence, action, and history. UI absence does not remove Owner access.                                                        | **OWNER DESIGN APPROVED / IMPLEMENTATION GAP**          |
| R34-048 | Detail UI             | Dedicated Owner review view.                                                                                                                                                                                       | Not present.                                                                                                                                                               | Show effective GNI decision, external evaluation, UA/matched rule, retrieval/parser provenance, policy chain, exact gate/eligibility, impact preview, override history and evidence history.                                                                                            | **GAP**                                                 |
| R34-049 | UI access             | The Proof 34 GUI must expose the Owner's existing robots override authority through the shared ledger; missing UI controls do not narrow Owner authority.                                                           | Current generic web app does not yet expose authenticated Owner policy mutation.                                                                                            | Implement the adjacent Override action with server-derived Owner identity, authorization, CSRF, reauthentication, reason/risk/scope confirmation, transactional re-resolution, stale-preview rejection, and append-only audit. Preserve every supported Owner scope and operational authority surface.                                              | **OWNER AUTHORITY CONFIRMED / UI IMPLEMENTATION GAP**   |
| R34-050 | CLI                   | CLI must use same registered policy service, validation and precedence.                                                                                                                                            | `scripts/owner_policy.py` exists, but current service allows arbitrary/unregistered keys/default behavior.                                                                 | Update CLI to use registered service; it must not become a validation bypass.                                                                                                                                                                                                           | **FOUNDATION — REFACTOR**                               |
| R34-051 | Date/time UI          | Time hidden by default; dates use American UI standard; current year omitted; time only when necessary and 12-hour.                                                                                                | Shared helper/governance foundation exists; current Acquisition Health has legacy display paths.                                                                           | All new/modified Proof 34 UI fields comply with UXD-0003 / American date-time standard.                                                                                                                                                                                                 | **GAP IN MODIFIED SURFACE**                             |
| R34-052 | UI governance         | Modified reusable Endpoint Health component must have governing component record/version/review.                                                                                                                   | CMP-0006 exists but is Experimental; CMP-0009 date-time component is Proposed.                                                                                             | Update/register relevant CMP contracts and ownership/version/state coverage.                                                                                                                                                                                                            | **GAP**                                                 |
| R34-053 | UI governance         | Materially changed workflow requires prototype/review and permanent acceptance evidence.                                                                                                                           | No Proof 34 UAR exists.                                                                                                                                                    | Produce UI review evidence and `UAR` for Proof 34 including mobile/adaptation/accessibility/date-time behavior.                                                                                                                                                                         | **GAP**                                                 |
| R34-054 | Migration             | Add strongly constrained robots persistence from current head.                                                                                                                                                     | No robots evidence/gate tables at reset. Recursive tree confirms absence.                                                                                                  | Migration `c2f4a6b8d0e1` revises `a9c1e3f5b7d2`; models/import metadata, cleanup fixture and head-sensitive tests updated coherently.                                                                                                                                                     | **IMPLEMENTED / MIGRATION TEST PASS**                   |
| R34-055 | Migration             | Historical robots evidence must not be silently destroyed by downgrade.                                                                                                                                            | Repository already uses lossless-only downgrade refusal for Owner-policy/archive history.                                                                                  | Empty round trip and retained-history downgrade refusal are database-tested.                                                                                                                                                                                                             | **IMPLEMENTED / MIGRATION TEST PASS**                   |
| R34-056 | Compatibility         | Legacy generic `robots_disallow_until` cannot survive as hidden authoritative robots state.                                                                                                                        | Column still exists in generic rate buckets and baseline tests verify it.                                                                                                  | Remove it from Proof 34 authority/reconciliation. Whether physical column removal is necessary requires migration design; do not invent that requirement.                                                                                                                               | **MANDATORY RUNTIME DEAUTHORIZATION**                   |
| R34-057 | Tests | Policy precedence/default/override/explain/preview/staleness/non-consumption. | Existing owner-policy tests cover foundation precedence, expiry/revoke/single-use, but not registry/explain/preview/fingerprint. | Registry, bounds, full scope family, exact authority chain, non-consumption, preview and stale-basis focused tests pass; cross-layer consumer parity remains pending. | **FOCUSED PASS / CROSS-LAYER PENDING** |
| R34-058 | Tests | Robots allow/deny/path isolation and no bucket contamination. | No Proof 34 robots tests at reset. | Add exact allow/disallow/path/origin/bucket-isolation tests. | **GAP** |
| R34-059 | Tests | Cache/revalidation/unavailable/Crawl-delay/parser/evidence tests. | None. | Unavailable registry/schema/immutability/downgrade tests are implemented in 34A.1; runtime must still prove 304 linkage, expired evidence, malformed/unreachable/stale handling, limits, provenance and Crawl-delay disposition. | **INFORMATION TEST PASS / RUNTIME GAP** |
| R34-060 | Tests | Overrides must preserve external observation, revoke correctly, and consume one-use only on actual operation. | Foundation policy tests only. | Add complete runtime tests with exact evidence/gate linkage. | **GAP** |
| R34-061 | Tests | UI and worker resolve the same external finding and effective decision; viewing must not mutate/consume. | No decision UI/service exists. | Prove intermediary target/evidence binding; allowed green `Allows`; enforced disallowed red `Disallows`; overridden disallowed green `Disallows` with `Owner override active`; secure Override mutation; and cross-layer parity without view-time consumption. | **GAP** |
| R34-062 | Tests | Stale UI preview must fail. | No preview. | Service-level basis change between preview and mutation is rejected and tested; UI wiring remains pending. | **SERVICE PASS / UI PENDING** |
| R34-063 | Tests | Secret headers/credentials absent from evidence. | Secret/egress foundations exist. | Explicit robots evidence and OwnerOperationResult redaction tests required. | **GAP** |
| R34-064 | Test runner | Focused tests and complete repository suite must pass using repository test convention. | `scripts/run-test-suite.sh` exists and separates migration/full suite with its test-safety guard. | 34A.1 focused tests pass 26/26; guarded suite passes 38 migration and 435 non-migration tests. Future Proof 34 runtime/UI tests remain acceptance work. | **CURRENT SUITE PASS / FUTURE TESTS PENDING** |
| R34-065 | Schema | Alembic current/check and schema drift zero. | No new migration yet. | Head `e5a7c9d1f3b2`, constraints, empty and retained-information downgrade, one head, and Alembic zero-drift check pass for the 34A.1 foundation. | **FOUNDATION SCHEMA PASS** |
| R34-066 | Live proof | Runtime proof must demonstrate allow, deny/delay, unavailable, Owner override and reconciliation. | Not performed; no implementation exists. | Use controlled/live evidence and record exact snapshot/evaluation/gate/policy/result identities. | **ACCEPTANCE REQUIRED** |
| R34-067 | Change report | Final report must record exact implementation evidence and remaining exclusions. | No valid Proof 34 implementation report at reset. | New report must be based only on new conforming implementation and test/runtime evidence. | **GAP** |
| R34-068 | Completion | Proof 34 cannot be declared complete until policy registration/default approval, DB, retrieval/cache/parser, evaluations/gates, Owner context/results, approved UI/Override workflow, tests, runtime proof and report are complete. | Governing standard explicitly says Proof 34 is incomplete at reset. | All rows above that are implementation/acceptance obligations must close. | **NOT COMPLETE** |
| R34-069 | Owner information access | Robots unavailable phase, reason, status, retryability, summary, evidence, and history are internal **and** Owner information. | No explicit dual-use/access guarantee or future Admin UI obligation at reset. | Persist the structured contract; keep operational Owner access; expose identical registered semantics in the future Admin UI; treat missing UI as a tracked gap, never as permission to hide or discard information. | **OWNER APPROVED / FOUNDATION IMPLEMENTED / UI PENDING** |

---

## 6. Cross-Cutting Implementation Controls

The requirements below apply across Proof 34 even where an individual matrix row does not repeat them.

### CONTROL-01 — No New Hidden Runtime Policy

If Proof 34 introduces any additional runtime:

- threshold
- timeout
- retry rule
- parser strictness decision
- fallback behavior
- cache rule
- scheduling limit
- response-size limit
- redirect limit
- safety limit
- enforcement decision

that decision must not silently become non-configurable.

Every such decision must satisfy at least one of the following:

1. It uses an already-approved Owner-policy authority.
2. It is registered as a new Owner-controlled policy with the required validation, scopes, default, resolution point, consequences, evidence, and tests.
3. It has an exact Owner-approved basis establishing that specific restriction as an invariant.

Existing code, library defaults, framework defaults, historical Proof 34 implementation choices, or developer preference are not sufficient authority for creating a permanent Owner lockout.

### CONTROL-02 — External Robots Evidence Remains Factual

Robots evidence records what the external publisher supplied and how that evidence applies to the exact evaluated request.

Owner policy must never rewrite that evidence.

For example:

`External evaluation: Disallowed`

may coexist with:

`Effective Owner policy: Do not enforce robots restriction`

and:

`Effective GNI decision: Acquisition permitted`

The external evaluation remains `Disallowed`.

### CONTROL-03 — Robots Authority Is Exact

A robots rule applying to one exact target path must not become an installation-wide, adapter-wide, platform-wide, credential-wide, Source-wide, or origin-wide restriction unless the external rule itself genuinely applies at that scope.

Proof 34 must not use the existing generic all-bucket robots hold mechanism unchanged.

### CONTROL-04 — Generic Rate State Is Not Robots Authority

The authoritative Proof 34 chain is:

`Robots Snapshot`

→ `Exact Robots Evaluation`

→ `Owner Policy Decision`

→ `Effective Runtime Decision`

→ `Exact Gate or Permit Action`

→ `OwnerOperationResult`

Generic acquisition-rate state may reference the relevant robots snapshot, evaluation, gate, or policy-decision identity.

It must not become the authoritative storage location for robots evidence or exact robots enforcement state.

### CONTROL-05 — Owner Authority Is Consumed Only by Real Runtime Use

Viewing a page, loading Acquisition Health, explaining a policy decision, validating a form, calculating eligibility, or previewing an override must not consume bounded or single-use Owner authority.

Authority may be consumed only when:

1. the override actually wins resolution;
2. the governed runtime decision point is reached;
3. the effective value is actually applied; and
4. the corresponding decision/result evidence is transactionally recorded.

### CONTROL-06 — One Decision Model Across All Interfaces

Worker, CLI, API, and UI must not independently calculate which Owner policy wins.

All interfaces must use the same Owner-policy authority, policy registry, precedence rules, validation behavior, and decision-context service.

### CONTROL-07 — Exact Browser Override Control for Proof 34

The initial Proof 34 browser interface may display:

- external robots evidence
- effective GNI decision
- effective Owner policy
- selected override
- matching policy chain
- explanation
- hypothetical preview
- exact gate
- next eligibility
- histories
- available Owner action
- exact validated CLI command where appropriate

The Proof 34 interface must expose the Owner's existing robots enforcement
authority through the publisher-relative Override described in
`../change-reports/PHASE_3_PROOF_34_MEDIATED_ROBOTS_AND_UI_OVERRIDE_DECISION.md`.
The GUI is an interface to the shared authority model, not the source or limit
of Owner authority. Any mutation control not yet present is an implementation
gap rather than an Owner lockout.

The action implements authentication, authorization, CSRF, reauthentication,
reason, risk acknowledgement, scope confirmation, stale-preview,
transactional, and append-only audit safeguards defined by the governing
Owner-policy standard. Loading, viewing, explaining, or previewing must not
mutate or consume authority.

### CONTROL-08 — Removed Proof 34 Work Has No Design Authority

The removed Proof 34A/B/C implementation and invalid Proof 34D artifact must not be used to establish:

- numeric defaults
- parser choice
- parser version
- fetch limits
- cache periods
- schema design
- enforcement semantics
- scope behavior
- UI behavior
- migration structure

A value or design appearing in removed implementation work may be adopted only when independently supported by current governing authority or newly approved by the Owner.

---

## 7. Pre-Implementation Review Disposition

### Review Result

**Pre-implementation repository review: COMPLETE**

The restart review found no basis for changing, weakening, or narrowing the governing Owner-authority or robots-enforcement standards.

### Principal Architecture Finding

Proof 34 must not be implemented as:

`robots parser + robots_disallow_until`

The existing generic robots-hold mechanism is unsuitable as the Proof 34 authority model because it can propagate an exact robots restriction into unrelated acquisition rate scopes.

The required architecture is:

`Durable External Robots Snapshot`

→ `Exact Target Evaluation`

→ `Owner Policy Decision`

→ `Effective Runtime Decision`

→ `Exact Gate / Permit Action`

→ `Structured OwnerOperationResult`

Generic rate-limit state may retain references to that authority chain but must not replace it.

### Existing Runtime Behavior That Must Not Be Reused Unchanged

The existing generic robots hold behavior must not be used unchanged because it can apply robots state across every rate bucket associated with a reservation.

This creates the possibility that one path-specific robots restriction could affect unrelated:

- installation activity
- adapters
- platforms
- credentials
- Sources
- endpoints
- paths on the same origin

Proof 34 requires exact robots evidence and exact gate reconciliation instead.

### Implementation Authorization State

**All eight restart decisions now have Owner approval. Implementation remains
subject to acceptance of this requirements review and the other restart-gate
controls.**

The repository review is complete. On 08-24-2026 the Owner approved:

1. `acquisition.robots.cache.max_age_seconds` default and bounds
2. `acquisition.robots.cache.max_stale_seconds` default and bounds
3. `fetch_limits.max_response_bytes` default and bounds
4. `fetch_limits.max_redirects` default and bounds
5. `fetch_limits.connect_timeout_seconds` default and bounds
6. `fetch_limits.read_timeout_seconds` default and bounds
7. The Protego parser distribution, exact version, source commit, and wheel hash
8. The mediated robots evidence and GUI Override architecture

The Owner additionally approved the version-one
`acquisition.robots.crawl_delay.enforce` default as `true`.

The Owner-approved mediated architecture requires GUI-supplied publisher
targets, intermediary retrieval and evaluation of publisher robots evidence,
and a target-bound evidence result that GNI validates and persists before
applying Owner policy and authorizing the publisher fetch.

### Restart Gate

Implementation begins only after:

- this requirements/compliance review is accepted;
- approved Owner defaults and validation bounds are implemented exactly;
- the parser selection/version and supply-chain pin are implemented and verified;
- the approved mediated-adapter evidence contract is reflected exactly in implementation planning;
- no new unresolved runtime restriction has been introduced during implementation planning.

---

## 8. Final Acceptance Summary

### Current State

**Proof 34 status: PRE-IMPLEMENTATION — NOT YET ELIGIBLE FOR FINAL ACCEPTANCE**

This section is intentionally established before implementation so final acceptance cannot be reconstructed informally after the fact.

### Final Acceptance Ledger

At completion, record:

- **Requirements reviewed:** 68
- **Requirements passed:** TBD
- **Owner-approved exclusions:** TBD
- **Unresolved requirements:** TBD
- **Failed requirements:** TBD

### Owner Decisions

- Required decisions identified: 8
- Approved: 9
- Unresolved: 0

### Verification

- Focused Proof 34 tests: TBD
- Migration tests: TBD
- Complete repository test suite: TBD
- Schema drift: TBD
- Runtime allow proof: TBD
- Runtime disallow/enforcement proof: TBD
- Runtime unavailable-evidence proof: TBD
- Runtime Owner-override proof: TBD
- Runtime gate-reconciliation proof: TBD
- UI/worker policy parity proof: TBD
- UI acceptance record: TBD
- Change report: TBD

### Final Acceptance Rule

Proof 34 may be marked **PASS** only when:

- every applicable `R34-*` requirement is `PASS`;
- all required Owner decisions are recorded;
- no unresolved requirement remains;
- no hidden robots authority remains in generic rate state;
- external evidence remains independently preserved;
- the Owner policy and runtime decision chain is reproducible;
- all required migration, focused, repository, runtime, and UI evidence has passed;
- the final Proof 34 change report identifies the exact evidence supporting completion.

### Final Disposition

**Current disposition:** NOT ACCEPTED — 34A AND 34A.1 FOUNDATIONS IMPLEMENTED; RUNTIME AND UI WORK REMAIN

**Final disposition:** TBD
