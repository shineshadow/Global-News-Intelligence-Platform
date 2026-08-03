# Phase 3 Feed Adapter and Shared Acquisition Worker

Status: IMPLEMENTED CANDIDATE  
Date: 2026-08-03

## Scope

This package is the first production-shaped adapter implementation on the
frozen Phase 3 acquisition architecture. It adds:

- the exact `feed/rss/feed_parser` and `feed/atom/feed_parser` adapter runtime
- guarded conditional HTTP retrieval through the IP-pinned egress boundary
- a shared worker that composes the active adapter configuration, durable
  lease, secret resolution, hierarchical rate reservation, Artifact security,
  feed normalization, Document persistence, and authority finalization
- bounded RSS and Atom structural identification and exact safe parsing inside
  the credential-free Bubblewrap/seccomp inspection sandbox
- repository seed data for the versioned adapter, exact compatibility tuples,
  terminal Artifact capabilities, and structural media/extension evidence
- Celery dispatch routing with stable schedule-window/configuration identities

The migration deliberately creates **zero endpoint configurations**. Existing
RSS/Atom endpoints remain on the named legacy path until they are individually
audited and explicitly configured. This package therefore establishes a safe
cutover boundary without performing a bulk cutover.

## Request Order

For a configured endpoint, the shared worker executes this order:

```text
validate exact active endpoint/adapter configuration
acquire durable PostgreSQL lease and append IngestionRun
resolve only declared secret bindings
reserve every applicable durable rate bucket atomically
derive the adapter's exact terminal Artifact allowlist
prove scanner, pinned signatures, detector, and parser availability
perform guarded outbound retrieval
stage, identify, scan, parse, and either delete or promote the Artifact
normalize an accepted feed and persist Documents/versions
finalize the reservation and lease
```

Security preflight occurs before outbound retrieval. The Artifact runtime
repeats its infrastructure check at ingestion so a dependency disappearing
between preflight and staging still fails closed.

A `304 Not Modified` response performs no Artifact ingestion because it
contains no new payload, but mandatory infrastructure is still proven before
the conditional request.

## Exact Feed Identity

RSS and Atom are identified structurally; an XML declaration is not treated as
a format identity. Inspection is bounded by payload size, element count, XML
depth, and attribute count. DTD/entity declarations, NUL bytes, malformed XML,
unsupported encodings, HTML, and format mismatches are rejected.

An RSS endpoint allows only the terminal `rss` format. An Atom endpoint allows
only `atom`. Generic XML media types and `.xml` extensions are evidence, not
permission to cross the endpoint's exact format allowlist.

The accepted Artifact records structural detector evidence, scanner engine and
signature versions, exact parser provenance, adapter/configuration identity,
retrieval provenance, and content-addressed storage identity. Rejected bytes
are deleted and verified absent before rejection metadata is persisted.

## Dispatch and Cutover Contract

Celery sends one normalized schedule window with every scheduled batch. The
Phase 3 execution identity combines that window with the active configuration
version; manual execution uses the Celery task identifier as its explicit
idempotency key. Redis remains the fast endpoint claim while PostgreSQL is the
durable replay authority.

Dispatch behavior is intentionally asymmetric:

```text
no active Phase 3 endpoint configuration  -> explicit legacy RSS path
active Phase 3 endpoint configuration     -> Phase 3 shared worker only
configured runtime unavailable or invalid -> fail closed; never use legacy
```

Before configuring the first endpoint, the installation must set distinct,
non-nested `ARTIFACT_STAGING_ROOT` and `ARTIFACT_CANONICAL_ROOT` directories,
import the pinned signature release, and pass the inspection and egress
smokes. Configuration is an audited per-endpoint action; there is no migration
backfill or automatic fallback.

## Deliberate Exclusions

This candidate does not yet:

- activate or migrate any existing endpoint
- declare full legacy RSS parity or remove the legacy poller
- implement RSSHub, RSS-Bridge, listing, changedetection, browser, video,
  subtitle, email, API, or file-repository adapters
- implement archive/container-recursive inspection
- implement the expanded acquisition-health state machine or its UI
- complete the formal Phase 3 implementation freeze

Those remain separate reviewable packages. The first live cutover requires a
bounded endpoint cohort, evidence comparison, rollback proof, and successful
repository and operational gates.

## Proof Surface

Automated coverage includes:

- guarded feed retrieval, redirects/provenance, conditional requests, HTTP
  failure, and exact endpoint compatibility
- exact RSS/Atom sandbox detection and rejection of HTML, DTD/entity, malformed,
  and wrong-format payloads
- deletion-first structural acceptance with detector/parser provenance
- worker success, Artifact rejection, replay, rate delay, and infrastructure
  failure before retrieval
- stable Phase 3 dispatch identity, explicit legacy routing, and no downgrade
  after configuration
- exact migration seed, zero endpoint configuration, downgrade protection,
  Alembic head, and schema drift

The candidate must pass the complete repository gate and live operational
smokes before endpoint activation or freeze.
