\set ON_ERROR_STOP on

\echo '=== GFA-D MIGRATION HEAD ==='
SELECT version_num
FROM alembic_version;

\echo '=== CONTENT FORMAT CATALOG: EXPECT 21 ==='
SELECT count(*) AS seeded_content_formats
FROM content_formats
WHERE metadata ->> 'seed_set' = 'gfa_d_1';

\echo '=== ACQUISITION ENVELOPE LEAKAGE: EXPECT 0 ==='
SELECT count(*) AS invalid_content_formats
FROM content_formats
WHERE slug IN ('rss', 'atom', 'json_feed');

\echo '=== INVALID CURRENT CONTENT FORMAT REFERENCES: EXPECT 0 ==='
SELECT count(*) AS invalid_documents
FROM documents AS document
LEFT JOIN content_formats AS format
  ON format.slug = document.content_format
WHERE format.id IS NULL;

\echo '=== INVALID HISTORICAL CONTENT FORMAT REFERENCES: EXPECT 0 ==='
SELECT count(*) AS invalid_versions
FROM document_versions AS version
LEFT JOIN content_formats AS format
  ON format.slug = version.content_format
WHERE format.id IS NULL;

\echo '=== INVALID INGESTION FORMAT REFERENCES: EXPECT 0 ==='
SELECT count(*) AS invalid_documents
FROM documents AS document
LEFT JOIN endpoint_formats AS format
  ON format.slug = document.ingestion_format
WHERE format.id IS NULL;

\echo '=== LEGACY DOCUMENT SOURCE TYPE COLUMN: EXPECT 0 ==='
SELECT count(*) AS legacy_columns
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'documents'
  AND column_name = 'source_type';

\echo '=== LEGACY DOCUMENT SOURCE TYPE INDEXES: EXPECT 0 ==='
SELECT count(*) AS legacy_indexes
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'documents'
  AND indexname IN (
      'ix_documents_source_type',
      'ix_documents_source_type_published_at'
  );

\echo '=== DOCUMENT FORMAT DISTRIBUTION ==='
SELECT content_format, count(*) AS documents
FROM documents
GROUP BY content_format
ORDER BY documents DESC, content_format;

\echo '=== DOCUMENT VERSION FORMAT DISTRIBUTION ==='
SELECT content_format, count(*) AS versions
FROM document_versions
GROUP BY content_format
ORDER BY versions DESC, content_format;
