# Publisher Workspace Technical Specification

**Project:** Global News Intelligence Platform  
**Document:** `PUBLISHER_WORKSPACE_TECHNICAL_SPECIFICATION.md`  
**Version:** 0.2  
**Status:** Companion Technical Specification  
**Formal Subsystem Name:** Publisher Workspace and Story Builder  
**UI / Functional Name:** Publisher Workspace  
**Internal / Database Namespace:** `publisher_workspace`

---

## 1. Purpose

The Publisher Workspace is the human research, evidence-selection, citation, media-management, and research-export layer of the Global News Intelligence Platform.

It sits downstream of acquisition, classification, Story Intelligence, Intelligence Calendar correlation, search, alerts, transcripts, and AI-assisted analysis.

Its purpose is not to replace the intelligence pipeline and not to become a full content-management system or word processor. Its purpose is to turn machine-organized intelligence into a structured, auditable research package that a human publisher can use to create articles, social posts, scripts, reports, and other editorial outputs.

The normal flow is:

```text
Source Acquisition
        ↓
Normalized Documents
        ↓
Unified Classification
        ↓
Story Intelligence
        ↓
Calendar / Event Correlation
        ↓
Search / Monitoring / Alerts
        ↓
PUBLISHER WORKSPACE
        ↓
Research Project
        ↓
Documents / Clips / Quotes / Facts / Media / Timeline
        ↓
Source Comparison / Verification
        ↓
Research Package
        ↓
External Editor or Lightweight Drafting Pane
        ↓
Final Article / Social Post / Script / Publication
```

The platform gathers, organizes, translates, compares, and preserves the evidence.

The human operator remains responsible for deciding which sources to trust, which evidence to use, how to frame the story, and what the final published work says.

---

## 2. Relationship to Other Subsystems

The Publisher Workspace is a consumer of canonical intelligence produced by other platform subsystems. It must not create incompatible copies of their domain models.

### 2.1 Source Acquisition

`SOURCE_ACQUISITION_TECHNICAL_SPECIFICATION.md` owns acquisition behavior for RSS, web pages, generated feeds, changedetection, browser automation, YouTube discovery, and other source types.

Publisher Workspace may display acquisition provenance but does not own source retrieval.

### 2.2 Unified Document Classification

`DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md` owns canonical:

```text
geographies
topics / topic hierarchy
entities / aliases
document types
classification confidence
classification provenance
classifier versions
taxonomy versions
```

Publisher Workspace must reuse those canonical records for filtering, display, research selection, and export metadata.

It must not treat `Source.country` as document geography and must not create a second topic, geography, entity, or document-type taxonomy.

### 2.3 Story Intelligence

`STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md` owns machine-generated Story objects, document-to-story relationships, new developments, claims, clustering, source comparison intelligence, and Story lifecycle.

Publisher Workspace consumes Story Intelligence as research context.

Conceptually:

```text
STORY INTELLIGENCE
Machine understanding of the evolving Story
        ↓
PUBLISHER WORKSPACE
Human research, evidence selection, verification, and editorial preparation
```

### 2.4 Intelligence Calendar

`INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md` owns expected future events, event validation, scheduling, pre-event monitoring, Calendar-to-document relationships, and scheduled-versus-observed outcomes.

A Research Project may be linked to one or more Intelligence Calendar Events and may consume their related Documents, Stories, entities, geographies, and timelines.

### 2.5 AI Routing

All AI-assisted research operations must use the provider-agnostic mechanisms defined by `AI_ROUTING_TECHNICAL_SPECIFICATION.md`.

Publisher Workspace must never call OpenAI, Qwen, Llama, Mistral, or another model provider directly.

### 2.6 Implementation-Level Documents

Implementation details belong in:

```text
ARCHITECTURE.md
IMPLEMENTATION.md
DATABASE_SCHEMA_SPECIFICATION.md
API_SPECIFICATION.md
WORKER_DESIGN_SPECIFICATION.md
MIGRATION_PLAN.md
BENCHMARK_PROCEDURES.md
UI_IMPLEMENTATION_NOTES.md
```

Those documents implement this specification and must not redefine its domain boundaries.

---

## 3. Architectural Invariants

1. Original Documents and Document Versions remain immutable source evidence.
2. Research clips, notes, summaries, and AI outputs must never silently overwrite original evidence.
3. Every reusable evidence item must preserve provenance to the exact source Document and, where practical, the exact `document_version_id` from which it was captured.
4. Human-authored notes must remain visually and structurally distinct from source material and AI-generated analysis.
5. AI-generated research artifacts must remain distinct from original evidence and retain AI provenance.
6. Canonical Geography, Topic, Entity, and Document Type records must come from the Unified Document Classification subsystem.
7. `Source.country` identifies publisher/organizational jurisdiction and must not be substituted for document geography.
8. Story Intelligence may recommend or summarize evidence, but humans control what is selected for a Research Project.
9. The workspace must support evidence from multiple sources, languages, formats, and Stories.
10. Citations and source traceability are first-class data, not text generated only at export time.
11. Media discovery and media publication rights are separate concerns.
12. Unknown licensing status must never be silently treated as permission to publish.
13. Research exports should be reproducible and should carry a machine-readable manifest.
14. Exporting or drafting content must not modify the source Documents that supplied the evidence.
15. The initial system is a research and preparation workspace, not a Drupal-like CMS and not a replacement for a full external editor.
16. Research Projects and evidence selections must survive service restarts and remain durable in PostgreSQL.
17. Important user actions should be auditable.
18. Where Story or classification intelligence changes later, historical research selections must still retain the context and evidence that existed when the operator selected them.

---

## 4. Core Publishing Workflow

The complete workflow is:

```text
Breaking / Search / Intelligence Calendar / Stories / Alerts
                         │
                         ▼
                 Open Story Workspace
                         │
                         ▼
             Review Related Documents
                         │
                         ▼
       Filter by Classification + Provenance
                         │
                         ▼
             Select Documents and Media
                         │
                         ▼
               Create Research Project
                         │
                         ▼
       Clip Facts / Quotes / Claims / Images
                         │
                         ▼
            Compare and Verify Sources
                         │
                         ▼
             Build Timeline and Notes
                         │
                         ▼
              Review Media Usage Rights
                         │
                         ▼
               Export Research Package
                         │
                         ▼
          External Editor / Drafting Pane
                         │
                         ▼
             Record Published Outputs
```

---

## 5. Entry Points

A Publisher Workspace research flow may begin from:

```text
Breaking
Stories
Search
Intelligence Calendar
Alerts
Geographies
Topics
Entities
Documents
YouTube
Monitors
Saved Views
```

Example:

```text
Intelligence Calendar
    ↓
Presidential Address
    ↓
Related Stories / Documents / Livestreams
    ↓
Create Research Project
```

Example:

```text
Search
    ↓
Geography: South Korea
Topic: Elections
Entity: National Election Commission
    ↓
Matching Stories and Documents
    ↓
Create Research Project
```

---

## 6. Story Workspace

When an operator opens a Story, the Publisher Workspace should present the canonical Story Intelligence view together with research actions.

Example:

```text
PRESIDENTIAL ADDRESS TO THE NATION

Documents: 84
Sources: 31
Languages: 5
Geographies: 3
New developments: 9
Official sources: 4
Video sources: 7
Claims: 22
```

### 6.1 Classification-Aware Filtering

Documents should support combinable filtering by:

```text
Geography
Topic / Topic hierarchy
Entity
Entity role
Document type
Language
Source
Source type
Publication time
Retrieval time
Classification confidence
Official versus media
Original reporting versus aggregation
Source authority
Document importance
New-development status
Agreement / contradiction state
Political/editorial orientation when available
```

`Geography` replaces the older ambiguous `Country` filter for document subject matter.

A publisher may still filter by a source organization's jurisdiction separately through Source metadata.

### 6.2 Document Decision Information

Each document row should expose useful research information such as:

```text
Source
Headline
Publication time
Language
Document type
Primary geographies
Primary topics
Key entities
Source authority
Original reporting indicator
Importance
New-information status
Agreement / contradiction status
Story relationship confidence
```

Low-confidence classifications should be visually distinguishable from confirmed or manually corrected classifications.

### 6.3 Story Intelligence Context

Where available, Story Workspace should surface:

```text
new developments
claim/evidence relationships
source diversity
source independence
contradictions
corrections
story timeline
cross-language reporting
related Calendar Events
related observed Events
```

These are machine intelligence aids. They do not automatically become evidence selected for publication.

---

## 7. Research Projects

A Research Project is a durable human-curated workspace containing selected source evidence and operator work product.

Example:

```text
Research Project:
South Korea Election Commission Investigation — July 2026
```

### 7.1 Candidate Project States

```text
collecting
researching
drafting
fact_checking
ready
published
archived
```

Final state semantics may be adjusted during implementation, but transitions should be explicit and auditable.

### 7.2 Relationships

A project may relate to:

```text
one or more Stories
one or more Intelligence Calendar Events
one or more observed Events
many Documents
many clips
many notes
many assets
many citations
many AI research results
many exports
many published outputs
```

### 7.3 Project Workspace Tabs

Recommended tabs:

```text
Overview
Documents
Clips
Quotes
Facts / Claims
Media
Videos / Transcripts
Timeline
Notes
Sources
Comparisons
AI Analysis
Citations
Exports
Published Outputs
History
```

---

## 8. Selecting Documents

Every eligible Document should offer actions such as:

```text
[Add to Research Project]
[Create Clip]
[Save Quote]
[Add Media]
[Open Source]
[Compare]
```

Examples of selected evidence may include:

- an official government announcement,
- a wire-service report,
- a Korean-language article,
- a Japanese or Chinese article,
- a YouTube transcript,
- a court decision,
- legislation,
- a regulatory filing,
- a research paper,
- a relevant image,
- a public notice,
- a military statement.

Document Type must come from the canonical classification subsystem rather than being inferred independently by the Publisher Workspace.

---

## 9. Research Clips

Original Documents remain unchanged. Operators create smaller reusable evidence objects called **research clips**.

### 9.1 Clip Types

Candidate clip types:

```text
fact
quote
paragraph
transcript
claim
timeline_item
statistic
official_statement
contradiction
correction
context
summary_reference
```

The final controlled vocabulary should be versioned rather than scattered through application code.

### 9.2 Text Clip

```text
Document:
Official announcement

Document Version:
Version 3

Selected text:
The president will address the nation at 9:00 p.m. Eastern.

Clip type:
fact
```

### 9.3 Quote Clip

```text
Speaker:
Named Entity → Donald Trump

Quote:
“We will address the challenges facing our country.”

Source Document:
White House transcript

Timestamp:
00:08:44
```

### 9.4 Transcript Clip

```text
Video:
Official livestream

Transcript Segment:
00:08:44–00:09:31

Transcript:
...
```

Where transcript segment records exist, a clip should reference them directly instead of duplicating their identity only as free text.

### 9.5 Research Note

```text
This is the first announced national address since...
```

A Research Note is operator-authored commentary and must remain explicitly labeled as such.

---

## 10. Evidence Provenance

Every fact, quote, paragraph, image, transcript segment, or other selected evidence should retain enough information to reconstruct where it came from.

At minimum, evidence should preserve or be able to resolve:

```text
source_id
source name
source_endpoint_id when relevant
document_id
document_version_id when relevant
document title
canonical URL
author
published_at
retrieved_at
original language
original text
translated text when used
transcript_segment_id when relevant
video timestamp when relevant
content hash
clip creator
clip creation time
```

### 10.1 Why Document Version Matters

A publisher may edit or replace an article after the platform retrieved it.

A clip must therefore be able to answer:

```text
Which version did the operator actually see and select?
```

The preferred relationship is:

```text
Research Clip
    ↓
Document Version
    ↓
Document
    ↓
Source Endpoint
    ↓
Source
```

Where the clip is derived from a transcript:

```text
Research Clip
    ↓
Transcript Segment
    ↓
Transcript
    ↓
YouTube Video / Media Document
    ↓
Source
```

### 10.2 Classification Snapshot

A research clip may optionally preserve a lightweight snapshot of relevant classifications at selection time, especially when those classifications materially influenced editorial research.

Canonical classification records remain authoritative; snapshots exist only to preserve historical research context.

---

## 11. Claims, Facts, and Verification

Publisher Workspace should not assume that an extracted statement is a confirmed fact.

Useful research statuses may include:

```text
reported_claim
confirmed_fact
official_statement
corroborated
contradicted
corrected
unverified
operator_note
```

Story Intelligence may provide claim/evidence analysis, but Publisher Workspace should permit operator review and explicit evidence selection.

A future evidence matrix may show:

```text
Claim
Supporting Documents
Contradicting Documents
Official Evidence
Source Independence
Confidence
Operator Status
```

Operator judgment must remain distinguishable from model-generated confidence.

---

## 12. AI-Assisted Research

AI should help the operator analyze selected evidence without silently creating unsupported material.

Candidate actions:

```text
Summarize selected Documents
Compare selected Sources
Extract candidate facts
Extract direct quotes
Build a timeline
Translate selected passages
Identify contradictions
Identify unsupported claims
Show information unique to each source
Separate official statements from media interpretation
Find the earliest known source
Compare cross-language framing
Explain differences between Document Versions
Generate research questions
Suggest missing evidence categories
```

### 12.1 AI Router Requirement

Every model-based operation must be submitted through the AI Router.

Conceptual flow:

```text
Publisher Workspace action
        ↓
Research service
        ↓
AI Router task request
        ↓
Deterministic path / Local model / OpenAI escalation
        ↓
Schema validation
        ↓
AI research artifact
```

### 12.2 AI Provenance

AI-generated research artifacts should retain, directly or through `ai_jobs` / `ai_results`:

```text
ai_job_id
provider
model
prompt/template version
schema version
input Document IDs
input Document Version IDs when relevant
input hash
output hash
created_at
latency
usage / estimated cost
escalation chain
```

### 12.3 Separation of AI Output and Evidence

An AI summary, extracted fact candidate, or comparison is not itself primary source evidence.

The UI must visually distinguish:

```text
Original Source Evidence
Operator Notes / Decisions
AI-Generated Analysis
```

### 12.4 Example Source Comparison

```text
AGREEMENT

All selected sources agree the address begins at 9:00 p.m.

UNIQUE TO OFFICIAL SOURCE

The address will be delivered from the Oval Office.

UNIQUE TO WIRE REPORT

Two administration officials say foreign policy will be discussed.

CONFLICT

One outlet reports 8:00 p.m.; the official schedule says 9:00 p.m.
```

Every finding should link back to the supporting Documents and, where possible, the exact evidence spans.

---

## 13. Media Tray

Research Projects should include a Media Tray.

Candidate media types:

```text
Official photographs
Article images
YouTube thumbnails
Video stills
Government graphics
Charts
Screenshots
Uploaded images
Maps
PDF figures
Public-domain graphics
```

### 13.1 Media Provenance

Each asset should retain, where available:

```text
source_id
document_id
document_version_id
asset type
original URL
local/object-storage path
caption
photographer / creator
publication
publication date
retrieval date
copyright owner
license
attribution requirement
usage status
usage notes
content hash
```

### 13.2 Usage Status

Candidate controlled values:

```text
unknown
public_domain
licensed
creative_commons
editorial_use
attribution_required
approved
restricted
do_not_publish
```

`unknown` must not be interpreted as permission to publish.

### 13.3 Rights Principle

Finding or storing an image does not itself establish legal permission to republish it.

The platform should favor media with known publication rights such as:

- official government images with clear usage terms,
- public-domain material,
- properly licensed wire-service material,
- Creative Commons material with compatible terms,
- media created or uploaded by the operator,
- properly attributed media where the license permits reuse.

Rights metadata is an editorial aid, not an automated legal determination.

---

## 14. Political / Editorial Orientation

Political or editorial orientation must not be represented as a Topic.

Where the platform later supports source-orientation analysis, it should be modeled as a separate source-profile dimension.

Potential future attributes:

```text
editorial_orientation
orientation_confidence
orientation_method
orientation_version
source_ownership
state_media_status
```

Publisher Workspace may filter or display these attributes when available, but it must not independently assign or maintain a competing orientation model.

---

## 15. Citations

Citations are first-class research objects.

The workspace should support:

```text
Copy With Citation
Copy Quote With Citation
Export Markdown Footnotes
Export Source List
Export Citation Manifest
```

### 15.1 Citation Provenance

A citation should be resolvable to:

```text
research_project_id
research_clip_id when relevant
document_id
document_version_id when relevant
source_id
source title / document title
source organization
author
canonical URL
published_at
retrieved_at
accessed/exported date if needed
```

### 15.2 Citation Rendering

Citation styles should be treated as presentation rules over preserved provenance, not as the authoritative evidence store.

Future supported styles may include:

```text
Markdown footnote
Plain source list
HTML citation
Internal newsroom citation
Custom publisher format
```

---

## 16. Timelines

Research Projects should support timelines assembled from:

```text
Story developments
Calendar Events
observed Events
Document publication times
operator-created timeline items
selected claims/facts
source corrections
schedule changes
```

Every automatically derived timeline item must preserve provenance.

The operator should be able to distinguish:

```text
scheduled event time
observed real-world event time
publication time
retrieval time
research note time
```

---

## 17. Research Exports

The platform does not initially need to become a complete word processor.

A Research Project should support:

```text
Copy Selected Clips
Copy With Citations
Export Markdown
Export Plain Text
Export HTML
Export JSON Manifest
Export Research Package
Send to Writing Folder
```

### 17.1 Primary Export Format

Markdown should be the preferred human-readable export format because it works well with source control, plain-text tools, external editors, and automated conversion.

### 17.2 Research Package

Example:

```text
presidential-address-2026-08-03/
│
├── draft.md
├── research-notes.md
├── selected-clips.md
├── sources.md
├── citations.md
├── timeline.md
├── manifest.json
│
└── assets/
    ├── official-photo.jpg
    ├── speech-thumbnail.jpg
    └── chart.png
```

### 17.3 Manifest

`manifest.json` should make an export reproducible and machine-readable.

Candidate fields:

```text
project_id
project_title
related_story_ids
related_calendar_event_ids
related_observed_event_ids
exported_at
export_format_version
platform_version
taxonomy_versions
classification_versions
documents
clips
citations
assets
ai_results
timeline_items
checksums
```

The manifest should not expose credentials or sensitive internal configuration.

---

## 18. Watch-Folder and External Editor Integration

Because the platform is self-hosted, Research Projects may support configured export destinations.

Example:

```text
/home/operator/news-drafts/
```

Possible destinations:

```text
Local filesystem
Samba share
NFS share
Nextcloud folder
Syncthing folder
Git repository
```

Export destinations must be configured by administrators and should not accept arbitrary filesystem paths from untrusted browser input.

The platform should not require any specific external editor.

Possible editors include:

```text
VS Code
Obsidian
Typora
Zettlr
Kate
LibreOffice
Microsoft Word after conversion
```

---

## 19. Optional Lightweight Drafting Pane

A future version may provide a lightweight drafting pane beside research evidence.

```text
┌─────────────────────────────┬──────────────────────────────┐
│ RESEARCH EVIDENCE           │ DRAFT                        │
│                             │                              │
│ Official announcement       │ Draft text...                │
│ Wire report                 │                              │
│ Transcript quote            │                              │
│ Image                       │                              │
└─────────────────────────────┴──────────────────────────────┘
```

Potential actions:

```text
Insert clip
Insert quote with citation
Insert fact with citation
Insert timeline item
Insert media placeholder
```

The initial implementation should remain lightweight. The platform should not attempt to compete with a full desktop publishing or word-processing application.

---

## 20. Published Outputs

The system should reserve a relationship between Research Projects and works eventually produced from them.

This does not require the platform to publish directly.

Candidate output types:

```text
article
social_post
thread
video_script
newsletter
research_report
briefing
other
```

Potential metadata:

```text
id
research_project_id
output_type
title
platform
published_url
external_identifier
published_at
notes
created_at
```

This enables historical traceability:

```text
Research Project
       ↓
Produced Article
       ↓
Produced X Post
       ↓
Produced Video Script
```

---

## 21. Recommended Database Model

The Publisher Workspace should initially reserve the following PostgreSQL entities:

```text
research_projects
research_project_stories
research_project_calendar_events
research_project_events
research_project_documents
research_clips
research_notes
research_project_assets
research_citations
research_ai_artifacts
research_timeline_items
research_exports
research_project_outputs
research_project_history
```

Implementation-level column definitions belong in `DATABASE_SCHEMA_SPECIFICATION.md` and migrations.

### 21.1 `research_projects`

Candidate fields:

```text
id
uuid
title
description
status
created_by_user_id
created_at
updated_at
archived_at
metadata
```

Story, Calendar, and Event relationships should use normalized relationship tables rather than single `related_story_id` fields if multiple relationships are required.

### 21.2 `research_project_documents`

Candidate fields:

```text
research_project_id
document_id
document_version_id
selected_by_user_id
selected_at
selection_reason
sort_order
metadata
```

### 21.3 `research_clips`

Candidate fields:

```text
id
uuid
research_project_id
document_id
document_version_id
transcript_segment_id
clip_type
content_original
content_translated
character_start
character_end
video_start_time
video_end_time
speaker_entity_id
classification_snapshot
content_hash
created_by_user_id
created_at
updated_at
metadata
```

### 21.4 `research_notes`

Candidate fields:

```text
id
research_project_id
note_type
content
created_by_user_id
created_at
updated_at
```

Research notes must be clearly marked as operator-authored content.

### 21.5 `research_project_assets`

Candidate fields:

```text
id
research_project_id
document_id
document_version_id
asset_type
original_url
storage_path
caption
credit
creator
copyright_owner
license
attribution_requirement
usage_status
usage_notes
content_hash
created_at
metadata
```

### 21.6 `research_citations`

Candidate fields:

```text
id
research_project_id
research_clip_id
document_id
document_version_id
citation_style
citation_text
created_at
metadata
```

The source-of-truth citation metadata should remain resolvable through relational references even if a rendered citation string is stored for convenience.

### 21.7 `research_ai_artifacts`

Candidate fields:

```text
id
research_project_id
ai_job_id
artifact_type
created_at
metadata
```

Detailed model provenance should remain owned by the AI subsystem.

### 21.8 `research_timeline_items`

Candidate fields:

```text
id
research_project_id
timestamp
precision
item_type
content
document_id
document_version_id
calendar_event_id
observed_event_id
created_by_user_id
created_at
metadata
```

### 21.9 `research_exports`

Candidate fields:

```text
id
research_project_id
format
export_path
manifest
content_hash
created_by_user_id
created_at
```

### 21.10 `research_project_outputs`

Candidate fields:

```text
id
research_project_id
output_type
title
platform
published_url
external_identifier
published_at
notes
created_at
```

### 21.11 `research_project_history`

Purpose:

Preserve important project lifecycle and operator actions.

Candidate events:

```text
PROJECT_CREATED
STATUS_CHANGED
DOCUMENT_ADDED
DOCUMENT_REMOVED
CLIP_CREATED
CLIP_UPDATED
CLIP_REMOVED
NOTE_CREATED
ASSET_ADDED
USAGE_STATUS_CHANGED
AI_ANALYSIS_CREATED
EXPORT_CREATED
OUTPUT_RECORDED
PROJECT_ARCHIVED
```

---

## 22. API Requirements

Potential API resources:

```text
GET    /api/v1/research-projects
POST   /api/v1/research-projects
GET    /api/v1/research-projects/{id}
PATCH  /api/v1/research-projects/{id}

POST   /api/v1/research-projects/{id}/documents
DELETE /api/v1/research-projects/{id}/documents/{document_id}

GET    /api/v1/research-projects/{id}/clips
POST   /api/v1/research-projects/{id}/clips
PATCH  /api/v1/research-clips/{id}
DELETE /api/v1/research-clips/{id}

GET    /api/v1/research-projects/{id}/assets
POST   /api/v1/research-projects/{id}/assets
PATCH  /api/v1/research-assets/{id}

GET    /api/v1/research-projects/{id}/citations
POST   /api/v1/research-projects/{id}/citations

POST   /api/v1/research-projects/{id}/compare
POST   /api/v1/research-projects/{id}/timeline
POST   /api/v1/research-projects/{id}/ai-analysis

POST   /api/v1/research-projects/{id}/exports
GET    /api/v1/research-projects/{id}/exports

POST   /api/v1/research-projects/{id}/outputs
GET    /api/v1/research-projects/{id}/history
```

Web UI server-rendered workflows may call the service layer directly and do not need to route browser rendering through these APIs.

Detailed request/response contracts belong in `API_SPECIFICATION.md`.

---

## 23. Service Boundaries

Potential application services:

```text
ResearchProjectService
ResearchClipService
ResearchCitationService
ResearchMediaService
ResearchComparisonService
ResearchTimelineService
ResearchExportService
ResearchOutputService
```

Service rules:

- business logic belongs in services, not Jinja templates or route handlers,
- services must enforce provenance requirements,
- services must validate that selected Documents and Document Versions exist,
- services must not mutate source Documents,
- AI operations delegate to the AI Router,
- export services must sanitize filesystem paths and filenames,
- rights metadata changes should be auditable.

---

## 24. Worker Design

Most Publisher Workspace CRUD operations should be synchronous application operations.

Long-running or expensive work may use background workers.

Candidate tasks:

```text
research-ai-worker
research-export-worker
research-media-worker
research-backfill-worker
```

### 24.1 Research AI Worker

Responsibilities may include:

```text
source comparison
multi-document summarization
candidate fact extraction
contradiction analysis
timeline assistance
cross-language comparison
```

The worker submits model work through the AI Router.

### 24.2 Export Worker

Useful for large research packages containing many Documents or binary assets.

Responsibilities:

```text
render Markdown / HTML
build manifest
copy approved assets
calculate checksums
write archive/package
record export result
```

### 24.3 Media Worker

Potential future responsibilities:

```text
retrieve approved remote asset copies
extract image metadata
calculate hashes
generate thumbnails
inspect dimensions / format
```

It must not infer publication rights merely because retrieval succeeded.

Detailed queue ownership, idempotency, retries, and failure policies belong in `WORKER_DESIGN_SPECIFICATION.md`.

---

## 25. UI Architecture

Publisher Workspace should use the platform's established Web UI stack:

```text
FastAPI
Jinja2
HTMX
Alpine.js
Tabler
Tabulator
```

Potential charts may use Apache ECharts where analytical visualization is useful.

The workspace should remain server-authoritative and progressively enhanced.

### 25.1 Main Navigation

Recommended top-level navigation:

```text
Publisher Workspace
```

with:

```text
Publisher Workspace
├── Projects
├── Research Queue
├── Saved Documents
├── Clips
├── Quotes
├── Media
├── Timelines
├── Source Comparisons
├── Exports
└── Archive
```

The exact navigation hierarchy may evolve, but the Publisher Workspace should be treated as a first-class operator workflow rather than an incidental saved-items screen.

### 25.2 Research Project Layout

A desktop-oriented layout may use:

```text
┌───────────────────────┬───────────────────────────────┐
│ PROJECT / FILTERS     │ EVIDENCE / WORK AREA          │
│                       │                               │
│ Story                 │ Documents                     │
│ Geography             │ Clips                         │
│ Topics                │ Quotes                        │
│ Entities              │ Timeline                      │
│ Document type         │ AI comparison                 │
│ Sources               │ Media                         │
│                       │                               │
└───────────────────────┴───────────────────────────────┘
```

### 25.3 Provenance UX

Every clip, quote, claim, and media item should provide a direct path back to its source evidence.

Useful actions:

```text
Open original Document
Open Document Version
Open publisher URL
Show source metadata
Show classification
Show Story context
Show AI provenance
```

---

## 26. Search and Filtering

Publisher Workspace should consume the platform-wide search/filter semantics.

Combinable filters should include:

```text
geography
topic / descendant topic
entity
entity role
document type
source
source type
language
published date
retrieved date
classification confidence
source authority
story
Calendar Event
observed Event
new-development status
text query
semantic query
```

Saved research views may be added later.

---

## 27. Security and Permissions

Future multi-user operation should distinguish permissions such as:

```text
view research projects
create project
edit own project
edit shared project
manage media rights metadata
run AI analysis
export project
record published output
archive project
administrator access
```

Filesystem exports must be constrained to configured destinations.

Research Projects may eventually require private/shared/team visibility settings.

Authentication and authorization architecture remain platform-wide concerns.

---

## 28. Audit and History

Important research actions should be auditable, particularly where they affect editorial evidence or publication rights.

Audit candidates include:

```text
project status changes
manual fact/claim status changes
clip edits
clip deletion
citation edits
asset usage-status changes
AI analysis creation
export generation
published-output recording
```

Audit records should identify the user and timestamp.

---

## 29. Failure Handling

The workspace must explicitly handle:

```text
source Document unavailable
Document Version missing
source URL later dead
media retrieval failure
media license unknown
AI provider failure
AI schema failure
export destination unavailable
filesystem permission denied
asset copy failure
partial export
stale Story intelligence
classification changed after clip selection
```

Failure handling principles:

- existing research evidence must remain readable when an external source disappears,
- export failures must not corrupt the Research Project,
- AI failure must never block manual research,
- partial exports should be marked failed/incomplete rather than reported as successful,
- missing current classifications must not erase historical clip provenance.

---

## 30. Benchmark and Evaluation Requirements

Publisher Workspace quality should be tested on real research workflows.

Benchmark areas should include:

```text
provenance completeness
citation correctness
clip-to-source traceability
Document Version traceability
cross-language source comparison fidelity
AI comparison hallucination rate
quote extraction accuracy
transcript timestamp accuracy
fact/claim evidence precision
export reproducibility
manifest completeness
large-project UI performance
large-project export performance
media-rights metadata completeness
```

A representative benchmark should include:

- multilingual news Stories,
- government releases,
- court materials,
- YouTube transcripts,
- conflicting reporting,
- corrected articles,
- source pages that later change,
- multi-country Stories,
- image/media evidence.

Detailed procedures belong in `BENCHMARK_PROCEDURES.md`.

---

## 31. Migration and Backfill Considerations

The Publisher Workspace is mostly additive and should not require destructive changes to existing Documents.

Migration principles:

1. Add research tables without changing original Document content.
2. Foreign-key Research Project evidence to existing Documents.
3. Reference `document_versions` where exact-version provenance is available.
4. Do not copy canonical classification taxonomies into Publisher Workspace tables.
5. Introduce media storage only when a storage policy is defined.
6. Add published-output tracking without requiring direct publication integration.
7. Preserve project history through future schema changes.

Detailed migration ordering belongs in `MIGRATION_PLAN.md`.

---

## 32. Development Roadmap

### Publisher Phase 1 — Research Project Foundation

Build:

```text
research_projects
research_project_documents
research_notes
basic project UI
add/remove Document workflow
```

Success criterion:

An operator can create a Research Project, add Documents, organize them, take notes, and reopen the project reliably.

### Publisher Phase 2 — Clips and Provenance

Add:

```text
research_clips
Document Version linkage
transcript segment linkage
quotes
fact/claim clip types
source traceability
```

Success criterion:

Every selected evidence item can be traced back to exact original evidence.

### Publisher Phase 3 — Citations and Export

Add:

```text
research_citations
Markdown export
source lists
manifest.json
configured writing-folder export
```

Success criterion:

A complete research package can be reproduced outside the platform.

### Publisher Phase 4 — Story Intelligence Integration

Add:

```text
new-development views
claim/evidence matrix
contradiction views
Story timeline integration
cross-language Story comparison
```

### Publisher Phase 5 — AI-Assisted Research

Add through AI Router:

```text
source comparison
candidate fact extraction
timeline assistance
translation assistance
unsupported-claim detection
research question generation
```

### Publisher Phase 6 — Media Tray

Add:

```text
research_project_assets
rights metadata
usage status
asset export
thumbnail / metadata processing
```

### Publisher Phase 7 — Drafting and Output Tracking

Add:

```text
lightweight drafting pane
research_project_outputs
published URL recording
output history
```

Direct publishing integrations, if ever added, require a separate architecture decision and must not be assumed by this specification.

---

## 33. Decisions Already Made

The following are architectural decisions:

- Publisher Workspace is a first-class companion subsystem.
- Internal namespace is `publisher_workspace`.
- Research Projects are durable PostgreSQL-backed objects.
- Original Documents are never modified by research operations.
- Clips preserve provenance to Documents and preferably Document Versions.
- Canonical Geography, Topic, Entity, and Document Type models are reused from Unified Classification.
- Story Intelligence supplies machine Story context; Publisher Workspace supplies human research/editorial selection.
- All AI-assisted research goes through the AI Router.
- AI analysis is never treated as original source evidence.
- Human-authored notes remain distinct from source evidence and AI output.
- Citations are first-class objects.
- Media rights/usage metadata is first-class and `unknown` is not publication approval.
- Markdown is the preferred initial human-readable export format.
- Research packages include machine-readable manifests.
- External editors remain supported and no specific editor is required.
- The platform does not initially attempt to become a full CMS or full word processor.
- Published-output relationships may be recorded without direct publishing automation.

---

## 34. Decisions Requiring Later Design or Benchmarking

The following remain open:

- exact project status transition rules,
- exact clip-type controlled vocabulary,
- whether claims/facts receive a dedicated shared platform model or remain Story-owned,
- exact citation-style support,
- exact media storage architecture,
- automated media metadata extraction,
- editorial-orientation model and governance,
- collaborative/multi-user editing semantics,
- project locking or optimistic concurrency strategy,
- lightweight drafting implementation,
- export archive format,
- AI research prompt/schema designs,
- evidence comparison UI,
- direct publishing integrations,
- research retention and archival policy.

---

## 35. Final Architecture Summary

```text
                      GLOBAL SOURCES
                           │
                           ▼
                    SOURCE ACQUISITION
                           │
                           ▼
                 NORMALIZED DOCUMENTS
                           │
                           ▼
                UNIFIED CLASSIFICATION
                           │
                           ▼
                   STORY INTELLIGENCE
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
        Search/Alerts   Calendar      Observed Events
             │          Correlation       │
             └─────────────┬───────────────┘
                           ▼
                  PUBLISHER WORKSPACE
                           │
                           ▼
                    RESEARCH PROJECT
                           │
          ┌────────────────┼─────────────────┐
          ▼                ▼                 ▼
      Documents          Clips             Media
          │                │                 │
          ├─────────────── Citations ─────────┤
          │                │                 │
          ▼                ▼                 ▼
       Timeline       Source Comparison   Rights Review
          │                │                 │
          └────────────────┼─────────────────┘
                           ▼
                 AI-ASSISTED RESEARCH
                  through AI Router
                           │
                           ▼
                  RESEARCH PACKAGE
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
       External Editor            Drafting Pane
             │                           │
             └─────────────┬─────────────┘
                           ▼
                   PUBLISHED OUTPUT
                           │
                           ▼
                 Output Relationship
                    retained in GNI
```

The Publisher Workspace is therefore the bridge between machine intelligence and human publication.

It should help the operator find the strongest evidence, understand how sources agree or disagree, preserve provenance, manage quotations and media, organize timelines, use AI without confusing generated analysis with evidence, and export a reproducible research package while leaving final editorial judgment with the human publisher.
