# GNI Global Foundation Audit

## Governing principle

GNI is a global news-intelligence platform.

Canonical data models answer:

> What can GNI represent?

Operator configuration answers:

> What does this installation or coverage profile monitor?

East Asia, politics, particular languages, particular outlets, polling priorities,
and alert thresholds are configuration choices. They must not constrain the
canonical universe.

## GFA-A — Source and endpoint normalization

A Source is the publisher, organization, institution, or person responsible for
the information.

`sources.source_type` answers: **What is this publisher/source?**

It must not describe retrieval technology.

One Source may have many endpoints. Each endpoint has four independent
dimensions:

```text
source_endpoints.endpoint_type
source_endpoints.endpoint_format
source_endpoints.acquisition_method
source_endpoints.platform
```

They answer:

1. What kind of access point is this?
2. What format does it deliver?
3. How does GNI retrieve it?
4. Which named platform hosts it, if any?

These become canonical database-backed vocabularies:

```text
source_types
endpoint_types
endpoint_formats
acquisition_methods
platforms
```

Stable slugs are API/configuration identifiers.

Attributes such as state ownership, editorial orientation, reliability, or
political alignment are not `source_type`; those are overlapping
characteristics and belong in separate metadata/classifications.

## GFA-B — Global language foundation

GNI must accept arbitrary valid language/script combinations.

The system will distinguish:

```text
original language
script where relevant
source default language
translation source language
translation target language
operator UI language
```

Language identifiers will be BCP 47-compatible and must not assume an East
Asia-only supported-language set.

## GFA-C — Canonical entity-type taxonomy

Actual entities remain open-ended, but `entity_type` should be canonical and
hierarchical.

The taxonomy will cover globally useful classes such as:

```text
person
organization
government organization
legislature
court
election authority
military
law enforcement
company
political party
international organization
NGO
university
think tank
labor union
media organization
place/facility
legal instrument
court case
treaty
technology/product
software
AI model
weapon system
vehicle
aircraft
vessel
spacecraft
program/initiative
other
```

## GFA-D — Semantic document type vs content format

**Status: FROZEN**

These are independent:

```text
document_type  = what kind of information is this?
content_format = what medium/container is it in?
```

Examples:

```text
court_decision + pdf
speech + video
news_report + html
analysis + audio
official_statement + plain_text
dataset + csv
```

The existing `document_types` catalog remains semantic. The canonical
`content_formats` catalog describes the medium/container. The
implementation and migration policy are defined by
`GFA_D_DOCUMENT_CONTENT_FORMAT_SEPARATION.md`.

## GFA-E — Coverage Profiles

Coverage Profiles turn the global canonical universe into a user's configured
news-intelligence deployment.

Profiles will eventually configure:

```text
enabled geographies
enabled topics
enabled source types
enabled sources
enabled languages
translation targets
document types
content formats
polling priorities
alert thresholds
saved monitoring rules
```

Example:

```text
Profile: East Asia Politics
Geographies: South Korea, Taiwan, Japan, China, North Korea, Philippines
Topics: Politics, Law & Judiciary, War & Security, Foreign Affairs
Translation target: English
```

A second user could create `European Energy Markets` without changing the
canonical schema.

## Migration sequence

```text
GFA-A  Source and endpoint normalization
GFA-B  Global language foundation
GFA-C  Entity-type taxonomy
GFA-D  Document content-format separation
GFA-E  Coverage Profiles
```

Each migration must be independently testable and preserve existing history.

Step 23B.2 structured metadata classification waits until GFA-A through GFA-D
are stable because those dimensions directly affect ingestion and
classification semantics.
