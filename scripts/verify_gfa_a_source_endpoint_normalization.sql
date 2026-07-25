-- GFA-A verification

\echo ''
\echo '=== REVISION ==='
SELECT version_num
FROM alembic_version;

\echo ''
\echo '=== REFERENCE VOCABULARY COUNTS ==='
SELECT 'source_types' AS vocabulary, COUNT(*) AS rows
FROM source_types
UNION ALL
SELECT 'endpoint_types', COUNT(*) FROM endpoint_types
UNION ALL
SELECT 'endpoint_formats', COUNT(*) FROM endpoint_formats
UNION ALL
SELECT 'acquisition_methods', COUNT(*) FROM acquisition_methods
UNION ALL
SELECT 'platforms', COUNT(*) FROM platforms
ORDER BY vocabulary;

\echo ''
\echo '=== NORMALIZED SOURCE TYPES ==='
SELECT source_type, COUNT(*) AS sources
FROM sources
GROUP BY source_type
ORDER BY sources DESC, source_type;

\echo ''
\echo '=== ENDPOINT DIMENSIONS ==='
SELECT
    endpoint_type,
    endpoint_format,
    acquisition_method,
    platform,
    COUNT(*) AS endpoints
FROM source_endpoints
GROUP BY
    endpoint_type,
    endpoint_format,
    acquisition_method,
    platform
ORDER BY endpoints DESC;

\echo ''
\echo '=== INVALID SOURCE TYPE REFERENCES: EXPECT 0 ==='
SELECT COUNT(*) AS invalid_source_types
FROM sources s
LEFT JOIN source_types st
    ON st.slug = s.source_type
WHERE st.id IS NULL;

\echo ''
\echo '=== INVALID ENDPOINT REFERENCES: EXPECT ALL 0 ==='
SELECT
    COUNT(*) FILTER (
        WHERE et.id IS NULL
    ) AS invalid_endpoint_types,
    COUNT(*) FILTER (
        WHERE ef.id IS NULL
    ) AS invalid_endpoint_formats,
    COUNT(*) FILTER (
        WHERE am.id IS NULL
    ) AS invalid_acquisition_methods,
    COUNT(*) FILTER (
        WHERE se.platform IS NOT NULL
          AND p.id IS NULL
    ) AS invalid_platforms
FROM source_endpoints se
LEFT JOIN endpoint_types et
    ON et.slug = se.endpoint_type
LEFT JOIN endpoint_formats ef
    ON ef.slug = se.endpoint_format
LEFT JOIN acquisition_methods am
    ON am.slug = se.acquisition_method
LEFT JOIN platforms p
    ON p.slug = se.platform;

\echo ''
\echo '=== DOCUMENT INGESTION FORMAT ==='
SELECT
    ingestion_format,
    COUNT(*) AS documents
FROM documents
GROUP BY ingestion_format
ORDER BY documents DESC, ingestion_format;

\echo ''
\echo '=== INGESTION FORMAT / LEGACY MISMATCH: EXPECT 0 ==='
SELECT COUNT(*) AS mismatches
FROM documents
WHERE ingestion_format <> source_type;

\echo ''
\echo '=== END GFA-A VERIFICATION ==='
