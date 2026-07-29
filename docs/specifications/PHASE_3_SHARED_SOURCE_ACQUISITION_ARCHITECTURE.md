# Phase 3 — Shared Source Acquisition Architecture

**Status:** ARCHITECTURE FROZEN
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

An Artifact is one immutable logical endpoint-resource version backed by one
accepted byte payload, not a normalized Document.

Proposed persistence:

```text
artifact_payloads
  immutable content-addressed accepted bytes
  cryptographic hash and byte length
  storage reference and verified format

acquisition_artifacts
  immutable accepted logical SourceEndpoint resource version
  stable adapter/provider resource identity
  payload reference
  parent Artifact for nested containers
  optional forward same-resource supersession
  canonical Artifact Format and member path
  detector, version, signature release, confidence, and evidence
  adapter and retrieval provenance
  acceptance time

acquisition_artifact_observations
  one append-only observation per IngestionRun/retrieval identity
  Artifact reference
  declared/observed media type, filename, extension chain, and locator
  HTTP/provider retrieval evidence and observation time

artifact_rejections
  post-deletion metadata for one rejected retrieval
```

`artifact_payloads` has one content-addressed identity by approved
cryptographic hash and byte length. A matching hash never bypasses staging,
scanner, detector, or parser checks; reuse occurs only after the newly
received bytes independently pass.

`acquisition_artifacts` is immutable. Changed accepted bytes append a new
same-resource Artifact version that points forward through a constrained
`supersedes_artifact_id`; the older row and payload remain unchanged.
Identical reacquisition reuses the accepted Artifact/payload and appends a new
observation, preserving the new IngestionRun without duplicating stored
bytes.

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

Retrieval streams under a hard installation byte ceiling and an
adapter-specific lower ceiling. Oversized declared content is rejected before
body retrieval. A stream that crosses its limit is terminated and its staged
bytes are deleted. Unbounded buffering, decompression, archive expansion, and
parser output are prohibited.

### 9.2 Outbound Retrieval Boundary

All endpoint and redirect destinations pass a non-bypassable SSRF/egress
validator before connection:

```text
approved scheme for the exact adapter
normalized hostname and port
no user-info credentials in the URL
DNS resolution through the controlled resolver
rejection of loopback, link-local, multicast, unspecified, private,
carrier-grade NAT, and cloud-metadata destinations
revalidation of every redirect and resolved address
bounded redirect count, header bytes, response bytes, and duration
TLS verification and approved certificate policy
```

DNS rebinding protection validates the address actually used for the
connection, not only a preliminary hostname lookup. Redirects never inherit
authorization headers or query credentials across origins.

GNI-owned local RSSHub, RSS-Bridge, changedetection, object-storage, or other
infrastructure cannot be enabled through an endpoint-level bypass. It uses an
installation-registered internal-service identity with exact adapter,
scheme, host/address range, port, TLS policy, and purpose. Arbitrary Sources
cannot target that internal range, and the registration does not weaken
public endpoint validation.

Browser automation runs in a disposable browser context with no host mounts,
no ambient credentials, restricted download paths, bounded child-resource
egress, and the same destination policy. An adapter receives only the exact
secret slots explicitly bound to its request.

### 9.3 Inspection Sandbox

Mount flags do not protect a worker from a vulnerable detector, archive
reader, media probe, or document parser. All untrusted inspection runs in a
separate, disposable sandbox identity with:

```text
unprivileged user and group
no network
no database or Redis credentials
no acquisition secrets
no canonical Artifact or Document write access
read-only detector, scanner, parser, and signature-release inputs
an isolated mount and process namespace
syscall restrictions
CPU, memory, process, output, file-count, byte, and wall-clock limits
no shell interpolation or provider-controlled command arguments
one bounded structured result channel
```

The implementation may use namespaces, seccomp, cgroups, a locked-down
container, or an equivalently reviewed isolation mechanism. The selected
mechanism and every parser invocation are implementation freeze gates.

At least one versioned malware/security scanner is mandatory for Artifact
acceptance. Detector and scanner engine versions and signature releases are
recorded. If the sandbox, required detector, scanner, or active signatures
cannot be verified before retrieval, GNI does not make the request. If the
failure occurs after bytes enter staging, those bytes are deleted
immediately.

A timeout, crash, signal, excessive output, invalid structured response, or
attempted sandbox violation is a security rejection. No preview, thumbnail,
text extraction, metadata enrichment, or downstream callback occurs before
the complete payload tree is accepted.

### 9.4 Mandatory Immediate Deletion

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

### 9.5 Identification Flow

```text
receive into isolated staging
        ↓
calculate bounded hash and structural evidence in the inspection sandbox
        ↓
identify through active signature release, mandatory scanner, and exact
safe parser
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

### 9.6 Rejection Persistence

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

If PostgreSQL or structured logging is unavailable, deletion still occurs.
The worker then emits a redacted post-deletion event through every available
local operational channel and retries metadata-only persistence. Rejection
logging failure can never retain or reconstruct the payload.

### 9.7 Accepted-Artifact Promotion

All members of a nested payload tree must pass before any member becomes
visible as accepted. Promotion means atomic visibility, not an unsafe
assumption that a filesystem rename is always available.

For filesystem storage:

1. copy or move verified bytes into an anonymous temporary object on the
   destination filesystem;
2. recalculate and compare the complete cryptographic hash;
3. apply immutable ownership and permission policy;
4. atomically link/rename the object to its content-addressed location; and
5. commit the Artifact tree and canonical visibility pointer transactionally.

For object storage:

1. upload to an opaque, unreadable staging key or multipart upload;
2. verify provider checksum, byte length, and GNI cryptographic hash;
3. complete an immutable content-addressed object;
4. expose it only through the committed PostgreSQL Artifact pointer; and
5. abort/delete incomplete or unreferenced objects.

No public URL, web route, downstream task, parser preview, or canonical
storage reference exists before successful promotion. A database failure
leaves no visible Artifact; an idempotent garbage collector removes
unreferenced accepted-byte objects without ever inspecting or preserving
rejected content.

## 10. Signature and Catalog Release Lifecycle

Authority updates never mutate active meaning silently.

The initial trusted release is a reviewed, repository-pinned bootstrap
snapshot with authority origin, release identifier, byte length, and
cryptographic digest. Installation verifies that pinned digest before the
Artifact path can activate. GNI does not bootstrap by downloading an
unreviewed "latest" release at first start.

Every later authority payload is itself untrusted acquisition input. It uses
the outbound guard, bounded staging, active detector/scanner, and inspection
sandbox. When an authority does not publish a cryptographic signature or
digest, GNI records that fact: TLS and exact origin establish transport,
while GNI's locally calculated digest establishes immutable candidate
identity. GNI never labels an unsigned authority release as cryptographically
signed.

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

Rollback changes only the release used for new identification. Existing
accepted/rejected records retain the exact release and detector provenance
that produced their decision.

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
one immutable Artifact version for endpoint/resource/hash identity
one append-only observation for every logical retrieval
one content-addressed payload for accepted identical bytes
container member identity includes parent and normalized member path
identical reacquisition reuses bytes but preserves observation history
changed accepted content appends a forward same-resource Artifact version
rejected content never becomes a duplicate stored Artifact
```

### 11.3 Documents and Downstream Work

Current Document identity remains endpoint plus external identifier.
Conditional HTTP 304 creates no Document or Artifact. Partial processing does
not advance fetch validators. Classification, Monitor matches, alerts, and
Calendar evidence retain their independent idempotency contracts.

## 12. Secret-Reference Contract

GNI persists the identity, purpose, scope, and backend location of a secret,
but never persists the secret value in ordinary application storage.

### 12.1 Adapter Requirements and Slots

Each versioned adapter declares named secret slots, whether each is required,
permitted authentication types, and permitted binding scopes. Common slots
include:

```text
username
password
bearer_token
api_key
client_id
client_secret
cookie_session
ssh_private_key
ssh_key_passphrase
webhook_signing_secret
database_dsn
```

Adapters cannot invent secret-bearing metadata keys at runtime. `custom`
authentication requires a registered, versioned adapter schema and is not an
escape hatch.

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

### 12.2 Global References and Acquisition Bindings

Secret references are a cross-cutting platform concern. Phase 3 creates a
global `secret_references` identity rather than an acquisition-only secret
store. Acquisition owns its binding table; later Alert, AI, storage, and
other consumers may adopt the same reference without sharing domain policy.

```text
secret_references
  stable identity and display name
  backend
  non-secret backend reference
  operational state
  rotation due time
  last resolution time/status
  immutable change history

acquisition_secret_bindings
  secret reference
  adapter and declared secret slot
  exact endpoint/source/platform-account/installation scope
  active validity
  actor and reason
  immutable change history
```

Secret backends:

```text
environment
systemd_credential
external_secret_store
```

Binding scopes:

```text
endpoint
source
platform_account
installation
```

Scope checks require exactly the owning resource. Sharing is explicit; the
mere existence of a Source-, platform-, or installation-level reference does
not grant an endpoint access. An adapter slot can bind only a compatible
authentication type and permitted scope.

The existing Step 26 `auth_token_env_var` remains a compatibility reference
until a later guarded migration adopts the global secret identity. Phase 3
does not create a second secret value or silently rewrite Alert history.

### 12.3 Resolution and Failure

```text
worker receives stable SourceEndpoint ID
        ↓
load endpoint and versioned adapter configuration
        ↓
load exact required bindings
        ├─ missing binding
        │      → make no provider request
        │      → record authentication/configuration failure
        └─ binding present
                ↓
        resolve through configured backend immediately before use
                ├─ backend unavailable
                ├─ reference missing
                ├─ permission denied
                ├─ expired/disabled
                └─ invalid value
                       → make no provider request
                       → never fall back to unauthenticated access
                ↓
        supply value only to the adapter request boundary
                ↓
        discard the in-memory reference as soon as practical
```

Python does not promise physical zeroing of immutable strings. The
implementation minimizes lifetime, copies, subprocess exposure, and process
scope rather than making an unverifiable memory-erasure claim.

Secret states exposed operationally:

```text
configured
missing
invalid
expired
rotation_required
disabled
```

### 12.4 Non-Leakage and Rotation

Secret values never appear in:

```text
PostgreSQL values or ordinary metadata
stored URLs
logs, errors, tracebacks, or metrics labels
telemetry attributes
Celery arguments/results
Redis keys/values
API responses or HTML
form redisplay or exports
source control
Artifact, rejection, or IngestionRun provenance
rate-limit identities
command-line arguments
```

Query-string credentials require an adapter-declared provider necessity. The
URL is constructed only at the request boundary, logs retain a redacted base
URL, and redirects never forward a credential to another origin.

The UI displays backend, masked reference identity, state, and last resolution
time, never the value. Rotation changes the backend value or explicit binding
without changing Source, SourceEndpoint, adapter, rate, or ingestion history.
A failed replacement does not silently destroy a still-valid old binding;
explicit revocation remains authoritative.

## 13. Hierarchical Rate-Limit Contract

Configuration inheritance and runtime enforcement are separate. A more
specific configured value may replace an inherited default within hard
bounds, but every runtime request must receive permission from every
applicable bucket.

### 13.1 Modes, Scopes, and Values

Modes:

```text
provider_defined
robots_aware
conservative
custom
```

Scopes:

```text
installation
adapter
platform
credential
origin
source
endpoint
```

Policy fields:

```text
requests_per_period
period_seconds
burst_size
max_concurrency
minimum_request_spacing_seconds
poll_interval_seconds
daily_request_budget
retry_base_seconds
retry_max_seconds
retry_jitter_percent
exhaustion_action
validity interval
```

Initial constrained values:

| Field | Constraint | Default |
|---|---:|---:|
| Requests per period | `1..10000` | `6` |
| Period seconds | `1..86400` | `60` |
| Burst size | `1..100` | `1` |
| Endpoint concurrency | exactly `1` | `1` |
| Origin concurrency | `1..16` | `2` |
| Poll interval | minimum `60` seconds | `900` seconds |
| Retry base | `1..86400` seconds | `60` seconds |
| Retry maximum | base through `604800` seconds | `86400` seconds |
| Retry jitter | `0..50` percent | `20` percent |
| Daily request budget | null or positive integer | null |
| Exhaustion action | `delay`, `disable`, `operational_exception` | `delay` |

Adapter defaults may be stricter. No adapter, endpoint, Source, manual poll,
or operator action may exceed an installation hard maximum.

`delay` preserves lifecycle state and schedules the next eligible attempt.
`disable` is an explicit policy-selected system-actor transition to the
endpoint's disabled lifecycle state and appends the same actor, reason, and
before/after history required of an operator transition. It is never an
implicit side effect of an exhausted bucket. `operational_exception` appends
an acquisition-scoped operational record for authorized review; it is not a
Calendar administrative exception and grants no bypass.

### 13.2 Persistence

```text
acquisition_rate_limit_policies
  versioned constrained values and validity

acquisition_rate_limit_bindings
  exact installation/adapter/platform/credential/origin/source/endpoint scope
  actor, reason, and immutable change history

acquisition_rate_limit_buckets
  durable window, request, daily-budget, provider-reset, and blocked state

acquisition_rate_limit_reservations
  one expiring reservation per outbound request and IngestionRun

acquisition_rate_limit_observations
  append-only status, Retry-After, provider quota/reset, and robots evidence
```

Scope checks require only the resource appropriate to the binding. Credential
buckets reference `secret_reference_id`, never a secret value. Multiple
endpoints explicitly sharing a provider account therefore share its quota
without revealing the credential.

### 13.3 Atomic Enforcement

PostgreSQL is authoritative. Redis may accelerate lookup but Redis loss,
restart, or eviction cannot permit a prohibited request.

```text
begin short transaction
        ↓
lock all applicable buckets in deterministic order
        ↓
expire abandoned reservations
        ↓
evaluate provider/robots holds and every installation, adapter, platform,
credential, origin, Source, and endpoint bucket
        ├─ any denial
        │      → create no partial reservation
        │      → persist next eligible time and controlling policy
        └─ all permit
                ↓
        atomically reserve one request against every bucket
commit
        ↓
perform request outside the transaction
        ↓
begin short finalization transaction
release concurrency reservation
update counters and provider observations
commit
```

Reservation expiry recovers crashed workers. Stable lock ordering prevents
deadlock. A request is sent only after the reservation transaction commits.
PostgreSQL or required-policy unavailability fails closed and sends nothing.

### 13.4 Precedence and HTTP Behavior

The strictest applicable limit wins:

```text
provider Retry-After or reset
robots access/crawl policy
credential/platform quota
origin bucket
adapter and installation policy
Source and endpoint policy
```

HTTP 429 honors valid Retry-After. A missing/malformed value uses conservative
exponential backoff with jitter. HTTP 503 honors Retry-After when present.
Jitter changes scheduling only and never shortens `blocked_until`.

A delayed/rate-limited request does not count as a parsing, structural,
security, or Source-health failure. Manual polls use the same buckets and
cannot bypass them.

### 13.5 Operator UI

The effective-policy view shows:

```text
installation and adapter defaults
platform and credential quota
origin policy
Source policy
endpoint override
provider/robots temporary hold
effective controlling policy and next eligible time
```

Authorized controls may create Source/endpoint policies and configure bounded
rate, burst, concurrency, polling, retry, and budget values with actor and
reason. They cannot ignore Retry-After or robots restrictions, exceed hard
limits, edit live counters, bypass a manual poll, or reuse a secret outside
its binding.

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

Lifecycle, verification, health, and temporary gates are separate controlled
dimensions. The existing lifecycle field remains:

```text
SourceEndpoint.status = active | disabled
```

Verification state:

```text
never_checked
verified
verified_empty
verification_failed
```

Health state:

```text
unknown
healthy
degraded
failing
stale
```

Temporary operational gates:

```text
rate_limited
authentication_failed
adapter_unavailable
security_blocked
```

Transport, rate, authentication, parsing, extraction, security, and
downstream-enrichment failures remain separate reason dimensions with
history. One rejected payload appends a security event; it does not silently
rewrite lifecycle or general health. Policy may place an endpoint under a
`security_blocked` gate after a defined security condition. A valid empty
official feed may be `verified_empty` and `healthy`.

## 16. Worker and Transaction Boundary

The acquisition worker:

1. claims a durable endpoint lease;
2. commits the logical run and configuration snapshot;
3. resolves rate and secret policy;
4. validates outbound destination and reserves every applicable rate bucket;
5. retrieves outside database transactions into bounded isolated staging;
6. invokes the credential-free inspection sandbox;
7. deletes rejected bytes before appending rejection metadata;
8. establishes atomic visibility for the fully accepted Artifact tree;
9. normalizes accepted content through the owning adapter;
10. commits Document/Calendar ownership changes in bounded transactions;
11. triggers idempotent downstream work;
12. finalizes health, rate, metrics, reservations, and lease state.

No database transaction remains open during network, browser, model, media,
signature-scanning, archive extraction, or other untrusted/long-running I/O.
The inspection sandbox has no acquisition secret, database, Redis, or
canonical-storage authority.

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

### 17.1 Migration and Cutover

The architecture review read-only preflight found 143 SourceEndpoints:

```text
141  feed / rss  / feed_parser
  2  feed / atom / feed_parser
  0  IMAP, POP3, FTP, or SFTP acquisition methods
  0  duplicate endpoint URLs
  0  URLs containing user-info credentials
  0  URLs with recognized secret query keys
```

Five metadata documents contain secret-like words only inside existing
`healthcheck_error` or `healthcheck_parse_warning` strings; no top-level
secret-named metadata key was found. Migration must scan without printing
values, apply the redaction policy prospectively, and block rather than guess
if an actual credential-like value is discovered. It never converts error
text into a secret reference.

Migration and activation rules:

```text
do not fabricate historical Artifact rows for existing Documents
do not infer old exact formats from endpoint envelopes
do not auto-extract secrets from URLs, metadata, errors, or environment
retain historical catalog references
install global secret identities before acquisition bindings
install detector, scanner, sandbox, and deletion path before Artifact intake
activate no new adapter until its exact capability/security proofs pass
keep existing RSS/Atom compatibility until the shared path proves parity
cut over through a versioned worker/configuration gate
never advertise deletion-first protection for work that bypasses it
```

Existing accepted Document text is not retroactively treated as a suspicious
file merely because no historical Artifact/signature evidence exists.
Prospective Artifact acceptance begins only at the explicit cutover.

Downgrade is lossless-only. It refuses while any Phase 3 Artifact payload,
Artifact version, observation, rejection, adapter configuration, secret
binding, rate policy/state, lease, signature release, or dependent custom
catalog mapping exists. Seeded catalog additions may be removed only when
unreferenced and exactly equal to the migration-owned seed. Downgrade never
deletes accepted bytes or audit history merely to make schema removal pass.

## 18. Required Proof Matrix

Phase 3 implementation must directly prove:

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
43. The inspection sandbox has no network, secret, database, Redis, or
    canonical-storage authority.
44. Sandbox crash, timeout, invalid output, or policy violation deletes staged
    bytes and cannot produce a preview or accepted Artifact.
45. Outbound validation rejects forbidden address ranges and revalidates DNS
    and every redirect destination.
46. GNI-owned internal services require exact installation registration and
    cannot become an arbitrary endpoint bypass.
47. Declared and streaming byte limits terminate acquisition and delete
    partial staged content.
48. Accepted promotion re-verifies hashes and provides atomic visibility
    across filesystem and object-storage backends.
49. Adapter secret slots, authentication types, and binding scopes are exact
    and database-enforced.
50. Missing/invalid secret resolution sends no request and never falls back
    to unauthenticated access.
51. Rate permission reserves every applicable bucket atomically; denial
    consumes no partial reservation.
52. Rate-authority or PostgreSQL unavailability sends no request.
53. Lifecycle, verification, health, temporary gates, and failure reasons
    remain separate.
54. Migration does not fabricate historical Artifacts, formats, or secret
    references from ambiguous legacy data.
55. Stored URL, error, metadata, telemetry, and redirect handling cannot leak
    secret values.
56. Installation starts only from the exact reviewed, repository-pinned
    signature/catalog bootstrap release.
57. Every later authority release is treated as untrusted input and cannot
    replace the active release unless verification and regression pass.
58. A known payload hash never bypasses staging, scanning, detection, parsing,
    or complete-tree acceptance.
59. Identical reacquisition appends an observation, while changed accepted
    bytes append an immutable forward same-resource Artifact version.
60. Downgrade refuses Phase 3-owned state and never deletes accepted bytes or
    audit history to make schema removal succeed.

## 19. Implementation Sequence

```text
Phase 3.1 architecture frozen
        ↓
corrective/additive catalog and Artifact migrations
        ↓
signature release importer and deletion-first detector
        ↓
inspection sandbox, mandatory scanner, and outbound egress guard
        ↓
durable lease, adapter registry, global secret references, rate policy
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

This freeze governs the architecture and mandatory proof obligations. It does
not claim that its migrations, worker, adapters, security runtime, or UI have
been implemented or operationally frozen.

## 20. Formal Architecture Freeze Review

**Review date:** 2026-07-28
**Outcome:** PASS — ARCHITECTURE FROZEN
**Implementation status:** NOT STARTED

The formal review found and corrected these freeze blockers:

1. secret references and hierarchical rate limits lacked implementable
   persistence, resolution, atomicity, failure, and non-leakage contracts;
2. mount-isolated staging did not isolate vulnerable inspection processes;
3. outbound retrieval lacked a non-bypassable SSRF, redirect, and internal
   service boundary;
4. accepted promotion did not define atomic visibility across filesystem and
   object-storage backends;
5. Artifact storage did not distinguish immutable payload bytes, logical
   resource versions, and repeated acquisition observations;
6. signature-catalog bootstrap trust and later untrusted authority updates
   were incomplete;
7. lifecycle, verification, health, and temporary operational gates were
   conflated; and
8. migration cutover, legacy preflight, and lossless downgrade were
   underspecified.

The corrected architecture now defines a credential-free inspection sandbox,
mandatory scanning, bounded retrieval, deletion-first failure handling,
content-addressed payloads, immutable Artifact history, append-only
observations, global secret identities with acquisition bindings,
PostgreSQL-authoritative all-bucket rate reservations, explicit health
dimensions, and a prospective cutover.

Read-only legacy preflight recorded:

```text
SourceEndpoints                                      143
distinct endpoint URLs                              143
active endpoints                                    118
feed/rss/feed_parser tuples                         141
feed/atom/feed_parser tuples                          2
IMAP/POP3/FTP/SFTP methods                            0
URLs containing user-info credentials                0
URLs containing recognized secret query keys          0
metadata rows with top-level secret-named keys         0
metadata documents with secret-like health text        5
```

The five metadata matches are four `healthcheck_error` strings and one
`healthcheck_parse_warning` string. Migration must scan and sanitize these
without printing their values and must block rather than infer a secret
reference. No historical Artifact, detected format, or secret binding may be
fabricated from the legacy rows.

Freeze is conditioned on all 60 proofs in Section 18. Implementation must
demonstrate those proofs directly before the Phase 3 implementation freeze;
this documentation review does not substitute for runtime, migration,
security-isolation, or live operational evidence.
