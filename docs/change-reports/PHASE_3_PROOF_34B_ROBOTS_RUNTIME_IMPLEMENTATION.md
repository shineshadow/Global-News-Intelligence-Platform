# Phase 3 Proof 34B Robots Runtime Implementation

**Date:** 08-25-2026  
**Status:** IMPLEMENTED CANDIDATE — OWNER REVIEW PENDING  
**Scope:** Backend runtime only; no browser mutation or Proof 34 UI

## Outcome

Proof 34B implements robots retrieval and enforcement in the shared Phase 3
acquisition worker. Publisher robots authorization now occurs before generic
rate reservation and before the adapter can retrieve the target resource.

The runtime preserves four separate facts:

```text
publisher robots evidence
exact external evaluation
effective Owner policy
effective GNI authorization and exact gate
```

An Owner `acquisition.robots.enforce=false` decision permits an attempt without
rewriting the retained external `disallowed` evaluation.

## Guarded And Bounded Retrieval

`GuardedRobotsFetcher` reuses the shared outbound egress guard. Robots requests:

- accept only canonical HTTP(S) publisher targets;
- derive the exact publisher origin and `/robots.txt` URL;
- reject URL credentials;
- send no endpoint or target-resource credentials;
- validate DNS, resolved addresses, redirects, TLS, and connected peer;
- strip declared credentials across origins;
- apply the effective Owner-selected response-byte, redirect, connect-timeout,
  and read-timeout limits; and
- retain bounded redacted retrieval provenance.

Outbound failures now carry stable internal reason codes where the shared
boundary can distinguish DNS failure, redirect-destination rejection,
redirect-limit exhaustion, read/total timeout, and oversized response.
Proof 34 maps those failures into the Owner-approved unavailable taxonomy
without persisting raw exceptions.

## Pinned Parsing And Trace Evidence

The runtime dependency is pinned to `protego==0.6.2`. The parser adapter records
and validates:

```text
parser_name: protego
parser_version: 0.6.2
source_commit: efe5039d39ee51f117acd0b01ffd8109ae265c22
wheel_sha256: 714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff
```

The downloaded wheel was independently hashed and then verified through
`scripts/verify_protego_wheel.py`. Cached normalized directives are digested
and reparsed through the same pinned adapter; mismatched parser provenance or
normalized evidence becomes `evidence_untrusted` rather than an inferred
allow/disallow.

The evaluation persists selected user agent, matched group, directive,
pattern, match specificity, Crawl-delay, parser/direction digest linkage, and
the exact canonical target. Protego does not expose original source-line
locations, so `matched_line_or_location` remains null rather than invented.

## Cache And Revalidation

The runtime applies the registered Owner cache policies on every real robots
authorization. It supports:

- fresh snapshot reuse without a network request;
- scope-sensitive effective freshness and staleness limits;
- conditional `If-None-Match` and `If-Modified-Since` revalidation;
- immutable 304 snapshots linked to the earlier usable snapshot;
- bounded prior-stale references when revalidation is unavailable; and
- refusal to treat expired evidence as current.

Empty, non-directive, parser-failed, retrieval-failed, and untrusted evidence
produce structured `unavailable` evidence. HTTP 404/410 remains specifically
`http_not_found`; other registered failure classes retain their phase,
retryability, sanitized Owner summary, and HTTP status when applicable.

## Exact Evaluation And Gate Reconciliation

`RobotsRuntimeService` locks the exact endpoint decision boundary and persists
one immutable evaluation for the exact target, request identity, and selected
user agent. It reconciles only the corresponding exact robots gate:

```text
allowed                         clear prior exact gate
disallowed + enforce=true       install/replace robots_denied
disallowed + enforce=false      permit and retain external disallow
unavailable + delay             install/replace robots_unavailable
unavailable + allow             permit and clear governing exact gate
unavailable + deny              install/replace robots_unavailable
Crawl-delay                     install robots_delayed after an actual attempt
changed evidence or policy      clear/supersede/reinstall exact gate
```

The Phase 3 worker always passes `enforce_robots=false` into the legacy generic
rate reservation service. The old `robots_disallow_until` column is retained
for compatibility but has no Phase 3 robots authority and receives no new
Proof 34 observations. Exact denial therefore does not contaminate
installation, adapter, platform, credential, origin, or Source rate buckets.

## Owner Authority

All runtime choices resolve through the shared PostgreSQL Owner-policy service.
The implementation applies the complete registered scope context rather than
creating a Proof 34-only override store.

Bounded/one-use authority is deferred when a robots override permits the
target but an independent generic rate gate still denies it. The worker
consumes that authority only after robots permits, the independent reservation
also permits, and the policy basis is transactionally rechecked. Cache/fetch
authority is consumed when it actually governs robots evidence retrieval or
selection; Crawl-delay authority is consumed when it governs an actual
post-attempt delay.

Revocation or changed evidence is evaluated on the next exact runtime decision.
If current evidence still disallows and enforcement again controls, the exact
gate is reinstalled. The external observation is never changed by override,
revocation, exhaustion, or gate state.

## Direct And Mediated Target Binding

Native feed and direct-listing adapters use the endpoint publisher URL.
Changedetection and Playwright already bind their internal-service response to
the endpoint publisher URL and use that publisher URL for robots.

RSSHub and RSS-Bridge require a separate exact `publisher_target_url` beside
their installation-owned `internal_service_identity`. Migration
`a7c9e1f3b5d4` updates the closed adapter schema, refuses upgrade when retained
generated-feed configurations lack a reviewed target, and refuses lossy
downgrade while target configurations remain.

## Owner Operation Information

Proof 34B adds a bounded registered Owner-operation result backend subset for:

```text
acquisition.retrieve_robots
acquisition.evaluate_robots
acquisition.retrieve_resource
```

Registered outcomes, reason/detail-schema combinations, JSON safety, and a
64-KiB details bound are enforced in code. Retrieval, evaluation, and target
operation results are recorded in Phase 3 ingestion-run evidence with exact
snapshot/evaluation/gate references. Authoritative robots history remains in
immutable snapshots/evaluations and retained gate transitions.

This does not claim completion of the broader cross-domain append-only result
index or all projection methods in `OWNER_OPERATION_INFORMATION_MODEL.md`.
Those remain final Proof 34 acceptance work.

## Verification

```text
Proof 34B focused service tests                        67 passed
complete non-migration repository inventory           455 passed
migration suite                                        38 passed
Alembic head                                           a7c9e1f3b5d4
Alembic schema drift                                   none
Protego wheel verification                             exact approved SHA-256
Ruff / compileall / diff check                         passed on touched implementation slice
```

The 455-test non-migration inventory was executed in three storage-bounded
database shards containing 174, 147, and 134 tests respectively. Controlled
guarded responses prove the runtime branches; no live external publisher
request is claimed by 34B.

## Deliberate Exclusions And Next Sequence

34B does not add a login system, authenticated browser mutation, Override
button, badge, Admin UI, or final live acceptance proof.

The accepted sequence remains:

```text
34B    robots backend runtime
next   Site-Wide Authentication and Authority Foundation
34C    authenticated robots GUI and Owner Override
34D    end-to-end and live acceptance
```

Until authentication exists, no Proof 34 browser/API mutation endpoint is
introduced. Owner authority remains available through the existing shared
ledger and operational interfaces; missing UI does not narrow that authority.
