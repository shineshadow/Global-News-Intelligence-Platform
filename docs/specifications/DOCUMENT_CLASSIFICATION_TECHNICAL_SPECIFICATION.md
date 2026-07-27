# Unified Document Classification System

**Project:** Global News Intelligence Platform  
**Document:** `DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md`  
**Version:** 0.1  
**Date:** July 23, 2026  
**Status:** Companion Technical Specification  
**Formal System Name:** Unified Document Classification System  
**Internal Namespace:** `classification`

---

## 1. Purpose

The Unified Document Classification System defines how the platform turns a normalized document into structured intelligence that can be filtered, monitored, searched, clustered, and correlated at scale.

The subsystem exists because a chronological stream of thousands or millions of documents is not operationally useful unless documents can be classified consistently across multiple independent dimensions.

The system must answer at least five separate questions for every document:

```text
Where is this document about?
What is this document about?
Which people, organizations, companies, agencies, military units, and places are involved?
What kind of document is it?
How was each classification produced and how trustworthy is it?
```

The canonical classification dimensions are:

1. geography,
2. hierarchical topics,
3. entities,
4. document type,
5. classification provenance and confidence.

The system is multi-label. A document may have many geographies, topics, and entities simultaneously.

---

## 2. Relationship to the Master Platform

This specification is authoritative for detailed classification behavior. The Master Technical Specification remains authoritative for platform-wide architectural decisions.

The same canonical classification records must be reusable by:

```text
Documents
Stories
Observed Events
Intelligence Calendar Events
Monitors
Search
Alerts
Research workflows
AI question answering
Analytics
```

No subsystem may maintain a competing topic, entity, geography, or document-type vocabulary when the canonical classification system can be reused.

---

## 3. Core Architectural Invariants

### 3.1 Source Geography Is Not Document Geography

`Source.country` identifies the home country, jurisdiction, or primary organizational context of the publisher or source.

It must never be treated as a substitute for the geographies discussed by a document.

Example:

```text
Source:
The Washington Post

Source country:
United States

Document:
Japan and the Philippines expand defense cooperation amid pressure from China.

Document geographies:
Japan
Philippines
China
```

A document may therefore contain zero, one, or many geography assignments independently of the source's country.

### 3.2 Geography Is Not a Topic

Topics answer:

```text
What is this content about?
```

Geographies answer:

```text
Which countries, regions, jurisdictions, or places does this content concern?
```

A classification such as `South Korea` must not be stored as a topic merely to make filtering convenient.

### 3.3 Multiple Topics Are Allowed

A single document may be simultaneously classified as:

```text
Politics
Elections
Election Administration
Law & Judiciary
```

Topic assignment is not mutually exclusive.

### 3.4 Topic Hierarchy Is Not Limited to Two Levels

Although the UI may use the terms topic and subtopic, the data model must support arbitrary hierarchy depth.

Example:

```text
War & Security
└── Military
    └── Naval Activity
        └── Naval Procurement
```

### 3.5 Source Type Is Not Document Type

Examples:

```text
source_type = government
endpoint_type = rss
document_type = press_release
```

```text
source_type = court
endpoint_type = website
document_type = court_decision
```

The acquisition mechanism and publisher type must not determine the document's semantic type.

### 3.6 Classification Is Auditable

Every classification produced by automation should be traceable to:

```text
classification method
classifier/model version
taxonomy version
confidence
classification time
supporting rule or evidence when practical
```

### 3.7 Classification Is Reprocessable

Historical documents must be capable of being reclassified when:

- the taxonomy changes,
- entity aliases improve,
- classifiers improve,
- thresholds change,
- errors are discovered.

Reclassification must not require rewriting original source content.

---

## 4. Classification Dimensions

## 4.1 Geography

Geography classifications may include:

```text
country
territory
region
subregion
state/province
city
maritime area
international organization region
custom intelligence region
```

Initial high-priority canonical geographies include:

```text
United States
South Korea
Japan
Taiwan
China
North Korea
Philippines
Indo-Pacific
```

A document may have more than one geography and each relationship may carry confidence and role.

Possible geography relationship roles:

```text
primary_subject
secondary_subject
location_of_event
actor_origin
target_location
mentioned
publisher_context
```

`publisher_context` should normally be derived from the Source and should not automatically count as substantive document geography.

### 4.1.1 Geography Versus Location Entities

Canonical geographies and location entities are related but not interchangeable.

```text
Geography:
South Korea
Seoul
Yellow Sea

Location entity:
Seoul Central District Court
Camp Humphreys
National Assembly Building
Taereung Country Club
```

Geographies provide normalized spatial filtering and jurisdictional context. Location entities identify named places, venues, facilities, installations, or buildings that participate in a story or event. A location entity may reference one or more canonical geographies.

---

## 4.2 Hierarchical Topics

The topic system is a canonical, hierarchical taxonomy.

The authoritative root layer is **Canonical Topic Taxonomy v1.0** and is frozen at 23 roots. The canonical vocabulary and taxonomy-version policy are maintained in `CANONICAL_TOPIC_TAXONOMY.md`.

Canonical roots:

```text
Politics
Law & Judiciary
War & Security
Foreign Affairs
Economy
Business
Technology
Energy
Health
Science
Environment
Society
Crime
Immigration
Media
Education
Religion
Arts, Culture & Entertainment
Disasters & Emergencies
Labor & Employment
Sports
Weather
Lifestyle & Human Interest
```

The root layer must not be expanded, removed, merged, split, or semantically repurposed without an explicit major taxonomy-version change and migration/reclassification review. Child and descendant topics remain intentionally extensible.

More specialized branches may include:

```text
Politics
└── Elections
    ├── Election Administration
    ├── Election Integrity
    ├── Campaigns
    ├── Polling
    ├── Election Law
    └── Certification / Recounts

Technology
├── Artificial Intelligence
│   ├── Foundation Models
│   ├── AI Chips
│   ├── AI Regulation
│   └── AI Export Controls
├── Semiconductors
│   ├── Fabrication
│   ├── Equipment
│   ├── Materials
│   └── Export Controls
└── Cybersecurity
    ├── Cyber Espionage
    ├── Ransomware
    ├── Vulnerabilities
    ├── Threat Intelligence
    └── Critical Infrastructure

War & Security
└── Military
    ├── Military Exercises
    ├── Procurement
    ├── Naval Activity
    ├── Air Operations
    ├── Missile Activity
    ├── Space
    └── Nuclear
```

The taxonomy should remain extensible without database migrations for every new child or descendant category.

Taxonomy version `1.0` freezes only the canonical root layer. Backward-compatible child-topic additions and refinements may advance minor taxonomy versions; root-layer or materially breaking semantic changes require a major taxonomy version.

---

## 4.3 Entities

Entity types include at minimum:

```text
person
organization
company
government
agency
political_party
military_unit
international_organization
location
court
legislative_body
media_organization
technology
weapons_system
program
law_or_regulation
```

Aliases must support multilingual and spelling variation.

Example:

```text
Canonical entity:
National Election Commission of South Korea

Aliases:
NEC
National Election Commission
중앙선거관리위원회
선관위
```

Entity resolution should distinguish canonical identity from raw extracted mention text.

Document-to-entity relationships should support roles such as:

```text
subject
speaker
author
participant
host
target
issuer
plaintiff
defendant
judge
agency
company_subject
military_actor
location
mentioned
```

---

## 4.4 Document Type

A canonical document-type taxonomy should distinguish the semantic form of the content from its source and acquisition method.

Initial document types should include:

```text
news_report
breaking_news
analysis
opinion
editorial
investigative_report
government_release
press_release
official_statement
speech
transcript
court_decision
court_filing
legal_notice
legislation
bill
regulation
rulemaking
public_notice
procurement_notice
tender
sanctions_notice
regulatory_filing
corporate_filing
research_paper
think_tank_report
policy_brief
statistical_release
calendar_notice
event_announcement
video
social_post
newsletter
podcast_episode
other
```

The initial implementation may assign one primary document type, while the schema should permit future secondary type relationships if required.

---

## 5. Canonical Taxonomy Model

Recommended `topics` fields:

```text
id
parent_id
slug
name
native_name
description
depth
sort_order
taxonomy_version
is_active
created_at
updated_at
```

Rules:

- `slug` is stable and machine-friendly.
- `parent_id` provides arbitrary hierarchy depth.
- topics should normally be retired with `is_active = false` rather than deleted.
- taxonomy edits that materially change meaning must be versioned.
- aliases or redirects should preserve old slugs where practical.

---

## 6. Geography Model

Recommended `geographies` fields:

```text
id
parent_id
slug
name
native_name
geography_type
iso_code
country_code
region_code
is_active
metadata
created_at
updated_at
```

Possible `geography_type` values:

```text
country
territory
region
subregion
state_province
city
maritime_area
custom_region
```

Recommended `document_geographies` fields:

```text
document_id
geography_id
confidence
relationship_role
classification_method
classifier_version
taxonomy_version
classification_run_id
is_manual_override
created_at
updated_at
```

A unique constraint should prevent duplicate active relationships for the same document, geography, and classification context where appropriate.

---

## 7. Topic Relationship Model

Recommended `document_topics` fields:

```text
document_id
topic_id
confidence
relationship_role
classification_method
classifier_version
taxonomy_version
classification_run_id
is_manual_override
created_at
updated_at
```

Possible `relationship_role` values:

```text
primary
secondary
contextual
mentioned
```

The exact UI-visible thresholds remain benchmark decisions.

---

## 8. Entity Relationship Model

Recommended `entities` fields:

```text
id
canonical_name
canonical_name_native
is_active
metadata
created_at
updated_at
```

Entity type and geography are separate, typed semantic assertions:

```text
entity_type_assignments
    entity_id
    entity_type_id
    assignment method, confidence, validity, evidence, provenance

entity_geographies
    entity_id
    geography_id
    relationship_type
    assignment method, confidence, validity, evidence, provenance
```

The entity row must not collapse these many-valued, historical facts
into free-text type or jurisdiction fields.

Recommended `entity_aliases` fields:

```text
id
entity_id
alias
language
script
alias_type
is_preferred
normalized_alias
created_at
updated_at
```

Recommended `document_entities` fields:

```text
document_id
entity_id
mention_text
entity_role
confidence
classification_method
classifier_version
classification_run_id
is_manual_override
created_at
updated_at
```

The system should retain the raw mention where useful for audit and model evaluation.

---

## 9. Document Type Model

Recommended `document_types` fields:

```text
id
slug
name
description
parent_id
is_active
created_at
updated_at
```

Recommended `document_type_assignments` fields:

```text
document_id
document_type_id
is_primary
confidence
classification_method
classifier_version
classification_run_id
is_manual_override
created_at
updated_at
```

---

## 10. Classification Methods and Provenance

Canonical classification methods should include:

```text
manual
deterministic_rule
source_default
endpoint_default
metadata_mapping
local_classifier
local_llm
openai
imported
backfill
```

Each automated classification should retain enough provenance to answer:

```text
What assigned this classification?
Which model or rule version was used?
Which taxonomy version was active?
What confidence did it produce?
When did classification occur?
Was the result later manually overridden?
```

Recommended `classification_runs` fields:

```text
id
document_id
pipeline_version
taxonomy_version
started_at
completed_at
status
language
classifier_versions
ruleset_version
llm_provider
llm_model
input_hash
output_hash
error
metadata
```

`classifier_versions` may initially be JSONB to permit multiple specialized classifiers in one run.

---

## 11. Confidence Model

Confidence should use a normalized range:

```text
0.00–1.00
```

Example conceptual interpretation:

```text
0.80–1.00  strong classification
0.60–0.79  secondary / reviewable classification
0.00–0.59  weak classification, normally hidden from default UI filtering
```

These are not permanent hard-coded thresholds. Final thresholds must be determined through benchmarking by classification dimension and language.

Different dimensions may require different thresholds.

For example:

```text
geography threshold != topic threshold != entity-resolution threshold
```

Manual assignments may be treated as authoritative unless explicitly revoked.

---

## 12. Classification Precedence and Fusion

The platform should combine cheap deterministic evidence with AI rather than forcing every item through a large model.

Recommended processing order:

```text
Source / endpoint defaults
        ↓
Structured metadata mappings
        ↓
Deterministic rules
        ↓
Dictionary / alias matching
        ↓
Local specialized classifier
        ↓
Local LLM when necessary
        ↓
OpenAI escalation for selected difficult cases
        ↓
Confidence fusion / conflict resolution
```

Examples:

```text
Endpoint:
CISA Cybersecurity Advisories

Strong default topic:
Cybersecurity
```

```text
Source:
South Korean Constitutional Court

Strong default geography:
South Korea

Likely document-type family:
Court / legal material
```

Defaults are priors, not proof that every document belongs exclusively to that category.

---

## 13. Classification Processing Workflow

Recommended document pipeline:

```text
NORMALIZED DOCUMENT
        │
        ▼
DETERMINISTIC ENRICHMENT
        │
        ├── source defaults
        ├── endpoint defaults
        ├── structured metadata
        └── rule matches
        │
        ▼
UNIFIED DOCUMENT CLASSIFICATION
        │
        ├── geography classification
        ├── topic classification
        ├── entity extraction + resolution
        └── document-type classification
        │
        ▼
CLASSIFICATION PERSISTENCE
        │
        ├── confidence
        ├── provenance
        ├── classifier version
        └── taxonomy version
        │
        ▼
MONITOR / FILTER EVALUATION
        │
        ▼
FUTURE EVENT DETECTION
        │
        ▼
TRANSLATION AS REQUIRED
        │
        ▼
EMBEDDINGS
        │
        ▼
STORY CANDIDATE NARROWING
        │
        ▼
STORY CLUSTERING
```

Some deterministic monitor rules may run before AI classification for low-latency alerts. Classified monitor rules may run again after enrichment.

---

## 14. Multilingual Classification

The classification system must support at minimum:

```text
English
Korean
Japanese
Traditional Chinese
Simplified Chinese
Filipino
```

Requirements:

- canonical topics remain language-independent identifiers,
- aliases may be multilingual,
- original mention text must be preserved where useful,
- entity resolution must work across scripts,
- translated text must not replace original text as classification evidence,
- classification may use original text, translated text, or both, with provenance retained.

Cross-language entity examples:

```text
Lee Jae-myung
이재명
李在明
```

must resolve to the same canonical entity when identity is unambiguous.

---

## 15. Manual Review and Overrides

Operators must be able to:

- add a classification,
- remove a classification,
- change the primary topic,
- change document type,
- correct entity resolution,
- change geography,
- mark AI output incorrect,
- request reclassification.

Manual overrides must not destroy the prior automated result.

The platform should preserve:

```text
previous automated classification
manual change
author/user
reason when provided
timestamp
```

---

## 16. Monitoring Integration

Monitor rules may combine classification dimensions with deterministic criteria.

Example:

```text
Geography:
South Korea

Topic:
Elections

Subtopic:
Election Administration

Entity:
National Election Commission

Keywords:
A-WEB OR Dominion OR Smartmatic

Time:
Last 24 hours
```

Supported classification-aware monitor criteria should include:

```text
geography
topic branch
specific topic
entity
entity role
document type
classification confidence
source
source group
source type
language
```

Monitor evaluation should permit minimum confidence thresholds.

---

## 17. Search and Filter Integration

The Documents UI and search APIs should support combinable filtering by:

```text
Geography
Topic
Subtopic / taxonomy branch
Entity
Entity role
Document type
Source
Source type
Language
Publication time
Retrieval time
Keyword / full-text query
Semantic query
Classification confidence
```

Example:

```text
Geography = South Korea
Topic = Elections
Subtopic = Election Administration
Entity = National Election Commission
Document Type = News Report
Language = Korean + English
Date = Last 30 days
```

Saved filters/views should eventually preserve these combinations.

### 17.1 Step 24 Shared Matching Contract

Step 24 upgrades the existing `/web/documents` News Feed and defines the
matching contract later consumed by persistent monitors.

The contract must support:

```text
coverage profile
canonical document geography, with explicit descendant inclusion
canonical topic, with explicit descendant inclusion
canonical entity
entity role
semantic document type
content format
source
source type
language
minimum classification confidence
time window
keywords and phrases
```

Unset criteria are unrestricted. Multiple values inside one dimension combine
with OR; constrained dimensions combine with AND. Coverage-profile scope is
applied first and additional News Feed criteria further narrow that scope.

Hierarchy expansion is explicit and read-time. Filtering must not materialize
inferred ancestor or descendant classification assertions. Classification
criteria match active assertions only, and a confidence threshold applies to
the assertion satisfying that criterion.

The current News Feed `Country / Region` input filters `Source.country`, which
is publisher home jurisdiction. Step 24 must replace that behavior with
canonical `document_geographies` matching. Publisher jurisdiction may remain
available as a separately named source filter, but it must never masquerade as
document subject geography.

Relationship filters should use `EXISTS`-style predicates or an equivalent
duplicate-safe query plan so multi-label classifications do not corrupt result
counts or pagination.

The Step 24 implementation must expose one typed criteria object and one
matching/query service rather than independently recreating semantics in the
web route, API, and future monitor worker.

### 17.2 Step 24, Step 25, and Step 26 Boundary

```text
Step 24
Build and validate a transient News Feed filter
        ↓
Step 25
Persist equivalent criteria as an active Monitor
        ↓
Step 26
Notify when new documents match
```

Step 25 owns rule lifecycle, evaluation runs, idempotent matches, activation,
and continuous reevaluation after enrichment. Step 26 owns notification
delivery and delivery history. Step 24 does not create hidden saved monitors or
send alerts.

---

## 18. Classification-Assisted Story Clustering

Classification should reduce story-clustering search space and improve precision.

Candidate narrowing may use:

```text
geography overlap
topic overlap
entity overlap
time proximity
document type
calendar-event prior
```

Then embeddings and other semantic signals perform finer comparison.

Example:

```text
New document
      ↓
South Korea + Elections + NEC
      ↓
Retrieve plausible recent story candidates
      ↓
Embedding / claim comparison
      ↓
Assign or create story
```

Classification is a weighted prior. It must not force documents into the same story when semantic evidence disagrees.

---

## 19. Story, Event, and Calendar Reuse

Stories, observed Events, and Intelligence Calendar Events should reuse the same canonical topic, entity, and geography records.

Recommended relationship tables may include:

```text
story_topics
story_entities
story_geographies

event_topics
event_entities
event_geographies

intelligence_calendar_event_topics
intelligence_calendar_event_entities
intelligence_calendar_event_geographies
```

Relationship tables may carry subsystem-specific confidence and roles while referencing the same canonical records.

---

## 20. API Requirements

Classification APIs should eventually support:

```text
GET  /api/v1/topics
GET  /api/v1/topics/tree
GET  /api/v1/geographies
GET  /api/v1/entities
GET  /api/v1/document-types

GET  /api/v1/documents/{id}/classifications
POST /api/v1/documents/{id}/classifications/reclassify
POST /api/v1/documents/{id}/topics
POST /api/v1/documents/{id}/geographies
POST /api/v1/documents/{id}/entities
POST /api/v1/documents/{id}/document-type
```

Exact routes may change during API design, but the capability must exist.

Manual modification routes require authorization and audit logging.

---

## 21. Worker Design

Potential worker queues/tasks:

```text
classification-worker
entity-resolution-worker
classification-backfill-worker
taxonomy-maintenance-worker
```

Responsibilities:

### classification-worker

```text
classify new documents
persist topic/geography/document-type assignments
record provenance
route difficult work through LLM Router
```

### entity-resolution-worker

```text
extract mentions
resolve aliases
create unresolved-entity review items
persist entity roles/confidence
```

### classification-backfill-worker

```text
reprocess historical documents
migrate classifications to new taxonomy versions
throttle workload
preserve prior runs
```

---

## 22. Failure Handling

Classification failure must not block durable ingestion of the original document.

Possible states:

```text
pending
running
succeeded
partial
failed
needs_review
superseded
```

A document should remain searchable by raw metadata even when classification is delayed or fails.

Retries should be idempotent.

---

## 23. Taxonomy Governance

Taxonomy maintenance should support:

```text
add topic
rename display label
add alias
move branch
merge topic
retire topic
split topic
version taxonomy
backfill affected documents
```

Potentially destructive taxonomy changes must preserve migration history.

A topic should not be silently repurposed to mean something materially different.

---

## 24. Benchmark Requirements

The permanent benchmark corpus should measure classification performance across source types and languages.

Required measurements include:

```text
topic precision / recall / F1
hierarchical topic accuracy
geography precision / recall
multi-geography accuracy
entity extraction precision / recall
entity resolution accuracy
alias resolution accuracy
document-type accuracy
confidence calibration
false-positive rate
cross-language consistency
JSON/schema reliability
latency
GPU utilization
cost per 1,000 documents
```

Benchmark slices should include:

```text
news
government
court
military
business
technology
cybersecurity
YouTube transcripts
short documents
long documents
multilingual documents
```

---

## 25. Migration and Backfill Requirements

Initial deployment should be additive.

The migration should:

1. create canonical classification tables,
2. preserve existing document fields,
3. populate deterministic defaults where safe,
4. backfill source-country only as publisher context, not document geography,
5. classify historical documents in controlled batches,
6. compare old and new filtering behavior,
7. retire legacy fields only after compatibility review.

No migration should infer substantive document geography solely from `Source.country`.

---

## 26. UI Requirements

Document list and detail screens should expose classification without overwhelming the operator.

Recommended document-list filters:

```text
Geography
Topic
Entity
Document Type
Source
Language
Time
Search
```

Recommended document-detail sections:

```text
Classification Summary
Geographies
Topics
Entities
Document Type
Classification Confidence
Classification Provenance
Manual Corrections
Classification History
```

Low-confidence classifications may be visually distinguished and optionally hidden by default.

---

## 27. Implementation Roadmap

### Classification Phase 1 — Canonical Data Model — Implemented

Add:

```text
topics hierarchy
geographies
document_geographies
document_topics
entity relationship metadata
document_types
document_type_assignments
classification_runs
```

### Classification Phase 2 — Deterministic Classification — Implemented

Add:

```text
source defaults
endpoint defaults
metadata mappings
keyword/rule classification
alias matching
```

### Classification Phase 3A — Step 24 Filtering — Next

Add:

```text
classification-aware document filters
shared typed matching criteria
News Feed canonical geography/topic/entity/type filters
coverage-profile scope
duplicate-safe pagination and counts
```

### Classification Phase 3B — Step 25 Monitoring

Add:

```text
persistent monitor rules
classification-aware evaluation
activation and lifecycle
idempotent monitor matches
saved monitor views
```

### Classification Phase 3C — Step 26 Alerts

Add:

```text
alert events
ntfy delivery
delivery attempts and status
```

### Classification Phase 4 — Local AI

Add:

```text
multilingual topic classifier
geography classifier
entity extraction/resolution
document-type classifier
confidence calibration
```

### Classification Phase 5 — Reprocessing and Governance

Add:

```text
taxonomy versioning
classification backfill
manual review
manual overrides
classifier comparison
```

### Classification Phase 6 — Intelligence Integration

Add:

```text
classification-assisted story clustering
calendar priors
observed-event classification
research/AI question integration
```

---

## 28. Decisions Already Made

- Classification is multi-dimensional.
- Geography and topic are separate dimensions.
- Source geography and document geography are separate concepts.
- Documents may have multiple geographies, topics, and entities.
- Topic hierarchy may have arbitrary depth.
- Source type and document type are separate concepts.
- Classification confidence and provenance must be retained.
- Classifier and taxonomy versions must be retained.
- Manual overrides must preserve prior automated output.
- Classification must be reprocessable.
- Canonical topics, entities, geographies, and document types must be reusable across the platform.
- Deterministic and metadata-based classification should be used before expensive AI where practical.
- Local AI is preferred; OpenAI is an escalation layer.
- Classification failure must not prevent durable document ingestion.

---

## 29. Decisions Requiring Benchmarking

- Exact confidence thresholds by dimension and language.
- Exact topic classifier model.
- Exact geography classifier model.
- Exact entity extraction and resolution models.
- Exact document-type classifier.
- Multi-label decision thresholds.
- Hierarchical-loss or parent/child inference strategy.
- Confidence-fusion strategy when rules and AI disagree.
- Reclassification cadence after model upgrades.
- Candidate-narrowing weights for story clustering.

---

## 30. Final Architecture Summary

```text
SOURCE + ENDPOINT METADATA
          │
          ▼
  NORMALIZED DOCUMENT
          │
          ▼
DETERMINISTIC ENRICHMENT
          │
          ▼
UNIFIED CLASSIFICATION
  │       │       │       │
  ▼       ▼       ▼       ▼
Geography Topics Entities Document Type
  │       │       │       │
  └───────┴───────┴───────┘
          │
          ▼
CONFIDENCE + PROVENANCE
          │
          ▼
MONITORING / SEARCH / FILTERS
          │
          ▼
EMBEDDINGS + STORY CANDIDATE NARROWING
          │
          ▼
STORY / EVENT / CALENDAR INTELLIGENCE
```

The Unified Document Classification System is the structural layer that turns a large archive of collected documents into an operational intelligence corpus.
