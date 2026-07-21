What you need is a new layer between **Research** and your external editor:

# Publisher Workspace and Story Builder

#### UI name:

Publisher Workspace

#### Suggested internal namespace:

publisher_workspace

The existing architecture gets the system to Sources, Documents, Stories, Events, Search, Alerts, and Research.  The Web UI strategy also establishes the reusable interface components needed to build this kind of workflow without turning the platform into Drupal or another CMS. 

The complete publishing workflow should be:

```text
Breaking / Search / Calendar / Stories
                  │
                  ▼
          Open Story Workspace
                  │
                  ▼
       Review Related Documents
                  │
                  ▼
       Select Documents and Media
                  │
                  ▼
        Create Research Project
                  │
                  ▼
      Clip Facts, Quotes and Images
                  │
                  ▼
       Compare and Verify Sources
                  │
                  ▼
        Export Research Package
                  │
                  ▼
       Write in External Text Editor
```

## 1. Finding the story

You would usually begin from one of these places:

```text
Breaking
Stories
Search
Intelligence Calendar
Alerts
Countries
Topics
Entities
YouTube
```

For example:

```text
Intelligence Calendar
    ↓
Trump Address to the Nation
    ↓
Related documents and livestreams
```

or:

```text
Search
    ↓
South Korea Constitution Day
    ↓
Matching stories and documents
```

## 2. Opening the Story Workspace

When you open a Story, the platform should show the story summary and all related documents.

```text
TRUMP ADDRESS TO THE NATION

Documents: 84
Sources: 31
Languages: 5
New developments: 9
Official sources: 4
Video sources: 7
```

The documents should be filterable by:

```text
Country
Language
Source
Source type
Publication time
Official versus media
Original reporting versus aggregation
Document importance
New-information status
Political/editorial orientation
Video, article, press release or social post
```

Each document row should show useful decision information:

```text
Source
Headline
Publication time
Language
Document type
Source authority
Original reporting
Importance
New information
Agreement or contradiction
```

This helps you decide which documents are worth using.

## 3. Selecting documents for your story

Every document should have an action such as:

```text
[Add to Research Project]
```

You could select:

* an official White House announcement,
* a Reuters report,
* a Korean-language article,
* a YouTube transcript,
* a court document,
* and a relevant image.

Those documents would go into a named research project:

```text
Research Project:
Trump Address — August 3
```

Possible project states:

```text
Collecting
Researching
Drafting
Fact Checking
Ready
Published
Archived
```

## 4. Research Project interface

The Research Project should function like a digital evidence board.

```text
TRUMP ADDRESS — AUGUST 3

Documents
Clips
Quotes
Facts
Images
Videos
Timeline
Notes
Sources
Export
```

The original documents remain unchanged. You create smaller reusable **clips** from them.

### Text clip

```text
Document:
White House announcement

Selected text:
The president will address the nation at 9:00 p.m. Eastern.

Clip type:
Confirmed fact
```

### Quote clip

```text
Speaker:
Donald Trump

Quote:
“We will address the challenges facing our country.”

Timestamp:
00:08:44
```

### Transcript clip

```text
Video:
White House livestream

Segment:
00:08:44–00:09:31

Transcript:
...
```

### Research note

```text
This is the first announced national address since...
```

The note is your own commentary and must remain clearly separate from source material.

## 5. Every clip preserves provenance

Every fact, quote, paragraph, image, and transcript segment should retain its source automatically.

Recommended stored information:

```text
source name
document title
canonical URL
author
publication date
retrieval date
original language
original text
translated text
video timestamp
document ID
```

That means you never have to wonder later:

> Where did I get this sentence?

You could click any clip and reopen the original source document.

## 6. AI-assisted research

The AI should help you research, but it should not silently assemble unsupported material.

Useful actions could include:

```text
Summarize selected documents
Compare selected sources
Extract confirmed facts
Extract direct quotes
Create a timeline
Translate selected passages
Identify contradictions
Identify unsupported claims
Show information unique to each source
Separate official statements from media interpretation
Find the earliest source
```

Example:

```text
[Compare Selected Sources]
```

Result:

```text
AGREEMENT

All selected sources agree the address begins at 9:00 p.m.

UNIQUE TO WHITE HOUSE

The address will be delivered from the Oval Office.

UNIQUE TO REUTERS

Two administration officials say foreign policy will be discussed.

CONFLICT

One outlet reports 8:00 p.m.; the official White House schedule says 9:00 p.m.
```

You then decide what belongs in your story.

## 7. Image and media tray

The Research Project should include a **Media Tray**.

```text
MEDIA

Official photographs
Article images
YouTube thumbnails
Video stills
Government graphics
Charts
Screenshots
Uploaded images
```

Each image should retain:

```text
original source
original URL
caption
photographer
publication
date
copyright owner
license
attribution requirement
usage status
```

Usage status could be:

```text
Approved
Public domain
Licensed
Attribution required
Editorial use
Unknown
Do not publish
```

This is important because finding an image does not automatically mean the image can legally be republished.

The platform should favor:

* official government images with clear usage rules,
* public-domain material,
* licensed wire-service images,
* Creative Commons material,
* images you created or uploaded,
* and properly attributed media.

## 8. Exporting to a separate editor

The platform does not initially need to become a complete word processor.

The Research Project should support:

```text
Copy Selected Clips
Copy With Citations
Export Markdown
Export Plain Text
Export HTML
Export Research Package
```

The best primary export format for your workflow is **Markdown**.

An exported research package could look like:

```text
trump-address-2026-08-03/
│
├── draft.md
├── research-notes.md
├── selected-clips.md
├── sources.md
├── timeline.md
├── manifest.json
│
└── assets/
    ├── white-house-photo.jpg
    ├── speech-thumbnail.jpg
    └── chart.png
```

### `draft.md`

```markdown
# Trump Address to the Nation

<!-- Begin writing here -->

## Selected Facts

- The address is scheduled for 9:00 p.m. Eastern.[^1]
- It will be delivered from the Oval Office.[^1]

## Selected Quotes

> “...”

## Sources

[^1]: White House, “Presidential Address Announcement,” August 2, 2026.
```

You could open this in:

```text
VS Code
Obsidian
Typora
Zettlr
Kate
Notepad++
LibreOffice
Microsoft Word after conversion
```

## 9. Watch-folder export

Because the platform is self-hosted, it could also support a configured export directory:

```text
/home/christopher/news-drafts/
```

When you click:

```text
[Send to Writing Folder]
```

the platform writes:

```text
/home/christopher/news-drafts/trump-address/
```

You then open that directory in your preferred editor.

Possible destinations could include:

```text
Local filesystem
Samba share
NFS share
Nextcloud folder
Syncthing folder
Git repository
```

## 10. Optional lightweight drafting pane

The platform could eventually include a simple drafting pane beside the Research Project:

```text
┌─────────────────────────────┬──────────────────────────────┐
│ RESEARCH CLIPS              │ DRAFT                        │
│                             │                              │
│ Official announcement       │ Trump will address...       │
│ Reuters report              │                              │
│ Transcript quote            │                              │
│ Image                       │                              │
└─────────────────────────────┴──────────────────────────────┘
```

You could drag or insert clips into the draft.

But I would initially keep this lightweight. The platform should not try to compete with a full editor during the early development phases.

## 11. Recommended database additions

I would add:

```text
research_projects
research_project_documents
research_clips
research_notes
research_project_assets
research_citations
research_exports
```

### `research_projects`

```text
id
title
description
status
created_by
created_at
updated_at
related_story_id
related_calendar_event_id
```

### `research_project_documents`

```text
research_project_id
document_id
selected_at
selection_reason
```

### `research_clips`

```text
id
research_project_id
document_id
clip_type
content_original
content_translated
start_offset
end_offset
video_start_time
video_end_time
user_notes
```

Clip types:

```text
fact
quote
paragraph
transcript
summary
claim
timeline_item
```

### `research_project_assets`

```text
id
research_project_id
document_id
asset_type
local_path
original_url
caption
credit
copyright_owner
license
usage_status
```

### `research_exports`

```text
id
research_project_id
format
export_path
created_at
manifest
```

## 12. Recommended Web UI navigation

The current `Research` section should become a first-class Publisher Workspace:

```text
Research
├── Research Projects
├── Draft Basket
├── Saved Documents
├── Saved Clips
├── Quotes
├── Media Tray
├── Timelines
├── Source Comparisons
└── Exports
```

Or the main navigation could explicitly say:

```text
Publisher Workspace
```

with:

```text
Publisher Workspace
├── Projects
├── Research Queue
├── Clips
├── Media
├── Exports
└── Archive
```

## Final workflow

Your normal publishing process would become:

```text
1. Find an important Story or Calendar Event.

2. Open the Story Workspace.

3. Review the related documents.

4. Filter out weak, repetitive, or irrelevant sources.

5. Select the strongest primary and secondary sources.

6. Add the documents to a Research Project.

7. Clip facts, quotes, transcript segments, and images.

8. Use AI to compare sources and identify contradictions or new information.

9. Review image rights and attribution.

10. Export the project as a Markdown research package.

11. Open the package in your preferred external editor.

12. Write and assemble your own final story or social post.
```

The platform gathers, organizes, translates, compares, and preserves the evidence.

**You remain the publisher who decides which sources to trust, which facts to use, how to frame the story, and what the final article or post says.**

