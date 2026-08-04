# Phase 3 changedetection.io and Playwright Fallback

**Status:** Implemented candidate  
**Date:** 2026-08-03  
**Migration:** `d3f5a7b9c1e4`

## Scope

This package adds two exact HTML listing adapters after the cheaper native,
generated-feed, and direct-HTTP paths:

| Adapter | Endpoint tuple | Role |
| --- | --- | --- |
| `changedetection` v1 | `website / html / web_scraper` | Consume an attested snapshot from a pre-provisioned watch |
| `playwright` v1 | `website / html / browser_automation` | Consume an attested render from a disposable browser service |

The repository does not embed a browser in Celery. Both acquisition services
are separately installed, installation-owned infrastructure reached through
the existing exact internal-service registry. This preserves worker-pool
isolation and avoids granting the application worker direct browser child
process, host-mount, download, or ambient-credential authority.

## Installation contract

Example `ACQUISITION_INTERNAL_SERVICES` registrations in `gni.env`:

```json
[
  {
    "identity": "local-changedetection",
    "adapter_slug": "changedetection",
    "scheme": "http",
    "hostname": "changedetection.gni.internal",
    "port": 5000,
    "address_networks": ["10.66.0.10/32"],
    "tls_policy": "plaintext_internal",
    "purpose": "GNI changedetection snapshot facade"
  },
  {
    "identity": "local-playwright",
    "adapter_slug": "playwright",
    "scheme": "http",
    "hostname": "playwright.gni.internal",
    "port": 3000,
    "address_networks": ["10.66.0.11/32"],
    "tls_policy": "plaintext_internal",
    "purpose": "GNI disposable Playwright renderer"
  }
]
```

Each adapter declares one required installation-scoped `api_key` secret slot.
The key is resolved through the Phase 3 secret-reference service and sent only
as `X-API-Key`; it is not stored in endpoint configuration or provenance.

The service route is pre-provisioned for one source target. GNI does not send
arbitrary target URLs to a generic internal browser endpoint. This prevents a
SourceEndpoint from turning trusted acquisition infrastructure into an SSRF
proxy.

## changedetection response proof

Configuration contains the registered identity, an exact snapshot facade URL
whose only query parameter is the matching `watch_uuid`, and the bounded HTML
listing extraction configuration. A successful facade response must provide:

```text
X-GNI-Changedetection-Policy: changedetection-snapshot-v1
X-GNI-Changedetection-Watch: <configured watch_uuid>
X-GNI-Source-URL: <exact SourceEndpoint URL>
Content-Type: text/html | application/xhtml+xml
```

Missing or conflicting watch, source, policy, content type, internal address,
or service identity fails closed.

## Playwright response proof

Configuration selects only `domcontentloaded` or `networkidle`, a timeout from
1 through 60 seconds, a pre-provisioned query-free render route, and bounded
listing selectors. A successful renderer response must provide:

```text
X-GNI-Renderer-Policy: playwright-disposable-v1
X-GNI-Child-Egress-Policy: ip-pinned-public-v1
X-GNI-Source-URL: <exact SourceEndpoint URL>
X-GNI-Wait-Strategy: <configured strategy>
X-GNI-Timeout-Seconds: <configured timeout>
Content-Type: text/html | application/xhtml+xml
```

The renderer policy denotes a disposable browser context with no host mounts
or ambient credentials, restricted downloads, bounded resources, and guarded
child-resource egress. GNI refuses output from a renderer that does not attest
this exact contract.

## Artifact and extraction boundary

Attested HTML still has no trust shortcut. It follows the same path as direct
listings:

```text
installation-registered guarded retrieval
bounded staging and structural HTML identification
mandatory ClamAV scan
credential-free Bubblewrap HTML extraction
accepted immutable Artifact promotion
bounded normalized listing records
Document persistence through the shared worker
```

Relative article URLs resolve against the publisher SourceEndpoint URL, not
the internal service route. The internal route and service policy remain in
retrieval provenance.

## Activation and fallback boundary

Migration `d3f5a7b9c1e4` registers both adapters, exact compatibility and HTML
capabilities, and their required secret slots. It installs no service or
browser, creates no watch or render route, binds no secret, configures no
SourceEndpoint, and performs no cutover.

“Fallback” describes acquisition priority, not an automatic retry. A failed
direct acquisition cannot silently invoke Playwright. The operator must review
and explicitly activate a versioned endpoint configuration after the service,
secret binding, source attestation, Artifact preflight, and extraction preview
pass. Rollback remains an explicit cutover event.

## Deliberate exclusions

- no CAPTCHA, login, paywall, WAF, or access-control bypass;
- no arbitrary target URL submitted to an internal watch/browser service;
- no cookies, publisher credentials, persistent browser profiles, downloads,
  or browser extensions;
- no automatic watch creation, route discovery, fallback, or endpoint
  activation;
- no article-body fetching or content extraction beyond listing records; and
- no claim of live parity until separate low-risk canaries pass.

## Repository proof

The 2026-08-03 candidate passed:

- 106 focused acquisition adapter, worker, Artifact sandbox, egress, runtime,
  and migration tests;
- all 20 migration-safety tests, including clean downgrade/re-upgrade,
  configuration-history refusal, and zero schema drift;
- all 387 non-migration repository regression tests;
- scoped Ruff lint and formatting checks;
- Alembic single head `d3f5a7b9c1e4`; and
- the guarded `/var` inode gate, ending at 62% below the 65% refusal
  threshold.
