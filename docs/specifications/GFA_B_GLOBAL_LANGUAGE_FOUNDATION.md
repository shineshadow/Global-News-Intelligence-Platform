# GFA-B — Global Language Foundation

## Status

Implementation package for the Global Foundation Audit language phase.

Alembic revision:

```text
f72c9a1e4b6d
```

Parent revision:

```text
e13a6f4c92b7
```

## Architectural boundary

GNI stores canonical BCP 47-compatible language tags.

BCP 47 and the IANA Language Subtag Registry govern tag syntax,
registered subtags, deprecated values, and preferred replacements.
GNI governs application semantics, provenance, source defaults,
translation configuration, and operator behavior.

The following concepts remain distinct:

```text
document original language
source primary/default language
translation source language
translation target language
operator UI language
```

A source primary language does not overwrite an unknown document language.

## Canonicalization

The application:

- strips surrounding whitespace;
- accepts underscores as external separators;
- stores hyphenated canonical tags;
- applies conventional casing;
- replaces deprecated or overlong codes where the library provides a
  canonical replacement;
- maps the observed compatibility value `English` to `en`;
- rejects invalid required values;
- records invalid external feed metadata without rejecting the document.

Examples:

```text
en-us   → en-US
zh_tw   → zh-TW
English → en
eng_US  → en-US
```

These remain distinct:

```text
zh-Hant
zh-TW
```

The first specifies script. The second specifies region.

Likely-subtag expansion is not stored as the original language tag.

## Null and special values

```text
NULL = absent or not classified
und  = explicitly undetermined language
zxx  = no linguistic content
```

GFA-B does not fill every `documents.language IS NULL` value from
`sources.primary_language`.

The automatic `und` default on `entity_aliases.language` is removed.
Future alias writes must provide a language tag explicitly.

## Registry model

`language_tags` is an extensible registry of canonical tags used by GNI.
It is not a closed supported-language enumeration.

The migration seeds the ten tags needed by current data and foundation
semantics. New valid tags are registered transactionally on first use.

`language_tag_aliases` records GNI compatibility aliases. The initial
alias is:

```text
English → en
```

All five existing language-bearing columns reference
`language_tags.tag`:

```text
sources.primary_language
documents.language
document_versions.language
classification_runs.language
entity_aliases.language
```

All are expanded from `varchar(20)` to `varchar(255)`. Language tags
must never be silently truncated.

## Ingestion behavior

RSS and Atom metadata is normalized before persistence.

Document metadata retains:

```text
language_raw
language_source
language_normalization
language_error
```

`language_source` is currently `entry`, `feed`, or `NULL`.

An invalid external language value produces:

```text
documents.language = NULL
metadata.language_raw = original value
metadata.language_normalization = invalid
metadata.language_error = validation message
```

The document remains durably ingested.

## Historical synchronization

The preflight verified zero language mismatches between:

```text
documents ↔ document_versions
documents ↔ classification_runs
```

The migration canonicalizes all synchronized copies in one transaction.

## Compatibility

The document browser continues using:

```text
COALESCE(documents.language, sources.primary_language)
```

as an effective display/filter value. This is a query-time fallback only.

Legacy query values such as `en-us` are canonicalized before filtering.

## Dependency

```text
langcodes>=3.5.1,<4
```

The package provides BCP 47 parsing, canonical formatting, deprecated
replacement handling, and registry-backed validity checks.

## Migration safety

Writers should be stopped while the development database is upgraded.

The migration refuses to complete if it finds a language value that is
not present in the seeded canonical registry after deterministic
normalization.

Downgrade refuses when any stored language tag exceeds the old
20-character limit.
