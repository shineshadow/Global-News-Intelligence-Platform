# Phase 3 — Shared Source Acquisition Architecture

**Status:** ARCHITECTURE CANDIDATE — NOT FROZEN
**Date:** 2026-07-28
**Phase:** Main Track Phase 3 — Expanded Sources
**First gate:** Phase 3.1 — Source Acquisition Foundation Audit
**Depends on:** GFA-A through GFA-E, Steps 24 through 26, and Calendar
Phase 2 — FROZEN
**Authority:** Owner-approved acquisition and deletion-first security
directives

## 1. Purpose

Phase 3 formalizes one shared acquisition contract before GNI adds RSSHub,
RSS-Bridge, direct website extraction, changedetection.io, or Playwright.
The contract must also be broad enough for later YouTube, audio, official
Calendar, storage, messaging, stream, repository, and bulk-import adapters
without claiming those later adapters are implemented in Phase 3.

The fixed model is:

```text
Source
  persistent publisher, organization, person, or issuing authority
        ↓ owns
SourceEndpoint
  concrete acquisition surface
        ↓ acquired through
AcquisitionAdapter
  versioned implementation and capability declaration
        ↓ produces
AcquisitionArtifact
  exact retrieved payload with authority-backed format evidence
        ↓ accepted and normalized into
Document / Calendar input / other owning subsystem
```

Untrusted bytes are not Documents, evidence, or historical originals merely
because GNI received them. They become canonical inputs only after mandatory
identification and security acceptance.

## 2. Frozen Boundaries Preserved

Phase 3 extends but does not redefine the frozen foundations:

```text
Source.source_type
  what the publisher or issuer is

SourceEndpoint.endpoint_type
  what kind of access surface it is

SourceEndpoint.endpoint_format
  the endpoint's primary declared response/envelope format

SourceEndpoint.acquisition_method
  how GNI acquires from the surface

SourceEndpoint.platform
  optional named distribution/hosting platform

AcquisitionArtifact.artifact_format
  the exact detected representation of one acquired payload

Document.ingestion_format
  historical acquisition-envelope provenance

Document.content_format
  the normalized representation actually stored

semantic document type
  what the normalized document means
```

These dimensions never infer one another automatically.

Examples:

```text
Japanese publisher + South Korean article
  Source country does not become Document geography.

YouTube channel + MP4 download + text transcript
  endpoint type       = video_platform
  endpoint format     = html or json
  artifact format     = mp4
  Document format     = plain_text
  semantic type       = transcript

official calendar endpoint
  endpoint type       = feed, api, website, file_repository, or email
  artifact format     = ical, json, html, PDF, or email_message
  Calendar semantics  = assigned only by the Calendar ingestion adapter
```

## 3. Current-State Audit

GNI already has:

```text
normalized Source and SourceEndpoint persistence
database-backed endpoint type, format, method, and platform catalogs
RSS/Atom compatibility normalization
conditional HTTP requests through ETag and Last-Modified
one Redis claim per endpoint
IngestionRun history
Document identity by SourceEndpoint and external identifier
deterministic generated identifiers
content hashing and DocumentVersion preservation
partial-item savepoints
deterministic classification and Monitor evaluation
poll scheduling and deterministic exponential failure backoff
Source and endpoint management UI
```

The current foundation does not yet provide:

```text
an adapter registry and exact capability declarations
durable database acquisition leases
authority-backed Artifact Format persistence
AcquisitionArtifact and ArtifactRejection records
versioned PRONOM/DROID signature releases
mandatory deletion-first artifact security
typed adapter configuration
secret-reference persistence
hierarchical rate-limit policy and durable quota state
the expanded health-state machine
RSSHub, RSS-Bridge, direct listing, changedetection, or Playwright adapters
```

The existing Redis endpoint claim remains a useful fast coordination layer,
but it is not the final durable idempotency authority.

## 4. Endpoint Catalog Evolution

Frozen catalog rows are never destructively deleted. Superseded values remain
referenceable for history and are marked inactive only after a guarded usage
audit and corrective migration.

### 4.1 Endpoint Types

Target active values:

```text
website
feed
api
email
social_platform
video_platform
audio_platform
file_repository
messaging_platform
object_storage
cloud_storage
message_queue
manual
other
```

`podcast` becomes inactive prospectively. It remains referenceable because a
podcast is a program/content layer distributed through feeds, websites,
audio/video platforms, or several of those surfaces.

`calendar_feed` is not introduced. Calendar meaning is independent of the
access surface and acquired representation.

Storage meanings are:

```text
file_repository
  remotely browsable or transferable file collection

object_storage
  bucket/blob/key-oriented object service

cloud_storage
  user/team document and file service
```

### 4.2 Acquisition Methods

Target active values:

```text
http_fetch
feed_parser
api_client
platform_api
web_scraper
browser_automation
email_client
file_download
file_transfer
storage_client
filesystem_import
repository_sync
stream_consumer
database_query
message_queue_consumer
media_downloader
webhook
bulk_import
manual
other
```

Historical protocol-specific values remain referenceable but become inactive
after guarded migration:

```text
imap
pop3
ftp
sftp
```

Protocol and operation detail belongs to typed adapter configuration:

```text
email_client.transport       = imap | pop3
file_transfer.transport      = ftp | ftps | sftp | webdav
stream_consumer.transport    = websocket | sse | provider_stream
repository_sync.sync_mode    = clone_or_update | fetch_only
repository_sync.transport    = https | ssh
```

`message_queue` is an endpoint type; `message_queue_consumer` is the method.
`media_downloader` is the method used by yt-dlp-class acquisition in the
later YouTube phase.

### 4.3 Platforms

The existing platform catalog remains extensible. Phase 3 adds the approved
reference values:

```text
dailymotion
odysee
bilibili
weibo
wechat
line
kakaotalk
snapchat
douyin
kuaishou
vk
gab
parler
gettr
kick
peertube
lemmy
quora
tumblr
pinterest
flickr
soundcloud
spotify
apple_podcasts
patreon
wordpress
blogger
```

RSSHub, RSS-Bridge, changedetection.io, Playwright, and yt-dlp are adapters or
acquisition infrastructure, not content platforms.

## 5. Acquisition Adapter Contract

Every executable acquisition implementation registers:

```text
adapter_slug
adapter_version
configuration_schema_version
supported endpoint types
supported endpoint envelope formats
supported acquisition methods
supported platforms
produced Artifact formats or families
secret requirements
rate-limit capabilities
pagination or streaming behavior
idempotency-key construction
health probes
resource limits
```

An adapter receives stable database identifiers and resolves current
configuration inside the worker. Credentials, embedded payloads, parser
output, and untrusted bytes never travel as Celery arguments.

The registry validates the complete tuple:

```text
endpoint type
endpoint envelope format
acquisition method
platform
adapter
configuration version
```

Individually valid slugs do not make an unsupported tuple valid.

## 6. Compatibility Registries

One giant permissive matrix is prohibited. Compatibility is expressed through
four coordinated registries.

### 6.1 Endpoint Contract Matrix

| Endpoint type | Permitted methods | Platform rule |
|---|---|---|
| `website` | `http_fetch`, `web_scraper`, `browser_automation`, `file_download` | Optional |
| `feed` | `feed_parser`, `http_fetch`, `api_client` | Optional |
| `api` | `api_client`, `platform_api`, `http_fetch`, `webhook` | Required for `platform_api` |
| `email` | `email_client`, `webhook`, `manual` | Optional |
| `social_platform` | `platform_api`, `api_client`, `web_scraper`, `browser_automation`, `stream_consumer` | Required |
| `video_platform` | `media_downloader`, `platform_api`, `api_client`, `web_scraper`, `browser_automation` | Required |
| `audio_platform` | `media_downloader`, `platform_api`, `api_client`, `feed_parser` | Required |
| `file_repository` | `file_download`, `file_transfer`, `repository_sync`, `http_fetch` | Optional |
| `messaging_platform` | `platform_api`, `api_client`, `stream_consumer`, `webhook` | Required |
| `object_storage` | `storage_client`, `api_client`, `file_download` | Optional |
| `cloud_storage` | `storage_client`, `platform_api`, `api_client`, `webhook` | Optional |
| `message_queue` | `message_queue_consumer`, `stream_consumer` | Optional |
| `manual` | `manual`, `bulk_import`, `filesystem_import` | Optional |
| `other` | Explicit registered adapter only | Optional |

### 6.2 Adapter Capability Matrix

The adapter registry narrows the broad endpoint matrix to exact supported
tuples and produced formats. Catalog recognition never claims that an adapter
exists.

### 6.3 Artifact Format Catalog

The authority-backed catalog identifies exact acquired representations and
their versions, aliases, media types, extensions, external identifiers,
signatures, and relationships.

### 6.4 Artifact Parser/Extractor Matrix

This registry distinguishes:

```text
recognized format
safe identification support
safe parser support
safe extraction support
normalized result formats
unsupported but recognizable format
forbidden format
```

Only formats with the required safe identification and parser capability may
be promoted.

## 7. Canonical Artifact Format Catalog

GNI does not invent format equivalence from common filenames.

The authority order is:

1. PRONOM PUID for precise file-format identity and version where available;
2. IANA for registered media types;
3. the originating IETF, ISO/IEC, W3C, OASIS, SMPTE, ECMA, vendor, or other
   normative specification authority;
4. Library of Congress Format Description Documents for preservation and
   relationship information;
5. an explicitly labeled GNI `de_facto` or `local` identity only when no
   adequate external identity exists.

Primary authority references:

- [PRONOM](https://pronom.nationalarchives.gov.uk/about)
- [IANA Media Types](https://www.iana.org/assignments/media-types/media-types.xhtml)
- [Library of Congress Format Descriptions](https://www.loc.gov/preservation/digital/formats/fdd/)
- [PREMIS](https://www.loc.gov/standards/premis/index.html)

Extensions, media types, common names, and PUIDs are many-to-many mappings.
No mapping is automatically an `exact_match`.

Signature verification is mandatory when the active authority catalog
provides an applicable signature. Some valid text/structured formats do not
have a unique byte signature. They may be accepted only when an exact safe
parser, adapter allowlist, declared/observed media type, structural markers,
and extension policy all agree. If those independent checks cannot establish
one positive identity, the payload is deleted.

### 7.1 Proposed Persistence

```text
artifact_formats
artifact_format_external_identifiers
artifact_format_media_types
artifact_format_extensions
artifact_format_aliases
artifact_format_relationships
artifact_signature_releases
artifact_format_signatures
```

`artifact_formats` records:

```text
stable internal slug
canonical display name
format family and kind
optional parent format
version/profile label
authority status
container/compression/manifest capabilities
active state and validity
provenance
```

Authority status values:

```text
registered
standardized
de_facto
vendor_defined
local
unknown
```

External-identifier relationships:

```text
exact_match
broader_match
narrower_match
related_match
normative_specification
preservation_description
```

### 7.2 Format Coverage

The initial candidate coverage includes:

```text
Text/markup
  html, plain_text, markdown, rtf

Web archives
  warc, mhtml

Feeds/structured data
  rss, atom, json_feed, json, json_ld, ndjson, yaml, xml,
  rdf_xml, turtle, n_triples

Messages/calendar
  email_message, ical

Documents/e-books
  pdf, doc, docx, odt, ppt, pptx, odp, xls, xlsx, ods, epub

Tabular text
  csv, tsv

Images
  image, jpeg, png, webp, gif, svg, avif, heic, tiff

Video/audiovisual containers
  video, mp4, webm, matroska, mpeg_ts, quicktime, avi

Audio
  audio, mp3, m4a, aac, flac, wav, ogg, opus

Timed text
  webvtt, subrip, ttml, ass, lrc

Streaming manifests
  m3u8, dash_mpd

Archives/compression
  archive, zip, tar, gzip, bzip2, xz, zstd, 7z, rar

Fallbacks
  binary, other
```

Broad values such as `image`, `audio`, `video`, and `archive` organize the
catalog and preserve compatible endpoint declarations. They are not terminal
accepted Artifact identities. The detector must resolve an approved leaf
format such as JPEG, MP4, FLAC, or ZIP.

`binary` and `other` remain useful endpoint/catalog compatibility values, but
an acquired payload detected only as `binary` or `other` is not positively
identified and is deleted. The deletion-first boundary never promotes a broad
family or fallback merely because the general media family is known.

Common extensions are aliases, not identities:

```text
jpg, jpeg, jpe  → candidate evidence for JPEG
vtt             → candidate evidence for WebVTT
srt             → candidate evidence for SubRip
mkv             → candidate evidence for Matroska
mov             → candidate evidence for QuickTime
```

## 8. Acquisition Artifacts

An Artifact is one acquired byte object, not a normalized Document.

Proposed persistence:

```text
acquisition_artifacts
  SourceEndpoint and IngestionRun
  parent Artifact for nested containers
  canonical Artifact Format
  declared and observed media type
  original filename and observed extension chain
  storage reference
  byte length and cryptographic content hash
  detector, version, signature release, confidence, and evidence
  adapter and retrieval provenance
  acceptance time
```

Nested containers append child Artifacts:

```text
archive.warc.gz
  gzip Artifact
      └── WARC Artifact

documents.tar.zst
  Zstandard Artifact
      └── TAR Artifact
             ├── PDF Artifact
             └── CSV Artifact
```

No suspicious parent or child is retained.

## 9. Security-Critical Deletion Boundary

This entire section is security-critical and non-configurable.

There is no API, UI, SQLAdmin control, adapter option, environment switch, or
operator override that can weaken, bypass, postpone, quarantine, retain, or
restore a rejected payload. Read-only rejection outcomes may be shown to an
authorized operator; the rules and execution controls are not exposed.

False-positive deletion is acceptable. Reacquisition after correcting the
catalog, adapter, or source configuration is the recovery mechanism.

### 9.1 Isolated Staging

Untrusted bytes enter only:

1. an anonymous `O_TMPFILE`, where supported;
2. ephemeral `tmpfs`; or
3. a dedicated staging filesystem mounted `noexec,nodev,nosuid`.

Staging is outside web, application asset, canonical Artifact, Document,
export, backup, and downstream-worker paths.

### 9.2 Mandatory Immediate Deletion

Deletion is required for:

```text
signature/extension mismatch
signature/media-type mismatch
signature/adapter expectation mismatch
unknown or ambiguous format
multiple incompatible signatures or polyglot content
unavailable/invalid/outdated required signature release
unavailable required detector or scanner
parser failure, malformed/truncated payload, or changing hash
unexpected executable, script, macro, or active content
encrypted/password-protected archive
archive traversal, link, device, socket, depth, count, size, or ratio violation
any rejected nested member
unexpected streaming manifest or reference
malware/security match
unsupported safe parser
resource-limit violation
any other suspicious or unverifiable condition
```

An anonymous file is closed without being linked. A path-backed file is
closed, unlinked, and verified absent. Extracted children are removed,
multipart uploads are aborted, and ephemeral encryption keys are destroyed.
Only after deletion is verified may GNI write the rejection record.

### 9.3 Identification Flow

```text
receive into isolated staging
        ↓
calculate bounded hash and structural evidence
        ↓
        identify through active signature release and exact safe parser
        ├─ identification infrastructure unavailable
        │      → delete immediately
        │      → record operational/security rejection afterward
        └─ candidate identity
                ↓
        container-aware format verification
                ├─ unknown, ambiguous, polyglot, malformed
                │      → delete immediately
                └─ exact detected format
                        ↓
        compare approved extension chain, media type, adapter allowlist,
        parser result, nested members, and resource limits
                        ├─ any disagreement or doubt
                        │      → delete immediately
                        └─ every required check succeeds
                                ↓
                        atomically promote accepted Artifact
```

Container-aware signatures prevent naïve mistakes such as treating DOCX as a
generic ZIP. An extensionless payload is rejected by default. A narrowly
declared adapter may accept extensionless output only with exact signature,
allowlist, media-type, parser, and security agreement.

### 9.4 Rejection Persistence

Rejected bytes never receive a stored Artifact row. After verified deletion,
GNI appends an `artifact_rejections` row containing identifiers, declared and
detected metadata, signature/detector versions, byte length, cryptographic
hash, reason, deletion time, and provenance.

Database constraints require:

```text
storage_reference IS NULL
deleted_at IS NOT NULL
deletion_verified = true
```

No suspicious bytes, excerpts, thumbnails, archive members, or samples enter
logs.

## 10. Signature and Catalog Release Lifecycle

Authority updates never mutate active meaning silently.

```text
retrieve candidate authority release
        ├─ network failure
        │      → retain active release; bounded retry
        ├─ TLS/origin failure
        │      → delete candidate; security alert
        ├─ missing version/digest
        │      → delete candidate; block update
        └─ retrieved
                ↓
        verify digest, origin, schema, and release identity
                ├─ mismatch/invalid/duplicate identity with different bytes
                │      → delete candidate; retain active release
                └─ valid
                        ↓
        import into isolated candidate catalog
                ├─ unknown authority identifier
                ├─ conflicting PUID definition
                ├─ invalid exact-match claim
                ├─ changed historical meaning
                ├─ missing parent or hierarchy cycle
                ├─ signature/alias collision
                └─ any failure
                       → reject candidate; retain active release
                        ↓
        run consistency and detection-corpus regression
                ├─ formerly accepted sample becomes unknown
                ├─ identity changes unexpectedly
                ├─ ambiguity/polyglot result increases
                ├─ forbidden content becomes acceptable
                ├─ detector crash/timeout
                └─ any regression
                       → reject candidate; retain active release
                        ↓
        dry-run against recent non-payload Artifact metadata
                ├─ rejection/acceptance threshold anomaly
                ├─ adapter allowlist incompatibility
                └─ any failure
                       → reject candidate; retain active release
                        ↓
        atomically activate versioned release
                ├─ transaction failure
                │      → rollback; retain previous release
                └─ success
                        ↓
        monitor
                ├─ anomaly
                │      → atomically restore previous release
                │      → block failed release
                └─ stable
                       → retain active release
```

Removed or deprecated external identifiers remain historically referenceable.
A changed external meaning creates a new validity interval or mapping; it
never rewrites historical evidence.

## 11. Idempotency

### 11.1 Execution

```text
one active acquisition lease per SourceEndpoint
Redis claim for fast coordination
PostgreSQL lease as durable authority
scheduled identity = endpoint + schedule window + configuration version
manual identity = endpoint + explicit request idempotency key
duplicate task = replay/skip, not a second logical acquisition
```

Lease expiry, ownership, heartbeat, takeover, and finalization are
transactional and auditable.

### 11.2 Discovery and Artifacts

```text
stable provider identifier when available
deterministic generated identity otherwise
canonicalized URL retained beside original URL
cryptographic payload hash
one logical Artifact for the same run/resource/hash identity
container member identity includes parent and normalized member path
identical reacquisition is unchanged
changed accepted content appends history
rejected content never becomes a duplicate stored Artifact
```

### 11.3 Documents and Downstream Work

Current Document identity remains endpoint plus external identifier.
Conditional HTTP 304 creates no Document or Artifact. Partial processing does
not advance fetch validators. Classification, Monitor matches, alerts, and
Calendar evidence retain their independent idempotency contracts.

## 12. Secret Boundary

Database rows and endpoint configuration store references only.

Authentication types:

```text
none
bearer_token
api_key_header
api_key_query
basic_auth
oauth2_client_credentials
cookie_session
ssh_key
custom
```

Secret backends:

```text
environment
systemd_credential
external_secret_store
```

Secret scopes:

```text
endpoint
source
platform_account
installation
```

Secret states exposed operationally:

```text
configured
missing
invalid
expired
rotation_required
disabled
```

Secret values never appear in URLs, ordinary metadata, provenance, logs,
errors, Celery arguments, API responses, HTML, exports, or source-control.
The worker resolves the value immediately before use and supplies it only to
the assigned adapter. Query-string credentials require an adapter-declared
provider necessity. Missing/invalid credentials fail closed.

## 13. Rate-Limit Contract

Rate-limit modes:

```text
provider_defined
robots_aware
conservative
custom
```

Scopes:

```text
endpoint
origin
platform
credential
installation
```

Initial constrained values:

| Field | Constraint/default |
|---|---|
| requests per period | `1..10000`, default `6` |
| period seconds | `1..86400`, default `60` |
| burst size | `1..100`, default `1` |
| endpoint concurrency | fixed maximum `1` |
| origin concurrency | `1..16`, default `2` |
| poll interval | minimum `60`, default `900` seconds |
| retry base | `1..86400`, default `60` seconds |
| retry maximum | base through `604800`, default `86400` seconds |
| retry jitter | `0..50`, default `20` percent |
| daily budget | null or positive integer |
| exhaustion action | `delay`, `disable`, `operational_exception`; default `delay` |

The strictest applicable provider reset/Retry-After, robots rule,
credential/platform quota, endpoint override, and installation default wins.
Rate-limit waiting occurs outside transactions and is not counted as a
structural parsing failure.

## 14. UI and Authorization

The Source/Endpoint operator UI will show:

```text
identity and exact compatibility tuple
adapter and configuration version
verification and health
last successful and failed acquisition
effective poll schedule and rate policy
inherited versus overridden rate values
provider reset/Retry-After observations
safe extraction preview
accepted Artifact counts
read-only rejection outcomes
secret configured/state indicators without values
source and endpoint history
```

Specialized forms cover RSSHub, RSS-Bridge, listing selectors,
changedetection, and Playwright only when their adapters are implemented.

The security-critical deletion rules, detectors, execution paths, bypasses,
and retention behavior have no configurable UI or API exposure.

FastAPI services enforce authorization. The current single-operator
deployment may expose authorized workflows before the later multi-user
authentication system, but every mutation records actor and reason and uses a
capability-ready server-side boundary.

Admin UI owns operational configuration and actions. Authentication owns
identity, sessions, permissions, reauthentication, revocation, and actor
attribution. Hiding controls in HTML is never authorization.

## 15. Health and Failure States

Endpoint health distinguishes:

```text
never_checked
verified
verified_empty
degraded
failing
stale
disabled
verification_failed
rate_limited
authentication_failed
adapter_unavailable
security_rejection
```

Transport, rate, authentication, parsing, extraction, security, and
downstream-enrichment failures remain separate dimensions. A valid empty
official feed is not structurally broken.

## 16. Worker and Transaction Boundary

The acquisition worker:

1. claims a durable endpoint lease;
2. commits the logical run and configuration snapshot;
3. resolves rate and secret policy;
4. retrieves outside database transactions into isolated staging;
5. performs mandatory identification and security checks;
6. deletes rejected bytes before appending rejection metadata;
7. atomically promotes accepted Artifacts;
8. normalizes accepted content through the owning adapter;
9. commits Document/Calendar ownership changes in bounded transactions;
10. triggers idempotent downstream work;
11. finalizes health, rate, metrics, and lease state.

No database transaction remains open during network, browser, model, media,
signature-scanning, archive extraction, or other untrusted/long-running I/O.

## 17. Roadmap Ownership

Phase 3 implements:

```text
shared acquisition and adapter contract
Artifact catalog and security foundation
durable acquisition leases
rate-limit and secret-reference foundation
RSSHub
RSS-Bridge
direct HTTP/API and HTML listing extraction
changedetection.io
Playwright fallback
acquisition-health and rate-limit UI
```

Recognized but deferred:

```text
YouTube and yt-dlp media acquisition           Main Phase 4
local audio transcription                      Main Phase 5
official/recurring Calendar ingestion           Calendar Phase 3
general message queue and streaming adapters    later adapter work
database query adapters                         later controlled adapter work
cloud/object storage adapters                   later unless pulled forward
full multi-user authentication                  later security/auth track
```

Catalog recognition is not an implementation claim.

## 18. Required Proof Matrix

The Phase 3 foundation freeze candidate must directly prove:

1. Source identity survives endpoint replacement and retirement.
2. Every executable adapter tuple is explicitly registered and compatible.
3. Individually valid but unsupported tuple combinations are rejected.
4. Deprecated frozen catalog values remain historically referenceable.
5. Calendar format does not become an endpoint type.
6. Podcast is modeled through its real endpoint surfaces.
7. Endpoint envelope, Artifact format, Document content format, and semantic
   type remain independent.
8. Artifact external mappings are many-to-many and authority-provenanced.
9. Extensions never establish canonical identity alone.
10. Exact PRONOM/IANA/standards relationships do not silently collapse.
11. Signature releases are versioned, hashed, regression-tested, and atomic.
12. A failed catalog update leaves the active release unchanged.
13. Historical external mappings are never overwritten.
14. Accepted Artifacts record detector and signature-release provenance.
15. A signature-less format requires exact safe-parser and independent
    evidence agreement.
16. Signature/extension mismatch deletes bytes before rejection logging.
17. MIME/signature or adapter/signature mismatch does the same.
18. Unknown, ambiguous, polyglot, or malformed payloads are deleted.
19. Detector/scanner unavailability fails closed and deletes the payload.
20. No rejected payload receives a storage reference.
21. No security policy or bypass is exposed through UI, API, SQLAdmin, or
    adapter configuration.
22. Broad family, `binary`, and `other` results cannot be promoted as
    accepted Artifact identities.
23. Container-aware detection recognizes valid compound formats.
24. One rejected archive member deletes the whole acquired archive tree.
25. Archive traversal, bomb, link, and device-file cases are rejected.
26. Accepted nested Artifacts preserve parent/member provenance.
27. Duplicate scheduled tasks produce one logical acquisition.
28. Redis loss cannot defeat the durable endpoint lease.
29. Replay does not duplicate Artifacts, Documents, classifications,
    Monitor matches, alerts, or Calendar evidence.
30. Partial item failure does not advance conditional-fetch validators.
31. HTTP 304 produces no new Artifact or Document.
32. Secret values cannot enter database metadata, logs, Celery, API, or HTML.
33. Shared credential/platform quotas apply across endpoints.
34. Retry-After and stricter robots/provider policy override local defaults.
35. Rate limiting does not count as structural endpoint failure.
36. Operator mutations are server-authorized and actor/reason audited.
37. Security rejections remain read-only operational outcomes.
38. Retrieval and untrusted processing hold no database transaction open.
39. A valid empty endpoint can be healthy.
40. Unsupported future catalog entries do not claim adapter implementation.
41. Existing RSS/Atom ingestion remains compatible.
42. Clean migration, guarded downgrade, complete regression, live operation,
    and zero Alembic drift pass.

## 19. Implementation Sequence

```text
Phase 3.1 architecture candidate
        ↓
formal architecture review and freeze
        ↓
corrective/additive catalog and Artifact migrations
        ↓
signature release importer and deletion-first detector
        ↓
durable lease, adapter registry, secret references, rate policy
        ↓
shared acquisition worker
        ↓
RSSHub and RSS-Bridge
        ↓
direct HTTP/listing extraction
        ↓
changedetection and Playwright fallback
        ↓
Source Acquisition and Health UI
        ↓
formal Phase 3 implementation freeze review
```

No migration, worker, adapter, security runtime, or UI behavior is frozen by
this architecture candidate alone.
