\pset pager off
\timing on

\echo ''
\echo '=== REVISION ==='
SELECT version_num
FROM alembic_version;

\echo ''
\echo '=== LANGUAGE CATALOG COUNTS ==='
SELECT
    (SELECT count(*) FROM language_tags) AS language_tags,
    (
        SELECT count(*)
        FROM language_tag_aliases
    ) AS language_tag_aliases;

\echo ''
\echo '=== SEEDED LANGUAGE TAGS ==='
SELECT
    tag,
    language_subtag,
    script_subtag,
    region_subtag,
    is_private_use,
    is_active
FROM language_tags
ORDER BY tag;

\echo ''
\echo '=== LANGUAGE ALIASES ==='
SELECT
    alias_key,
    alias,
    canonical_tag,
    alias_type,
    is_active
FROM language_tag_aliases
ORDER BY alias_key;

\echo ''
\echo '=== SOURCE LANGUAGE VALUES ==='
SELECT primary_language, count(*) AS sources
FROM sources
GROUP BY primary_language
ORDER BY sources DESC, primary_language;

\echo ''
\echo '=== DOCUMENT LANGUAGE VALUES ==='
SELECT
    CASE
        WHEN language IS NULL THEN '<NULL>'
        ELSE language
    END AS language,
    count(*) AS documents
FROM documents
GROUP BY 1
ORDER BY documents DESC, language;

\echo ''
\echo '=== DOCUMENT VERSION LANGUAGE VALUES ==='
SELECT
    CASE
        WHEN language IS NULL THEN '<NULL>'
        ELSE language
    END AS language,
    count(*) AS versions
FROM document_versions
GROUP BY 1
ORDER BY versions DESC, language;

\echo ''
\echo '=== CLASSIFICATION RUN LANGUAGE VALUES ==='
SELECT
    CASE
        WHEN language IS NULL THEN '<NULL>'
        ELSE language
    END AS language,
    count(*) AS runs
FROM classification_runs
GROUP BY 1
ORDER BY runs DESC, language;

\echo ''
\echo '=== INVALID LANGUAGE REFERENCES: EXPECT ALL 0 ==='
SELECT
    (
        SELECT count(*)
        FROM sources AS row
        LEFT JOIN language_tags AS tag
          ON tag.tag = row.primary_language
        WHERE tag.tag IS NULL
    ) AS invalid_source_languages,
    (
        SELECT count(*)
        FROM documents AS row
        LEFT JOIN language_tags AS tag
          ON tag.tag = row.language
        WHERE row.language IS NOT NULL
          AND tag.tag IS NULL
    ) AS invalid_document_languages,
    (
        SELECT count(*)
        FROM document_versions AS row
        LEFT JOIN language_tags AS tag
          ON tag.tag = row.language
        WHERE row.language IS NOT NULL
          AND tag.tag IS NULL
    ) AS invalid_version_languages,
    (
        SELECT count(*)
        FROM classification_runs AS row
        LEFT JOIN language_tags AS tag
          ON tag.tag = row.language
        WHERE row.language IS NOT NULL
          AND tag.tag IS NULL
    ) AS invalid_run_languages,
    (
        SELECT count(*)
        FROM entity_aliases AS row
        LEFT JOIN language_tags AS tag
          ON tag.tag = row.language
        WHERE tag.tag IS NULL
    ) AS invalid_alias_languages;

\echo ''
\echo '=== NONCANONICAL LEGACY VALUES: EXPECT 0 ==='
SELECT count(*) AS noncanonical_values
FROM (
    SELECT primary_language AS language FROM sources
    UNION ALL
    SELECT language FROM documents
    UNION ALL
    SELECT language FROM document_versions
    UNION ALL
    SELECT language FROM classification_runs
    UNION ALL
    SELECT language FROM entity_aliases
) AS values_to_check
WHERE language IN (
    'en-us',
    'zh-tw',
    'English'
);

\echo ''
\echo '=== DOCUMENT / VERSION MISMATCHES: EXPECT 0 ==='
SELECT count(*) AS mismatches
FROM document_versions AS version
JOIN documents AS document
  ON document.id = version.document_id
WHERE version.language IS DISTINCT FROM document.language;

\echo ''
\echo '=== CLASSIFICATION RUN / DOCUMENT MISMATCHES: EXPECT 0 ==='
SELECT count(*) AS mismatches
FROM classification_runs AS run
JOIN documents AS document
  ON document.id = run.document_id
WHERE run.language IS DISTINCT FROM document.language;

\echo ''
\echo '=== LANGUAGE COLUMN LENGTHS: EXPECT 255 ==='
SELECT
    table_name,
    column_name,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
      (table_name = 'sources'
       AND column_name = 'primary_language')
      OR
      (
          table_name IN (
              'documents',
              'document_versions',
              'classification_runs',
              'entity_aliases'
          )
          AND column_name = 'language'
      )
  )
ORDER BY table_name, column_name;

\echo ''
\echo '=== ENTITY ALIAS DEFAULT: EXPECT NULL ==='
SELECT column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'entity_aliases'
  AND column_name = 'language';

\echo ''
\echo '=== END GFA-B VERIFICATION ==='
