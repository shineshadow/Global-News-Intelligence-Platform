# Phase 3 Live Feed Canary and Parity Review

**Review date:** 2026-08-03

**Outcome:** PASS — LIVE RSS CANARY AND ROLLBACK PARITY PROVEN

**Canary endpoint:** `47` — CISA RSS

**Endpoint URL:** `https://www.cisa.gov/news.xml`

## Scope

This review covers the first operator-controlled live transition of one
eligible RSS endpoint from the legacy feed poller to the Phase 3 shared
acquisition worker. It reviews:

```text
bounded one-endpoint activation
mandatory runtime preflight
live retrieval and structural RSS inspection
Artifact acceptance and rejection evidence
Document preservation and duplicate prevention
manual and scheduled Phase 3 execution
live rollback to the legacy path
manual legacy execution after rollback
reactivation on a new configuration version
immutable cutover-event history
```

This is a parity decision for the exact
`feed/rss/feed_parser` CISA endpoint only. It does not establish production
approval, parity for every RSS or Atom feed, or readiness of any remaining
Phase 3 adapter type.

## Preconditions

The canary began only after the following gates passed:

```text
distinct Artifact staging and canonical roots          configured
Phase 3 feed cutover cohort limit                       1
repository-pinned signature release                     active
Bubblewrap/seccomp/ClamAV inspection smoke              passed
clean-payload acceptance and EICAR rejection            passed
outbound HTTPS/IP-pinning and loopback-refusal smoke     passed
migration safety tests                                  12 passed
non-migration repository regression tests              362 passed
Alembic database revision                         a4c2e8f0b6d1 (head)
Alembic schema drift                                     none
GNI API, PostgreSQL, and Redis health                    healthy
```

The installed systemd environment uses
`/etc/global-news-intelligence/gni.env`. The actual Artifact roots and their
contents remain installation state and are not repository content.

## Canary Selection

CISA RSS endpoint `47` was selected from the Acquisition Health eligible
cohort because it was:

- active and verified;
- healthy and current;
- an exact `feed/rss/feed_parser` tuple;
- an unauthenticated public HTTPS endpoint;
- returning HTTP `200`; and
- free of an acquisition gate or prior cutover state.

The activation actor was `shine`. The retained reason was:

> Phase 3 live-feed canary: validate RSS parity, Artifact evidence,
> scheduling, and rollback for CISA endpoint 47.

## Initial Phase 3 Proof

The first activation created configuration
`feed-parser-v1-cutover-0001`. Manual and scheduled Phase 3 polling then
showed:

```text
cutover path                                      phase3
adapter                                    feed_parser v1
proof state                                        passed
runtime storage                                configured
HTTP status                                           200
accepted Artifacts                                       1
Artifact rejections                                      0
Documents                                                15
health                                              healthy
temporary gate                                         none
```

Scheduled Phase 3 success was observed through 08/03 06:27 pm EDT. The
Document count remained 15 across repeated retrievals. The accepted Artifact
count remained one, consistent with content-addressed deduplication of the
observed payload.

The source did not send a `Content-Type` header. Feed parsing retained the
warning `no Content-type specified`, but exact structural RSS inspection,
malware scanning, Artifact acceptance, Document persistence, and endpoint
health all succeeded. The warning is therefore a non-blocking upstream-header
observation for this canary, not evidence of a bypass or failed inspection.

## Live Rollback Proof

The operator rolled the endpoint back with the retained reason:

> Phase 3 canary rollback proof after successful manual and scheduled
> acquisition.

Rollback produced the expected state:

```text
cutover path                                       legacy
active worker                          legacy feed poller
Phase 3 proof                              not applicable
accepted Artifacts                                       1
Artifact rejections                                      0
cutover events                                           2
Documents                                                15
last HTTP status                                        200
```

The Phase 3 configuration was retired rather than deleted. Artifact,
Document, run, and immutable cutover evidence remained intact. A manual
legacy poll succeeded at 08/03 06:41 pm EDT, and the Document count remained
15.

## Reactivation Proof

The operator reactivated the endpoint with the retained reason:

> Phase 3 canary reactivation after successful live rollback proof.

Reactivation created the expected new configuration version
`feed-parser-v1-cutover-0002`. A manual Phase 3 poll succeeded at
08/03 06:49 pm EDT. Final reviewed state was:

```text
cutover path                                      phase3
adapter                                    feed_parser v1
configuration                  feed-parser-v1-cutover-0002
proof state                                        passed
runtime storage                                configured
HTTP status                                           200
accepted Artifacts                                       1
Artifact rejections                                      0
cutover events                                           3
Documents                                                15
health                                              healthy
temporary gate                                         none
```

The three immutable events represent activation, rollback, and reactivation
in order. No Document loss, duplicate Document creation, security rejection,
or silent downgrade was observed.

## Decision

The exact RSS/feed-parser canary passes live acquisition, Artifact evidence,
Document parity, schedule behavior, rollback, and reactivation review.
Endpoint `47` may remain active on the Phase 3 path.

`PHASE3_FEED_CUTOVER_LIMIT=1` remains unchanged. Expanding the feed cohort is
a separate installation decision, and implementation of the remaining Phase
3 acquisition adapters remains the next main-track package.
