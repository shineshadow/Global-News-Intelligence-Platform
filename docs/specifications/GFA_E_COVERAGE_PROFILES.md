# GFA-E — Coverage Profiles

**Status:** FROZEN  
**Alembic revision:** `f8a1c2d3e4b5`  
**Date:** 2026-07-26

## 1. Purpose

GFA-E separates two questions:

```text
canonical universe
    What can GNI represent?

coverage profile
    What does this operator configuration monitor?
```

A profile selects canonical resources without copying, narrowing,
reparenting, or modifying their catalogs.

## 2. Frozen Scope

The frozen foundation models:

```text
enabled geographies
enabled topics
enabled source types
enabled sources
enabled original/content languages
ordered translation targets
enabled semantic document types
enabled content formats
default polling priority
per-source polling-priority overrides
```

Alert thresholds and saved monitoring rules are deferred. GNI has no frozen
alert score, alert metric, or monitoring-rule entity to reference yet.
Thresholds or rules must not be hidden in profile metadata. Their future
tables will reference `coverage_profiles.id`.

User/tenant ownership is also deferred until the identity and authorization
model exists. Profiles are installation-level operator configuration in this
foundation.

## 3. Tables

```text
coverage_profiles
coverage_profile_geographies
coverage_profile_topics
coverage_profile_source_types
coverage_profile_sources
coverage_profile_languages
coverage_profile_translation_targets
coverage_profile_document_types
coverage_profile_content_formats
coverage_profile_source_polling_overrides
```

Every selector is a normalized foreign key. Polymorphic resource keys and
untyped selector JSON are prohibited.

Deleting a profile cascades only its configuration rows. Deleting a selected
canonical resource is restricted. A profile never owns canonical data.

## 4. Selection Algebra

Coverage dimensions use allowlist semantics:

```text
no rows for a dimension
    unrestricted

one or more rows for a dimension
    candidate must match at least one row

within one dimension
    OR

across constrained dimensions
    AND
```

This makes the seeded empty `global` profile preserve pre-GFA-E behavior.
Empty does not mean “monitor nothing.”

Translation targets are outputs, not coverage selectors:

```text
no translation-target rows
    no translation requested

one or more rows
    targets are processed by ascending preference_order
```

Translation targets never make a document eligible or ineligible.

## 5. Hierarchy Policy

Geography, topic, source-type, and document-type selectors record:

```text
selected canonical node
include_descendants
```

`include_descendants = false` means the exact node only.
`include_descendants = true` resolves the node and all current descendants.

Resolution is read-time behavior. GFA-E does not generate inferred child
selector rows. Catalog hierarchy changes therefore remain catalog changes,
not silent profile mutations.

## 6. Profile Identity and Default

Profile slugs are stable lowercase identifiers using digits and underscores.
Names must be nonempty. Profiles may be deactivated without deleting their
configuration.

Exactly one active profile is default. The migration seeds:

```text
slug: global
name: Global
active: true
default: true
scope rows: none
default polling priority: normal
metadata.seed_set: gfa_e_1
```

The partial unique index `uq_coverage_profiles_default` enforces the
single-default upper bound, a check constraint prevents an inactive profile
from remaining default, and the deferred
`coverage_profiles_require_default` constraint trigger prevents a transaction
from committing without exactly one active default. Application service
operations lock and switch the default within one transaction.

Inactive profiles retain their configuration for later reactivation or
inspection, but they are not executable monitoring configurations. Reading or
resolving configuration does not activate a profile.

## 7. Polling Policy

Polling priority is profile configuration:

```text
coverage_profiles.default_polling_priority
coverage_profile_source_polling_overrides.polling_priority
```

Allowed values remain:

```text
low
normal
high
critical
```

Effective priority is the source override when present, otherwise the
profile default. An override does not select the source and a source selector
does not create an override.

The legacy `sources.priority` column is removed. Existing non-normal values
are migrated to overrides on the seeded global profile. The API and web
lifecycle compatibility field now reads and writes the default profile's
effective policy, preserving existing behavior while removing global
configuration from the source record.

If the required default profile is missing, compatibility writes fail
explicitly. They never accept and silently discard a polling priority.
CSV inventory imports use the same default-profile policy path, so a newly
imported non-normal priority is persisted as an override rather than assigned
to the removed source column. Inventory priority is validated on every row;
when a source already exists, its current polling policy is preserved.

## 8. Atomic Configuration

`replace_coverage_profile_scope` is a complete, atomic selector replacement.
It validates every requested canonical reference as active before deleting
the previous rows. Missing or inactive references reject the whole
replacement.

The profile row is locked during replacement, serializing concurrent complete
replacements for the same profile. Polling-policy writes use the same
profile-row serialization boundary.

Duplicate selectors, duplicate translation languages, and duplicate
translation preference positions are rejected. Silent deduplication is not
allowed.

Polling overrides are updated separately because policy and selection are
independent.

## 9. Migration and Downgrade Policy

Upgrade first rejects any legacy source priority outside the frozen four-value
vocabulary. It then creates the profile tables, seeds the unrestricted global
profile, migrates effective source priorities, and removes the legacy column.

Downgrade is allowed only when:

```text
the seeded global profile is present and identifiable
no custom profile exists
no selector or translation-target row exists
```

Global-profile polling overrides and its default priority are losslessly
reconstructed into `sources.priority`. Any meaningful profile configuration
blocks downgrade.

## 10. Direct Proofs

The implementation directly proves:

```text
the seeded global profile is active, default, and unrestricted
all selector and policy resources are reference-backed
invalid profile slugs and polling priorities are rejected
the database rejects removal of the final active default
creating a new default atomically switches the existing default
duplicate selectors and target orders are rejected
empty coverage dimensions resolve as unrestricted
empty translation targets resolve as translation disabled
descendants are included only when explicitly requested
descendant resolution creates no inferred selector rows
translation targets retain deterministic preference order
missing canonical references reject the whole replacement
a rejected replacement preserves the prior scope
polling priorities can differ by profile for one source
legacy source priority remains API-compatible through the default profile
inventory priority persists through the default profile
invalid inventory priority is rejected
concurrent whole-scope replacements serialize on the profile row
invalid legacy priorities block upgrade
meaningful profile configuration blocks downgrade
clean downgrade and re-upgrade succeed
ORM metadata and the applied schema have no drift
```

## 11. Frozen Invariants

```text
canonical catalogs are global; profiles only reference them
profile metadata is not a selector, threshold, or rule store
empty coverage selector sets mean unrestricted
empty translation targets mean translation disabled
within a dimension selections are OR; constrained dimensions combine with AND
hierarchy expansion is explicit and read-time
no inferred selector rows are generated
coverage languages and translation targets are independent
source selection and source polling policy are independent
polling priority is profile-specific and absent from sources
exactly one active profile is default at transaction commit
scope replacement is all-or-nothing
whole-scope and polling-policy writes serialize per profile
custom configuration blocks destructive downgrade
```

## 12. Verification Results

Validation used isolated PostgreSQL 17.10:

```text
coverage-profile tables                                  10
seeded active/default unrestricted profiles               1
legacy source priority columns                            0
invalid profile or override priorities                    0
duplicate translation preference positions                0
orphan canonical profile references                       0
direct and affected GFA-E tests                           31
complete repository tests                                143
clean downgrade and re-upgrade                         passed
real critical-priority upgrade/reconstruction          passed
Alembic model/schema drift operations                      0
schema-only snapshot regenerated                         yes
```

## 13. Formal Freeze Review

The formal review covered semantic boundaries, relational constraints,
transaction behavior, migration reversibility, source-consumer compatibility,
direct tests, the complete repository suite, verification SQL, schema drift,
and documentation.

Three blockers were found and corrected:

```text
the database enforced at most one default but not the required minimum
concurrent complete scope replacements were not serialized
CSV inventory priority targeted the removed source column
```

The deferred default constraint, per-profile row locks, and default-profile
inventory persistence close those gaps. Direct regression tests pin each
behavior. A fresh-database test also exposed and corrected a test fixture that
requested an unseeded language tag; canonical-reference rejection itself was
working correctly.

## 14. Freeze Decision

GFA-E is frozen at Alembic revision `f8a1c2d3e4b5`. No remaining schema,
semantic, migration-safety, concurrency, compatibility, test, drift, or
documentation blocker was found.
