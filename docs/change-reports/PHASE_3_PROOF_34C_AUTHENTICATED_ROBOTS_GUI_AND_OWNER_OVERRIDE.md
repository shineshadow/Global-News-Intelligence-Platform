# Phase 3 Proof 34C Authenticated Robots GUI And Owner Override

**Date:** 08-26-2026  
**Status:** IMPLEMENTED CANDIDATE — OWNER REVIEW PENDING  
**Scope:** Authenticated robots projection, Owner override/revocation workflow,
and immediate exact-gate reconciliation; Proof 34D remains pending

## Outcome

Proof 34C exposes the retained publisher-origin robots decision in Acquisition
Health without changing the authority model established by 34A and 34B.

The compact authenticated view now shows:

```text
allowed                         green Allows
disallowed + enforced           red Disallows and Owner Override
disallowed + Owner override     green Disallows and Owner override active
unavailable                     warning plus registered broad reason
expired prior evidence          Stale
no evaluation                   Not checked
```

The external `disallowed` evaluation never becomes `allowed`. Green
`Disallows` means only that the Owner's effective
`acquisition.robots.enforce=false` authority permits GNI to attempt the fetch.

## Information And Access

`RobotsGuiService` projects the same immutable snapshots, evaluations, exact
gates, and Owner-policy context used by the runtime. Viewing and preview use
non-consuming policy resolution.

Authenticated users receive the compact robots summary. Detailed operational
information is restricted to Owner/Admin capability and is explicitly labeled
internal and Owner information. The detail view includes:

- external finding and effective GNI decision;
- exact publisher target and origin;
- selected user agent and matched rule;
- retrieval, parser, snapshot, and evaluation provenance;
- registered unavailable phase, reason, HTTP status, retryability, sanitized
  Owner summary, and effective action;
- effective Owner-policy chain and basis fingerprint;
- current exact gate plus gate/evaluation/snapshot history; and
- applicable retained Owner override and event history.

## Owner Mutation Workflow

The adjacent Override action uses the existing registered Owner-policy ledger;
34C introduces no competing override store and removes no supported scope.
The review screen offers every scope applicable to the exact target context:
global, adapter, platform, credential, origin, Source, endpoint, and request.

Mutation requires all of the following:

- an authenticated principal with `owner.policy` capability;
- CSRF validation;
- passkey verification within the preceding five minutes;
- a non-empty Owner reason;
- confirmation of the retained external `Disallows` finding;
- confirmation of the exact selected scope;
- explicit risk acknowledgement; and
- transaction-time revalidation of both policy basis and exact robots evidence.

The evidence confirmation fingerprint binds endpoint, evaluation, snapshot,
external decision, freshness, policy basis, and selected scope. Changed or
expired evidence and changed policy context reject the mutation for a fresh
review. Server-derived authenticated identity is the audit actor.

Revocation has the same authentication, CSRF, reason, exact-override, policy,
and evidence protections.

## Exact Gate Reconciliation

Override and revocation reconcile the exact runtime gate in the same database
transaction as the Owner-policy mutation:

```text
activate enforce=false     clear the current exact robots_denied gate
revoke enforce=false       reinstall robots_denied for current retained disallow
```

Reconciliation refuses a superseded evaluation or expired snapshot. Generic
rate buckets remain outside Proof 34 robots authority.

## Verification

The focused 34C slice passes 28 tests covering the GUI projection, runtime,
authenticated web workflow, immediate gate clearing/restoration, retained
external disallow, unavailable and stale states, fresh passkey verification,
Owner capability enforcement, non-consuming preview, and stale confirmation
rejection.

The expanded authentication, worker, policy, robots, and web regression
selection passes 61 tests after the final evidence-binding and immediate-gate
changes. Proof 34D will run the complete repository, device/browser UI, and
live external-publisher acceptance sequence.

Targeted Ruff, compileall, and diff checks pass on the 34C slice.

## Deliberate Exclusions

This implementation does not declare final UI acceptance, production
deployment, or Proof 34 completion. Owner visual/device review and its
permanent UI acceptance record remain open. Live external publisher evidence,
complete repository acceptance, and final Proof 34 reconciliation remain
assigned to 34D.
