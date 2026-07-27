\set ON_ERROR_STOP on

\echo '=== GFA-E MIGRATION HEAD ==='
SELECT version_num
FROM alembic_version;

\echo '=== DEFAULT PROFILE: EXPECT 1 ==='
SELECT count(*) AS default_profiles
FROM coverage_profiles
WHERE is_default;

\echo '=== SEEDED GLOBAL PROFILE: EXPECT 1 ==='
SELECT count(*) AS seeded_global_profiles
FROM coverage_profiles
WHERE slug = 'global'
  AND is_active
  AND is_default
  AND default_polling_priority = 'normal'
  AND metadata ->> 'seed_set' = 'gfa_e_1';

\echo '=== LEGACY SOURCE PRIORITY COLUMN: EXPECT 0 ==='
SELECT count(*) AS legacy_priority_columns
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'sources'
  AND column_name = 'priority';

\echo '=== INVALID PROFILE PRIORITIES: EXPECT 0 ==='
SELECT count(*) AS invalid_profile_priorities
FROM coverage_profiles
WHERE default_polling_priority
      NOT IN ('low', 'normal', 'high', 'critical');

\echo '=== INVALID OVERRIDE PRIORITIES: EXPECT 0 ==='
SELECT count(*) AS invalid_override_priorities
FROM coverage_profile_source_polling_overrides
WHERE polling_priority
      NOT IN ('low', 'normal', 'high', 'critical');

\echo '=== DUPLICATE TRANSLATION ORDER: EXPECT 0 ==='
SELECT count(*) AS duplicate_translation_orders
FROM (
    SELECT profile_id, preference_order
    FROM coverage_profile_translation_targets
    GROUP BY profile_id, preference_order
    HAVING count(*) > 1
) AS duplicates;

\echo '=== ORPHAN PROFILE REFERENCES: EXPECT ALL ZERO ==='
SELECT
    (SELECT count(*)
     FROM coverage_profile_geographies AS member
     LEFT JOIN geographies AS target
       ON target.id = member.geography_id
     WHERE target.id IS NULL) AS geographies,
    (SELECT count(*)
     FROM coverage_profile_topics AS member
     LEFT JOIN topics AS target
       ON target.id = member.topic_id
     WHERE target.id IS NULL) AS topics,
    (SELECT count(*)
     FROM coverage_profile_source_types AS member
     LEFT JOIN source_types AS target
       ON target.slug = member.source_type_slug
     WHERE target.id IS NULL) AS source_types,
    (SELECT count(*)
     FROM coverage_profile_sources AS member
     LEFT JOIN sources AS target
       ON target.id = member.source_id
     WHERE target.id IS NULL) AS sources,
    (SELECT count(*)
     FROM coverage_profile_languages AS member
     LEFT JOIN language_tags AS target
       ON target.tag = member.language_tag
     WHERE target.tag IS NULL) AS languages,
    (SELECT count(*)
     FROM coverage_profile_translation_targets AS member
     LEFT JOIN language_tags AS target
       ON target.tag = member.language_tag
     WHERE target.tag IS NULL) AS translation_targets,
    (SELECT count(*)
     FROM coverage_profile_document_types AS member
     LEFT JOIN document_types AS target
       ON target.id = member.document_type_id
     WHERE target.id IS NULL) AS document_types,
    (SELECT count(*)
     FROM coverage_profile_content_formats AS member
     LEFT JOIN content_formats AS target
       ON target.slug = member.content_format_slug
     WHERE target.id IS NULL) AS content_formats,
    (SELECT count(*)
     FROM coverage_profile_source_polling_overrides AS member
     LEFT JOIN sources AS target
       ON target.id = member.source_id
     WHERE target.id IS NULL) AS polling_overrides;

\echo '=== PROFILE CONFIGURATION DISTRIBUTION ==='
SELECT
    profile.slug,
    profile.is_active,
    profile.is_default,
    profile.default_polling_priority,
    (SELECT count(*) FROM coverage_profile_geographies
     WHERE profile_id = profile.id) AS geographies,
    (SELECT count(*) FROM coverage_profile_topics
     WHERE profile_id = profile.id) AS topics,
    (SELECT count(*) FROM coverage_profile_sources
     WHERE profile_id = profile.id) AS sources,
    (SELECT count(*) FROM coverage_profile_languages
     WHERE profile_id = profile.id) AS languages,
    (SELECT count(*) FROM coverage_profile_translation_targets
     WHERE profile_id = profile.id) AS translation_targets
FROM coverage_profiles AS profile
ORDER BY profile.slug;
