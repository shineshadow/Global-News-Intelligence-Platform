# GFA-D — Semantic Document Type and Content-Format Separation

**Status:** FROZEN  
**Alembic revision:** `e73f0a4b6c12`  
**Date:** 2026-07-26

## 1. Purpose

GFA-D freezes three independent document dimensions:

```text
document_type
    What kind of information is this?

ingestion_format
    What envelope or serialization delivered it to GNI?

content_format
    What medium or container represents the document content?
```

Examples:

```text
court_decision + rss + pdf
speech + json + video
news_report + rss + html
analysis + json + audio
official_statement + email_message + plain_text
dataset + html + csv
```

The existing `document_types` and `document_type_assignments` remain
the canonical semantic classification model. GFA-D does not replace,
duplicate, or infer semantic type from content format.

## 2. Boundaries

The frozen ownership model is:

```text
sources.source_type
    publisher or source organization kind

source_endpoints.endpoint_type
    kind of access point

source_endpoints.endpoint_format
documents.ingestion_format
    delivered envelope or serialization

documents.content_format
document_versions.content_format
    content representation

document_type_assignments
    semantic information kind
```

RSS, Atom, and JSON Feed are ingestion formats. They are deliberately
absent from `content_formats`: a feed entry may describe an HTML
article, link to a PDF, or enclose audio or video.

## 3. Standards Authority

IANA's Media Types registry is the authority for observed media-type
identifiers:

```text
https://www.iana.org/assignments/media-types/media-types.xhtml
```

RFC 6838 defines media-type registration procedures. RFC 6839 and RFC
7303 establish structured-syntax suffix behavior such as `+json` and
`+xml`. GNI maps registered or observed media types into a smaller,
stable operational catalog; it does not claim that its slugs replace
IANA identifiers.

The exact observed media type remains in ingestion metadata when
available:

```text
metadata.content_media_type
metadata.content_media_type_source
```

## 4. Canonical Content-Format Catalog

The canonical table is:

```text
content_formats

id
slug
name
description
is_active
metadata
created_at
updated_at
```

The initial catalog contains 21 extensible entries:

```text
unknown
html
plain_text
markdown
pdf
word_processing
presentation
spreadsheet
csv
tsv
json
xml
email_message
calendar
image
audio
video
archive
ebook
binary
other
```

`unknown` means no defensible representation evidence was available.
`other` means evidence identified a representation that the current
catalog does not yet model. These meanings must not be collapsed.

Catalog metadata records media family, representative IANA media
types, file extensions, seed set, and catalog version. The catalog is
open to reviewed additions and is not a schema-level closed world.

## 5. Persistence and History

Both current and historical representations carry a required,
reference-backed format:

```text
documents.content_format
    FK → content_formats.slug

document_versions.content_format
    FK → content_formats.slug
```

The field describes the primary normalized representation stored by
that row. Supplemental links or enclosures remain metadata. If GNI
later retrieves an enclosure or linked resource as a separately
managed representation, that resource receives its own content-format
fact rather than silently replacing the format of the feed-derived
text row.

A historical snapshot copies the current format before an updated
representation is stored. `content_format` participates in changed
field detection so a representation change remains visible in version
history.

Historical representation identity is:

```text
UNIQUE (document_id, content_hash, content_format)
```

The same normalized content hash may therefore be preserved under two
different representations without conflating their history.

The current-document index is:

```text
ix_documents_content_format_published_at
    (content_format, published_at)
```

## 6. Detection Policy

New feed ingestion uses the strongest item-level evidence:

```text
entry content media type
    preferred

entry summary media type
    fallback

no item-level media type
    unknown
```

Normalization:

```text
exact registered media type
    maps to its reviewed canonical format

*+json
    json

*+xml
    xml

image/*
    image

audio/*
    audio

video/*
    video

unrecognized nonempty media type
    other

missing or blank media type
    unknown
```

The endpoint format, URL extension, document title, and semantic
document type are not sufficient evidence and must not be used as
automatic substitutes.

An enclosure media type also does not override the media type of the
stored `content_original` or `summary_original`. This prevents
supplemental images, attachments, or podcast enclosures from
reclassifying the normalized text representation before those
resources are actually ingested.

## 7. Migration Policy

GFA-A created `documents.ingestion_format` as the canonical historical
replacement for the legacy `documents.source_type` compatibility
copy.

Before destructive cleanup, GFA-D verifies:

```text
documents.source_type = documents.ingestion_format
for every existing document
```

Any mismatch aborts the transaction. After the check:

```text
existing documents.content_format          = unknown
existing document_versions.content_format  = unknown
```

This backfill is intentional. A feed envelope does not prove the
medium of its entries, and historical rows do not retain sufficient
item-level media-type evidence for a deterministic reconstruction.

GFA-D then removes:

```text
documents.source_type
ix_documents_source_type
ix_documents_source_type_published_at
```

No provenance is lost because the guarded value remains in the
required, reference-backed `documents.ingestion_format`.

## 8. Downgrade Policy

Downgrade is allowed only when it is lossless:

```text
all current content formats are unknown
all historical content formats are unknown
no custom content-format catalog rows exist
```

Otherwise downgrade aborts. A permitted downgrade reconstructs
`documents.source_type` from `ingestion_format`, restores its original
nullability/default/indexes, and removes the GFA-D catalog and columns.

## 9. Direct Tests

The candidate directly proves:

```text
missing media type maps to unknown
unrecognized media type maps to other
exact HTML, plain-text, PDF, and tabular mappings
+json and +xml structured-syntax mappings
image, audio, and video family mappings
RSS and Atom are absent from content formats
RSS summary media type produces HTML content format
Atom content media type produces HTML content format
ingestion and content formats persist independently
format-only changes preserve the prior historical representation
current and historical content formats are required FKs
legacy provenance mismatch is rejected
legacy document source column and indexes are absent
meaningful formats block downgrade
```

## 10. Verification Results

Validation used isolated PostgreSQL 17.10:

```text
legacy mismatch upgrade guard                         passed
honest unknown historical backfill                    passed
clean upgrade                                         passed
meaningful-format downgrade guard                     passed
clean downgrade and re-upgrade                        passed
GFA-A post-compatibility verification SQL             passed
GFA-D verification SQL                                passed
seeded content formats                                    21
acquisition-envelope leakage                               0
invalid content-format references                           0
legacy document source columns                              0
legacy document source indexes                              0
focused and affected tests                          43 passed
complete repository suite                          127 passed
Alembic model/schema drift operations                       0
schema-only snapshot regenerated                          yes
```

## 11. Formal Freeze Review

The formal review examined:

```text
semantic document-type independence
source, endpoint, ingestion, and content ownership boundaries
IANA media-type authority and structured-syntax normalization
unknown versus other semantics
catalog extensibility and reference integrity
current and historical representation persistence
format-only version history
legacy provenance equality guard
honest historical unknown backfill
lossless-downgrade guard
consumer and fixture migration completeness
verification SQL and schema snapshot
focused and repository-wide regression results
Alembic model/schema agreement
```

The review found and corrected one documentation ambiguity: enclosure
or link media types must not override the representation actually
stored by the document row. No code, schema, migration-safety,
history, standards, or test blocker remained.

GFA-D separates semantic type, acquisition envelope, and content
representation without inventing historical format facts or
discarding legacy provenance.

No GFA-D freeze blockers remain.

## 12. Frozen Invariants

```text
semantic document type is independent of medium/container
ingestion format is independent of content format
source and endpoint types do not determine document type
RSS, Atom, and JSON Feed are not content formats
content format describes the normalized representation actually stored
unknown means evidence missing; other means known but not yet modeled
observed media type and evidence source remain in metadata
current and historical content formats are required canonical references
format-only changes preserve the prior representation in history
legacy document source_type is absent
historical acquisition provenance remains in ingestion_format
unsafe legacy mismatches block upgrade
meaningful formats and custom catalog rows block downgrade
```

## 13. GFA-D — FROZEN
