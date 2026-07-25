-- Step 23 deterministic classification inspection queries.

-- Recent deterministic classification runs.
SELECT
    cr.id,
    cr.document_id,
    cr.status,
    cr.pipeline_version,
    cr.ruleset_version,
    cr.taxonomy_version,
    cr.started_at,
    cr.completed_at,
    cr.error
FROM classification_runs cr
WHERE cr.pipeline_version = 'deterministic-v1'
ORDER BY cr.id DESC
LIMIT 50;

-- Active topic classifications.
SELECT
    d.id AS document_id,
    left(d.title_original, 120) AS title,
    t.slug AS topic,
    dt.relationship_role,
    dt.confidence,
    dt.classification_method,
    dt.classifier_version
FROM document_topics dt
JOIN documents d ON d.id = dt.document_id
JOIN topics t ON t.id = dt.topic_id
WHERE dt.is_active
ORDER BY d.id DESC, dt.confidence DESC
LIMIT 100;

-- Active geography classifications.
SELECT
    d.id AS document_id,
    left(d.title_original, 120) AS title,
    g.slug AS geography,
    dg.relationship_role,
    dg.confidence,
    dg.classification_method
FROM document_geographies dg
JOIN documents d ON d.id = dg.document_id
JOIN geographies g ON g.id = dg.geography_id
WHERE dg.is_active
ORDER BY d.id DESC, dg.confidence DESC
LIMIT 100;

-- Active semantic document types.
SELECT
    d.id AS document_id,
    left(d.title_original, 120) AS title,
    dtype.slug AS document_type,
    dta.is_primary,
    dta.confidence,
    dta.classification_method
FROM document_type_assignments dta
JOIN documents d ON d.id = dta.document_id
JOIN document_types dtype
    ON dtype.id = dta.document_type_id
WHERE dta.is_active
ORDER BY d.id DESC, dta.is_primary DESC, dta.confidence DESC
LIMIT 100;

-- Active resolved entities.
SELECT
    d.id AS document_id,
    left(d.title_original, 120) AS title,
    e.canonical_name,
    de.mention_text,
    de.entity_role,
    de.confidence,
    de.classification_method
FROM document_entities de
JOIN documents d ON d.id = de.document_id
JOIN entities e ON e.id = de.entity_id
WHERE de.is_active
ORDER BY d.id DESC, de.confidence DESC
LIMIT 100;
