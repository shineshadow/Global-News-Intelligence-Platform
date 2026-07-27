# Step 24 — Classification-Aware News Feed Filters

**Status:** FROZEN  
**Schema migration:** none  
**Date:** 2026-07-27

## 1. Purpose

Step 24 establishes one reusable document-matching contract:

```text
transient News Feed query
        ↓
shared matching semantics
        ↓
Step 25 persistent Monitor
```

Step 24 does not persist saved rules, evaluate background monitors, or deliver
alerts.

## 2. Supported Criteria

```text
coverage profile
document geography and explicit descendant inclusion
topic and explicit descendant inclusion
entity and entity role
semantic document type and explicit descendant inclusion
content format
source
source type and explicit descendant inclusion
effective document language
minimum classification confidence
effective publication/retrieval time
literal keyword or phrase
```

Unset criteria are unrestricted. Values within one dimension combine with OR.
Constrained dimensions combine with AND.

The active default coverage profile applies when no profile is selected.
Explicit filters further narrow profile scope.

## 3. Classification Semantics

Geography filters query active `document_geographies` assertions.
`Source.country` is publisher jurisdiction and never supplies document
geography.

Topic, geography, entity, and semantic document-type filters use correlated
existence predicates. A document therefore appears once even when multiple
matching assertions exist, and pagination counts remain document counts.

Only active assertions match. Minimum confidence is evaluated on the same
assertion that satisfies its classification criterion. It does not globally
discard documents when no classification criterion is selected.

Hierarchy expansion happens at read time. No inferred classification rows are
written.

## 4. Text Semantics

The initial text query is one literal, case-insensitive keyword or phrase over:

```text
title_original
summary_original
content_original
```

SQL wildcard characters in user input are escaped. Boolean expressions and
regular-expression execution belong to the reviewed Step 25 rule language;
Step 24 does not silently interpret them.

## 5. Language Semantics

The effective News Feed language remains:

```text
COALESCE(documents.language, sources.primary_language)
```

This is the query-time fallback frozen by GFA-B. It does not write an inferred
document language.

## 6. Implementation Boundary

```text
app/schemas/document_match.py
    typed provider-independent matching contract

app/services/document_matching_service.py
    coverage resolution, hierarchy expansion, and SQL predicates

app/services/document_browser_service.py
    document result/count query and filter options

app/web/document_routes.py
    HTTP parameter adaptation and pagination URLs

app/web/templates/documents.html
    transient operator controls
```

Step 25 must consume `DocumentMatchCriteria` or an explicitly versioned
successor. It must not implement a second, incompatible matcher.

## 7. Candidate Proofs

The implementation candidate must directly prove:

```text
publisher country does not drive document-geography filtering
geography descendants match only when explicitly enabled
source-type descendants match only when explicitly enabled
values within one classification dimension combine with OR
different constrained dimensions combine with AND
inactive historical assertions do not match
minimum confidence applies to the matching assertion
entity and entity-role predicates apply to the same assertion
coverage-profile scope is applied before transient filters
multi-label matches do not duplicate rows or counts
content format, semantic document type, source type, and language combine
literal percent and underscore characters are not SQL wildcards
blank legacy form values remain harmless
HTMX responses remain partial and pagination retains active criteria
```

## 8. Freeze Gate

Before Step 24 freezes:

```text
focused matching and News Feed tests pass
all repository tests pass
rendered filter controls preserve pagination state
no schema migration or Alembic drift is introduced
documentation and current behavior agree
no Step 25 persistence or Step 26 delivery behavior leaks into Step 24
```

## 9. Final Validation

Validated on 2026-07-27:

```text
27 direct criteria, matching, and News Feed tests passed
161 repository tests passed
Alembic check: no new upgrade operations detected
Ruff checks passed for the Step 24 contract, service, route, and exports
Python compilation passed
git diff --check passed
```

## 10. Formal Freeze Review

The formal review examined:

```text
GFA-A through GFA-E ownership boundaries
publisher jurisdiction versus canonical document geography
semantic document type versus content format
coverage-profile scope and transient-filter intersection
OR-within-dimension and AND-across-dimension behavior
active assertion and same-assertion confidence semantics
explicit read-time hierarchy expansion
duplicate-safe counts and pagination
effective language fallback
literal text and SQL wildcard handling
criteria validation, normalization, and immutability
caller-independent reuse by Step 25
HTMX and full-page UI state
Step 24 versus Step 25/26 ownership
repository regression and Alembic drift
```

The review found and corrected two blockers:

```text
source-type and fallback-language predicates implicitly required callers
to join the sources table

the claimed literal underscore wildcard behavior lacked a direct proof
```

Source predicates are now correlated to each document, so the shared matcher
works correctly from a document-only query. Direct regression coverage pins
that consumer-independent behavior, source-language fallback, source-type
descendants, and literal handling of both `%` and `_`.

The review also froze criteria objects against mutation and rejects
timezone-ambiguous effective timestamps.

## 11. Frozen Invariants

```text
Source.country never supplies document subject geography
coverage profile scope always applies before transient criteria
values within a dimension are OR; constrained dimensions are AND
hierarchy descendants are included only when explicitly requested
classification filters match active assertions only
confidence belongs to the assertion satisfying its criterion
multi-label assertions never duplicate document rows or counts
document type and content format remain separate dimensions
effective language uses the frozen query-time source fallback
text input is one literal case-insensitive keyword or phrase
matching criteria are normalized and immutable after validation
matching predicates do not require an undocumented outer Source join
Step 24 persists no monitors, matches, alerts, or delivery records
```

## 12. Freeze Decision

Step 24 is frozen. It required no schema migration and introduced no Alembic
drift. Step 25 must reuse `DocumentMatchCriteria` and
`build_document_match_plan`, or introduce an explicitly versioned successor;
it must not silently redefine these matching semantics.
