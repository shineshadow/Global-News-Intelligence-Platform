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
WHERE revision.id IS NULL;

\echo '=== DUPLICATE LOGICAL MATCHES: EXPECT 0 ==='
SELECT count(*) AS duplicate_monitor_document_pairs
FROM (
    SELECT monitor_id, document_id
    FROM monitor_matches
    GROUP BY monitor_id, document_id
    HAVING count(*) > 1
) AS duplicates;

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
