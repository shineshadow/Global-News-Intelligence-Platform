# Phase 3 Direct HTTP/API and HTML Listing Extraction

**Status:** Implemented candidate  
**Date:** 2026-08-03  
**Migration:** `c1e3f5a7b9d2`

## Scope

This package adds two exact, public, credential-free adapters:

| Adapter | Endpoint tuple | Artifact |
| --- | --- | --- |
| `direct_json_api` v1 | `api / json / api_client` | JSON |
| `html_listing` v1 | `website / html / web_scraper` | HTML |

The migration registers adapters, exact compatibility tuples, HTML/JSON
media-type and extension evidence, and safe-extraction capabilities. It does
not create a SourceEndpoint configuration, activate an endpoint, bind a
secret, change a rate policy, or perform a cutover.

## Security and execution boundary

Both adapters use the shared IP-pinned public egress guard, including guarded
redirects. Retrieved bytes then pass through bounded Artifact staging,
structural identification, mandatory ClamAV scanning, and exact parsing.

JSON and HTML are parsed only in the credential-free Bubblewrap/seccomp
inspection worker. The worker emits at most 25 records with bounded fields.
The Celery acquisition worker receives only the sandbox-normalized record
mapping; an adapter refuses to normalize raw or absent inspection output.
Accepted original bytes remain immutable Artifacts under the existing
content-addressed promotion boundary.

## Configuration contracts

`direct_json_api` uses arrays of object keys rather than executable query
expressions:

```json
{
  "items_path": ["data", "items"],
  "fields": {
    "url": ["url"],
    "title": ["headline"],
    "summary": ["summary"],
    "published_at": ["published_at"]
  }
}
```

`html_listing` v1 deliberately supports only one simple `tag` or `tag.class`
item selector and simple descendant field selectors. A field may read text or
one named attribute:

```json
{
  "item_selector": "article.story",
  "fields": {
    "url": {"selector": "a", "attribute": "href"},
    "title": {"selector": "h2"},
    "summary": {"selector": "p.summary"},
    "published_at": {"selector": "time", "attribute": "datetime"}
  }
}
```

Required fields are `url` and `title`. Optional fields are `summary`,
`published_at`, `external_id`, `author`, and `language`. Extracted relative
URLs are resolved against the final guarded response URL; fragments are
removed. Non-HTTP(S), user-info, malformed, or empty identities fail closed.

## Deliberate exclusions

- no repository-created or automatically activated endpoint;
- no API key, cookie, session, or other credential slot;
- no POST, pagination, arbitrary JSONPath, XPath, or executable selector;
- no JavaScript execution or browser automation;
- no article-page body fetch or content extraction in this package;
- no access-control, CAPTCHA, paywall, or anti-bot bypass.

Changedetection and Playwright remain the next separately reviewed Phase 3
package. A live direct-listing canary requires an explicit low-risk endpoint,
configuration review, preflight, activation, parity observation, and rollback
proof.

## Repository proof

The 2026-08-03 candidate passed:

- 58 focused sandbox, Artifact, worker, runtime, adapter, and migration tests;
- all 17 migration-safety tests, including downgrade/re-upgrade and zero drift;
- all 381 non-migration regression tests;
- scoped Ruff lint and formatting checks;
- Alembic single head `c1e3f5a7b9d2`; and
- migration verification that no direct-listing endpoint configuration or
  cutover was created.
