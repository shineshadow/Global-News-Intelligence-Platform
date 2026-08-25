# Phase 3 RSSHub and RSS-Bridge Adapters

Status: IMPLEMENTED CANDIDATE

Date: 08-03-2026

## Scope

This package adds exact RSSHub and RSS-Bridge generated-feed adapters to the
shared Phase 3 acquisition worker. Both adapters reuse the proven RSS/Atom
normalization path and mandatory Artifact boundary while narrowing outbound
authority to an installation-owned internal-service registration.

The package provides:

- `rsshub` version `1` and `rss_bridge` version `1` runtime adapters;
- exact `feed/rss|atom/feed_parser` compatibility declarations;
- terminal RSS and Atom identification and safe-parser capabilities;
- required `internal_service_identity` endpoint configuration;
- installation configuration through `ACQUISITION_INTERNAL_SERVICES`;
- exact adapter, scheme, hostname, port, address-network, TLS-policy, and
  purpose checks before connection; and
- lossless-only downgrade refusal after generated-feed configuration history
  exists.

## Installation-Owned Egress

An endpoint cannot introduce an internal address exception. The operator must
first register the service in the installation environment. The setting is a
JSON array with this shape:

```json
[
  {
    "identity": "local-rsshub",
    "adapter_slug": "rsshub",
    "scheme": "http",
    "hostname": "rsshub.gni.internal",
    "port": 1200,
    "address_networks": ["10.55.0.10/32"],
    "tls_policy": "plaintext_internal",
    "purpose": "local RSSHub acquisition"
  }
]
```

The endpoint configuration stores only the matching identity:

```json
{"internal_service_identity": "local-rsshub"}
```

Missing, malformed, mismatched, or endpoint-invented identities fail closed.
Public endpoint validation is unchanged.

## Retrieval and Artifact Boundary

Generated feed bytes follow the same ordered boundary as the native feed
adapter:

```text
installation-registered IP-pinned retrieval
bounded staging
Bubblewrap/seccomp inspection
mandatory ClamAV scan
exact RSS or Atom structural identification
safe feed parsing
accepted Artifact promotion or verified deletion
Document normalization through the shared feed path
```

Conditional `ETag` and `Last-Modified` requests, bounded redirects, response
limits, run provenance, durable leases, rate reservations, and idempotent
execution remain shared worker responsibilities.

## Migration and Activation Boundary

Revision `b7d9e1f3a5c2` registers both adapters and their exact capabilities. It
does not install RSSHub or RSS-Bridge, configure an internal service, create or
change a SourceEndpoint, bind a secret, add a rate policy, or activate a
generated feed.

Generated-feed endpoint activation remains a deliberate operator action after
the corresponding service is installed and its exact route is verified. No
fallback to a public or legacy path occurs if the registered internal service
is unavailable.

## Deliberate Exclusions

This package does not implement direct listing extraction,
changedetection.io, Playwright, route discovery, custom RSS-Bridge code,
automatic conversion of source-discovery candidates, or a live generated-feed
canary. Those remain separate reviewable work.

## Proof Results

The implemented candidate passed:

- 20 focused native/generated adapter, installation-registry, and migration
  tests;
- 15 migration-safety tests, including clean downgrade/re-upgrade and refusal
  after generated-feed configuration history exists;
- 376 non-migration repository regression tests;
- scoped Ruff, Python compilation, and whitespace checks;
- Alembic head `b7d9e1f3a5c2` with no schema drift; and
- the guarded `/var` inode gate, ending at 52% use below the 65% refusal
  threshold.
