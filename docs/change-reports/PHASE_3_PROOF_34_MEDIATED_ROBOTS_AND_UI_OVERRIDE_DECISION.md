# Phase 3 Proof 34 Mediated Robots Workflow and Owner Authority Confirmation

**Approver:** GNI Owner<br>
**Approval date:** 08-24-2026<br>
**Authority:** Existing Owner authority confirmed; workflow approved<br>
**Scope:** Publisher URL entry, intermediary robots retrieval and evaluation, Owner-visible status, and exact browser override workflow<br>
**Implementation status:** Existing authority confirmed; workflow implementation and acceptance evidence pending

## Owner Authority

This record does not grant the Owner new override or access authority. The
Owner already has final authority under
`../specifications/OWNER_AUTHORITY_AND_CONFIGURATION_STANDARD.md` and
`../specifications/OWNER_CONFIGURATION_LOCKOUT_INVENTORY.md`.

The GUI described here is one interface to the existing PostgreSQL-backed
Owner-policy authority. Missing or incomplete GUI controls are implementation
gaps; they do not make a policy unavailable, non-bypassable, permanently
read-only, or outside Owner control. Operational, script, database, and future
authorized interfaces remain valid authority surfaces as defined by the
governing Owner documents.

Authentication, confirmation, evidence, and audit controls protect correct
application and attribution of Owner decisions. They do not outrank, grant,
or narrow Owner authority.

## Approved Workflow

The GNI Owner approves this workflow for mediated publisher acquisition:

1. The Owner supplies publisher URL targets through the GNI GUI.
2. Before fetching publisher content, the intermediary retrieves the exact
   publisher origin's `robots.txt` and evaluates the supplied target URL.
3. If the external result is `disallowed`, GNI displays a red badge labeled
   `Disallows` relative to that publisher.
4. An `Override` button appears next to the `Disallows` badge. The authenticated
   Owner may use it to authorize the intermediary to attempt the publisher
   fetch despite the retained external finding.
5. When the override becomes effective, the badge turns green but retains the
   text `Disallows`, preserving the original external finding. The interface
   also exposes an accessible, non-color-only `Owner override active` state.
6. If the external result is `allowed`, GNI displays a green badge labeled
   `Allows` relative to that publisher.

## Meaning of Override

An override changes GNI's effective enforcement decision. It does not rewrite
the intermediary's external `disallowed` evaluation.

The override authorizes a publisher fetch attempt; it cannot force an external
publisher or network to return content. Other GNI runtime policies and gates
are resolved independently through Owner-controlled policy authority. This
robots override does not silently change those separate policies, and their
independence does not place them outside Owner control.

## Intermediary Evidence Contract

For every robots retrieval and evaluation, the intermediary must return a
bounded, versioned evidence result that GNI can validate and persist. It must
identify at least:

```text
publisher identity
Owner-supplied target URL and canonical target URL
canonical publisher origin and robots URL
retrieval identity, state, time, HTTP status, validators, and bounded digest
parser name, version, approved artifact provenance, and parse state
selected user agent
matched group, directive, pattern, and location when available
external decision: allowed | disallowed | unavailable
Crawl-delay observation when present
warnings and unavailable reason when applicable
```

The result must be bound to the exact intermediary request and target fetch.
Missing, malformed, stale, mismatched, untrusted, or unregistered evidence is
classified as `unavailable`; GNI then applies the Owner-controlled
`acquisition.robots.unavailable_action` value (`delay`, `allow`, or `deny`). An
intermediary may not rewrite an unavailable observation into `allowed` or
`disallowed` without persistable exact evidence.

The intermediary must use the Owner-approved parser distribution and fetch
limits or a GNI-controlled component using those exact approved controls. The
implementation must prove this boundary for RSSHub, RSS-Bridge,
changedetection, and Playwright paths.

## UI and Authority Contract

The `Override` action uses the shared PostgreSQL Owner-policy ledger and the
same registered policy definition, validation, precedence, explanation, and
decision-context services as worker, CLI, and API paths. It is not a separate
UI-owned authority store.

Before mutation, the GUI must show the external `Disallows` finding, proposed
effective behavior, Owner-selected supported scope, consequences, and current
basis. The GUI must not silently narrow the scope family established by the
Owner-policy standard. Browser mutation implements:

```text
server-derived authenticated Owner identity
Owner-capability authorization
CSRF protection
reauthentication and explicit confirmation
reason and risk acknowledgement
exact scope confirmation
transactional re-resolution and stale-preview rejection
append-only override audit
```

Loading or reviewing the GUI must not create or consume an override. Bounded
or one-use authority is consumed only if it wins resolution and is actually
applied to a publisher-fetch authorization decision.

Revocation, expiration, exhaustion, supersession, or changed robots evidence
must reconcile the exact gate and badge projection. If current evidence still
disallows and no override governs, the badge returns to red `Disallows` and the
intermediary is not authorized by that override.

## Accessibility and Presentation

Color supplements but does not replace text or machine-readable state:

| External finding | Effective enforcement | Badge | Additional state/action |
| --- | --- | --- | --- |
| `allowed` | Fetch permitted | Green `Allows` | Review details |
| `disallowed` | Enforced | Red `Disallows` | `Override` button |
| `disallowed` | Owner override governs | Green `Disallows` | `Owner override active`; review/revoke controls as authorized |

The badge must expose external finding and effective enforcement separately to
assistive technology. The green `Disallows` state must not be represented as
an external `allowed` result.

## Supersession and Completion Boundary

This workflow resolves the mediated-adapter architecture blocker in the Proof
34 restart review. It applies existing Owner override and access authority to
the Proof 34 GUI and supersedes language that treated read-only browser state
as an Owner authority restriction. Browser implementation must still preserve
the shared ledger, exact Owner decision, evidence separation, audit,
transaction, accessibility, and UI-governance requirements.

This approval does not claim that the intermediary evidence contract, GUI,
override runtime, persistence, tests, or Proof 34 acceptance are complete.
