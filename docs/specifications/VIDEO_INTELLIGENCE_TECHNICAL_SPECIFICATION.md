# Video Intelligence Technical Specification

**Project:** Global News Intelligence Platform  
**Status:** Development Candidate  
**Version:** 0.1  
**Date:** 2026-07-30

## 1. Purpose

Video Intelligence discovers and evaluates video content without downloading
video media by default. It is metadata- and subtitle-first, preserves original
evidence, and exposes expensive media processing only through an explicit
operator workflow.

## 2. Source and Item Semantics

```text
Follow Channel
    configure the channel as a Source and discover its future videos

Watch Video
    create a semantic Watch from that video's transcript content

Process Video
    explicitly request download, extraction, ASR, or another media operation
```

These actions are independent. Watching a video does not download its media or
implicitly Follow its channel.

## 3. Default Acquisition

For a video discovered through a followed channel, GNI attempts to retain:

```text
platform video and channel identifiers
canonical URL
title
author description
published and discovered times
duration
video thumbnail
channel icon/favicon
available format/manifest inventory
platform-declared container, codecs, resolution, bitrate, and size when exposed
subtitle-track inventory
selected original subtitle artifact
```

Declared media metadata remains distinct from locally probed metadata. The
absence of downloaded media means some codec/container facts may remain
unknown or platform-declared.

Video bytes are not downloaded by default.

## 4. Subtitle Policy

Original subtitle artifacts and track metadata are preserved. Track state
distinguishes:

```text
available
selected
authored
automatically generated
no_subtitles
subtitles_unavailable
retrieval_failed
translation_failed
```

If a usable English track exists, GNI uses it. Otherwise every selected
non-English subtitle for followed-channel video is queued for English
translation. Translation retains language, timestamps when practical, input
hash, provider/model, and processing provenance.

A video without usable subtitles remains discoverable by metadata, but its
card and detail view state plainly that no usable subtitle is available.
Automatic ASR is prohibited.

## 5. Summary Policy

The English subtitle text, title, and author description enter the summary
queue. Subtitle evidence remains primary; title and description are context.

Initial targets:

```text
fewer than 200 transcript words
    no summary; display transcript

200 through 2,500 transcript words
    target approximately 20 percent

more than 2,500 transcript words
    target 400–500 words, optionally sectioned
```

Summary policy is configurable and never replaces the full transcript for
Watch, Story, classification, entity, or claim processing.

## 6. Video Processing Workbench

The card Process action opens a Video Processing page with the selected video.
Opening the page starts no processing.

Candidate explicit operations:

```text
download selected video format
download audio/video
extract audio
speech-to-text
translate transcript
summarize or resummarize
generate chapters
extract still frames
create evidence clips
future text-to-speech and generated voice outputs
```

Before submission, the UI shows available inputs, expected outputs, estimated
download size when known, resource class, and existing job state. Submitted
operations are durable and idempotent.

## 7. Story and Attention Integration

A video with usable subtitle or operator-generated transcript may be a
qualifying Story item. Story membership and priority follow
`CONTENT_ATTENTION_AND_ENRICHMENT_POLICY.md`.

The video summary is for operator convenience. System analysis uses full
metadata, original and translated transcript evidence, classifications,
entities, claims, and semantic representations.

## 8. Persistence Candidate

```text
video_channels or canonical Sources/Endpoints
videos
video_format_observations
video_subtitle_tracks
transcripts
transcript_segments
video_processing_jobs
video_processing_attempts
video_derived_artifacts
```

The final schema must reuse canonical Source, Endpoint, Document, content
format, language, Artifact, AI job, and provenance models rather than create
competing taxonomies.

## 9. Acceptance and Conflict Tests

```text
following a channel does not download video bytes
watching a video does not download video bytes or Follow its channel
opening Video Processing starts no job
ASR requires an explicit operator request
usable English subtitles prevent unnecessary translation
selected non-English subtitles queue English translation
no-subtitle and retrieval-failure states remain distinct
declared and locally probed media metadata remain distinct
summary is not used as a substitute transcript
video qualifies for Story only with usable text evidence
all derived artifacts retain source and process provenance
```

