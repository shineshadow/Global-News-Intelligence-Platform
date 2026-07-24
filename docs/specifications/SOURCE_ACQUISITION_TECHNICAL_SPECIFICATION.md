# Source Acquisition Technical Specification

**Project:** Global News Intelligence Platform  
**Document:** `SOURCE_ACQUISITION_TECHNICAL_SPECIFICATION.md`  
**Status:** Development Placeholder / Architectural Seed  
**Version:** 0.1-placeholder

---

## 1. Purpose

This document defines the future authoritative acquisition architecture for discovering, configuring, fetching, validating, and maintaining non-uniform information sources.

It should eventually absorb detailed acquisition rules that would otherwise make the Master excessively large.

---

## 2. Acquisition Priority

Preferred acquisition order:

```text
Native RSS / Atom
        ↓
RSSHub
        ↓
RSS-Bridge
        ↓
Direct HTTP listing/API retrieval
        ↓
Direct website extraction
        ↓
changedetection.io
        ↓
Playwright
        ↓
platform-specific adapters
```

The least expensive reliable acquisition method should be preferred.

---

## 3. Source Versus Endpoint

A Source is the organization/publisher.

A Source Endpoint is a concrete acquisition surface.

Examples:

```text
Source:
Reuters

Endpoints:
Asia-Pacific listing page
Technology listing page
Search/API surface
Synthetic-feed bridge
```

Changing acquisition strategy should normally modify or add endpoints without destroying Source identity or history.

---

## 4. Endpoint Types to Support

Future canonical endpoint types may include:

```text
rss
atom
rsshub
rss_bridge
html_listing
html_article
json_api
xml_api
ics
pdf_listing
changedetection
playwright_listing
youtube_channel
youtube_playlist
social
newsletter
podcast
manual
```

---

## 5. Synthetic Feed / Listing-Page Acquisition

For publishers without RSS, the platform should be able to discover articles directly without generating internal RSS XML.

Conceptual flow:

```text
Listing page
     ↓
fetch/render
     ↓
extract repeating article records
     ↓
normalize article URLs
     ↓
detect unseen URLs
     ↓
fetch article pages
     ↓
content extraction
     ↓
normalized Documents
```

Possible endpoint configuration fields:

```text
listing_url
article_container_selector
link_selector
title_selector
date_selector
summary_selector
next_page_selector
include_url_regex
exclude_url_regex
requires_javascript
render_wait_strategy
```

Selectors are configuration, not hard-coded application logic.

---

## 6. Health and Reliability

Endpoint health must distinguish:

```text
never_checked
verified
verified_empty
degraded
failing
stale
disabled
verification_failed
```

A syntactically valid but temporarily empty official feed should not necessarily be treated as structurally broken.

Reliability scoring should consider:

```text
fetch success rate
parse success rate
item freshness
consecutive failures
redirect stability
TLS behavior
GUID/URL stability
content extraction success
rate-limit behavior
```

---

## 7. TLS and Security

- Do not globally disable certificate validation to accommodate one source.
- Per-source exceptions require explicit configuration, auditability, and risk review.
- Prefer alternate official hosts or acquisition surfaces when certificate chains are defective.
- Credentials and API tokens must not be stored in endpoint metadata in plaintext.

---

## 8. Canonicalization and Deduplication

Acquisition should normalize:

```text
URL fragments
tracking parameters
known campaign parameters
redirected canonical URLs
publisher-specific duplicate URL forms
```

Raw source URLs should remain available for provenance.

---

## 9. Extraction Layers

Recommended progression:

```text
HTTP response
  ↓
structured feed/API parse
  ↓
HTML listing extraction
  ↓
article content extraction
  ↓
JavaScript rendering only when required
```

Article extraction may use:

```text
trafilatura
BeautifulSoup
lxml
site-specific selectors
structured data (JSON-LD)
```

---

## 10. Anti-Bot / Failure Policy

Future design should explicitly address:

- 403/429 handling,
- robots and publisher restrictions,
- rate limiting,
- exponential backoff,
- user-agent policy,
- cookies/session requirements,
- CAPTCHA detection,
- login/paywall detection,
- legal/terms review for high-risk acquisition methods.

The platform should fail closed rather than silently bypassing access controls.

---

## 11. Source Discovery and Maintenance

This specification should integrate with `SOURCE_DISCOVERY_AND_MAINTENANCE.md` and eventually define:

```text
candidate discovery
review queue
verification
activation
revalidation
replacement endpoints
historical preservation
retirement
```

---

## 12. API Placeholder

Potential routes:

```text
GET  /api/v1/sources
GET  /api/v1/source-endpoints
POST /api/v1/source-endpoints/{id}/verify
POST /api/v1/source-endpoints/{id}/poll
POST /api/v1/source-endpoints/{id}/disable
POST /api/v1/source-endpoints/{id}/revalidate
```

Future HTML/synthetic-feed configuration will need validation endpoints and preview tools.

---

## 13. Worker Placeholder

Potential workers:

```text
rss-ingestion-worker
web-listing-worker
web-article-worker
playwright-worker
source-health-worker
source-revalidation-worker
calendar-ingestion-worker
youtube-discovery-worker
```

---

## 14. Benchmark Placeholder

Measure by acquisition method:

```text
fetch success
parse/extraction success
false article discovery
missed article rate
latency
bandwidth
CPU/memory
browser-render cost
site-breakage frequency
duplicate creation
```

---

## 15. Open Decisions

- generic selector configuration schema,
- whether synthetic RSS export is useful externally,
- Playwright pool architecture,
- per-domain concurrency/rate policies,
- proxy support,
- HTML-change detection strategy,
- article extraction fallback ordering,
- verified-empty endpoint semantics.
