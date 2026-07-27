\set ON_ERROR_STOP on

\echo '=== STEP 25 MIGRATION HEAD ==='
SELECT version_num
FROM alembic_version;

\echo '=== STEP 25 TABLES: EXPECT 13 ==='
SELECT count(*) AS monitor_rule_tables
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'monitors',
      'monitor_revisions',
      'monitor_revision_geographies',
      'monitor_revision_topics',
      'monitor_revision_entities',
      'monitor_revision_entity_roles',
      'monitor_revision_document_types',
      'monitor_revision_content_formats',
      'monitor_revision_sources',
      'monitor_revision_source_types',
      'monitor_revision_languages',
      'monitor_evaluation_runs',
      'monitor_matches'
  );

\echo '=== MONITORS WITHOUT A CURRENT REVISION: EXPECT 0 ==='
SELECT count(*) AS invalid_current_revisions
FROM monitors AS monitor
LEFT JOIN monitor_revisions AS revision
  ON revision.monitor_id = monitor.id
 AND revision.revision_number = monitor.current_revision_number
 AND revision.sealed_at IS NOT NULL
WHERE revision.id IS NULL;

\echo '=== UNSEALED OR MIXED-POLICY REVISIONS: EXPECT BOTH ZERO ==='
SELECT
    (SELECT count(*)
     FROM monitor_revisions
     WHERE sealed_at IS NULL) AS unsealed_revisions,
    (SELECT count(*)
     FROM (
         SELECT revision_id
         FROM monitor_revision_geographies
         GROUP BY revision_id
         HAVING count(DISTINCT include_descendants) > 1
         UNION ALL
         SELECT revision_id
         FROM monitor_revision_topics
         GROUP BY revision_id
         HAVING count(DISTINCT include_descendants) > 1
         UNION ALL
         SELECT revision_id
         FROM monitor_revision_document_types
         GROUP BY revision_id
         HAVING count(DISTINCT include_descendants) > 1
         UNION ALL
         SELECT revision_id
         FROM monitor_revision_source_types
         GROUP BY revision_id
         HAVING count(DISTINCT include_descendants) > 1
     ) AS mixed) AS mixed_hierarchy_policies;

\echo '=== DUPLICATE LOGICAL MATCHES: EXPECT 0 ==='
SELECT count(*) AS duplicate_monitor_document_pairs
FROM (
    SELECT monitor_id, document_id
    FROM monitor_matches
    GROUP BY monitor_id, document_id
    HAVING count(*) > 1
) AS duplicates;

\echo '=== CROSS-MONITOR EVALUATION PROVENANCE: EXPECT 0 ==='
SELECT count(*) AS cross_monitor_evaluation_references
FROM monitor_matches AS match
LEFT JOIN monitor_evaluation_runs AS first_run
  ON first_run.id = match.first_evaluation_run_id
LEFT JOIN monitor_evaluation_runs AS last_run
  ON last_run.id = match.last_evaluation_run_id
WHERE (
    match.first_evaluation_run_id IS NOT NULL
    AND first_run.monitor_id IS DISTINCT FROM match.monitor_id
) OR (
    match.last_evaluation_run_id IS NOT NULL
    AND last_run.monitor_id IS DISTINCT FROM match.monitor_id
);

\echo '=== INVALID MATCH ACCUMULATION: EXPECT 0 ==='
SELECT count(*) AS invalid_match_history
FROM monitor_matches
WHERE observation_count < 1
   OR last_matched_at < first_matched_at;

\echo '=== INVALID EVALUATION COUNTS: EXPECT 0 ==='
SELECT count(*) AS invalid_evaluation_counts
FROM monitor_evaluation_runs
WHERE candidate_count < 0
   OR matched_count < 0
   OR new_match_count < 0
   OR matched_count > candidate_count
   OR new_match_count > matched_count;

\echo '=== SELECTOR JSON COLUMNS: EXPECT 0 ==='
SELECT count(*) AS selector_json_columns
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'monitor_revisions'
  AND data_type IN ('json', 'jsonb');

\echo '=== STEP 26 TABLES: EXPECT 0 ==='
SELECT count(*) AS premature_alert_tables
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
      table_name LIKE 'alert%'
      OR table_name LIKE 'notification%'
      OR table_name LIKE 'delivery%'
  );

\echo '=== MONITOR LIFECYCLE DISTRIBUTION ==='
SELECT status, count(*) AS monitor_count
FROM monitors
GROUP BY status
ORDER BY status;
