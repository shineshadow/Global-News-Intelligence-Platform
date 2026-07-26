\set ON_ERROR_STOP on

\echo '=== GFA-C MIGRATION HEAD ==='
SELECT version_num
FROM alembic_version;

\echo '=== REQUIRED GFA-C TABLES: EXPECT 13 ==='
WITH required(table_name) AS (
    VALUES
        ('semantic_assignment_methods'),
        ('entity_types'),
        ('entity_type_hierarchy_edges'),
        ('entity_type_assignments'),
        ('external_semantic_authorities'),
        ('external_semantic_schemes'),
        ('external_semantic_resource_kinds'),
        ('external_semantic_resources'),
        ('semantic_mapping_relations'),
        ('entity_type_external_mappings'),
        ('entity_geography_relationship_types'),
        ('entity_geographies'),
        ('entity_geography_relationship_type_external_mappings')
)
SELECT count(*) AS present_tables
FROM required
JOIN information_schema.tables USING (table_name)
WHERE table_schema = 'public';

\echo '=== ASSIGNMENT METHODS: EXPECT 6 ==='
SELECT slug
FROM semantic_assignment_methods
ORDER BY slug;

\echo '=== EXTERNAL RESOURCE KINDS: EXPECT 5 ==='
SELECT slug
FROM external_semantic_resource_kinds
ORDER BY slug;

\echo '=== SEMANTIC MAPPING RELATIONS: EXPECT 12 ==='
SELECT
    slug,
    relation_family,
    applicable_resource_kind,
    inverse_slug
FROM semantic_mapping_relations
ORDER BY applicable_resource_kind, slug;

\echo '=== GFA-C.5 ENTITY TYPES: EXPECT 32 ==='
SELECT count(*) AS seeded_entity_types
FROM entity_types
WHERE metadata ->> 'seed_set' = 'gfa_c_5';

\echo '=== GFA-C.5 HIERARCHY EDGES: EXPECT 27 ==='
SELECT count(*) AS seeded_hierarchy_edges
FROM entity_type_hierarchy_edges AS edge
JOIN entity_types AS parent
  ON parent.id = edge.parent_entity_type_id
JOIN entity_types AS child
  ON child.id = edge.child_entity_type_id
WHERE parent.metadata ->> 'seed_set' = 'gfa_c_5'
  AND child.metadata ->> 'seed_set' = 'gfa_c_5';

\echo '=== GFA-C.5 ENTITY-GEOGRAPHY RELATIONSHIPS: EXPECT 10 ==='
SELECT count(*) AS seeded_relationship_types
FROM entity_geography_relationship_types
WHERE metadata ->> 'seed_set' = 'gfa_c_5';

\echo '=== GFA-C.5 EXTERNAL RESOURCES: EXPECT 23 ==='
SELECT resource_kind, count(*) AS seeded_resources
FROM external_semantic_resources
WHERE metadata ->> 'seed_set' = 'gfa_c_5'
GROUP BY resource_kind
ORDER BY resource_kind;

\echo '=== GFA-C.5 ENTITY-TYPE MAPPINGS: EXPECT 29 ==='
SELECT count(*) AS seeded_entity_type_mappings
FROM entity_type_external_mappings
WHERE provenance ->> 'seed_set' = 'gfa_c_5';

\echo '=== GFA-C.5 RELATIONSHIP MAPPINGS: EXPECT 5 ==='
SELECT count(*) AS seeded_relationship_mappings
FROM entity_geography_relationship_type_external_mappings
WHERE provenance ->> 'seed_set' = 'gfa_c_5';

\echo '=== ENTITY-BOUNDARY LEAKAGE: EXPECT 0 ==='
SELECT count(*) AS invalid_entity_types
FROM entity_types
WHERE slug IN (
    'geography',
    'geo_area',
    'event',
    'point_of_interest',
    'abstract'
);

\echo '=== INVENTED UNCERTAIN PROPERTY MAPPINGS: EXPECT 0 ==='
SELECT count(*) AS uncertain_mappings
FROM entity_geography_relationship_type_external_mappings
WHERE relationship_type IN (
    'jurisdiction_in',
    'operates_in',
    'incorporated_in',
    'resident_in',
    'citizen_of'
)
  AND provenance ->> 'seed_set' = 'gfa_c_5';

\echo '=== DUPLICATE ACTIVE ENTITY-TYPE FACTS: EXPECT 0 ==='
SELECT count(*) AS duplicate_groups
FROM (
    SELECT entity_id, entity_type_id
    FROM entity_type_assignments
    WHERE is_active
    GROUP BY entity_id, entity_type_id
    HAVING count(*) > 1
) AS duplicates;

\echo '=== MULTIPLE ACTIVE PRIMARY ENTITY TYPES: EXPECT 0 ==='
SELECT count(*) AS invalid_entities
FROM (
    SELECT entity_id
    FROM entity_type_assignments
    WHERE is_active
      AND is_primary
    GROUP BY entity_id
    HAVING count(*) > 1
) AS invalid;

\echo '=== DUPLICATE ACTIVE ENTITY-GEOGRAPHY FACTS: EXPECT 0 ==='
SELECT count(*) AS duplicate_groups
FROM (
    SELECT entity_id, geography_id, relationship_type
    FROM entity_geographies
    WHERE is_active
    GROUP BY entity_id, geography_id, relationship_type
    HAVING count(*) > 1
) AS duplicates;

\echo '=== CONTRADICTORY ACTIVE ENTITY-TYPE MAPPINGS: EXPECT 0 ==='
SELECT count(*) AS contradictory_pairs
FROM (
    SELECT entity_type_id, external_resource_id
    FROM entity_type_external_mappings
    WHERE is_active
    GROUP BY entity_type_id, external_resource_id
    HAVING count(*) > 1
) AS contradictory;

\echo '=== CONTRADICTORY ACTIVE RELATIONSHIP-PROPERTY MAPPINGS: EXPECT 0 ==='
SELECT count(*) AS contradictory_pairs
FROM (
    SELECT relationship_type, external_resource_id
    FROM entity_geography_relationship_type_external_mappings
    WHERE is_active
    GROUP BY relationship_type, external_resource_id
    HAVING count(*) > 1
) AS contradictory;

\echo '=== INVALID CONFIDENCE OR VALIDITY: EXPECT 0 ==='
SELECT count(*) AS invalid_assertions
FROM (
    SELECT confidence, valid_from, valid_to
    FROM entity_type_assignments
    UNION ALL
    SELECT confidence, valid_from, valid_to
    FROM entity_type_external_mappings
    UNION ALL
    SELECT confidence, valid_from, valid_to
    FROM entity_geographies
    UNION ALL
    SELECT confidence, valid_from, valid_to
    FROM entity_geography_relationship_type_external_mappings
) AS assertions
WHERE (
    confidence IS NOT NULL
    AND (confidence < 0 OR confidence > 1)
)
OR (
    valid_from IS NOT NULL
    AND valid_to IS NOT NULL
    AND valid_to < valid_from
);

\echo '=== INVALID EXTERNAL MAPPING KIND PAIRS: EXPECT 0 ==='
SELECT count(*) AS invalid_mappings
FROM (
    SELECT
        mapping.external_resource_id,
        mapping.resource_kind,
        mapping.mapping_relation
    FROM entity_type_external_mappings AS mapping

    UNION ALL

    SELECT
        mapping.external_resource_id,
        mapping.resource_kind,
        mapping.mapping_relation
    FROM entity_geography_relationship_type_external_mappings AS mapping
) AS mapping
JOIN external_semantic_resources AS resource
  ON resource.id = mapping.external_resource_id
JOIN semantic_mapping_relations AS relation
  ON relation.slug = mapping.mapping_relation
WHERE mapping.resource_kind <> resource.resource_kind
   OR mapping.resource_kind <> relation.applicable_resource_kind;

\echo '=== LEGACY COMPATIBILITY COLUMNS: EXPECT 0 AFTER GFA-C.6 ==='
SELECT count(*) AS legacy_columns
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'entities'
  AND column_name IN (
      'entity_type',
      'country_or_jurisdiction'
  );

\echo '=== LEGACY COMPATIBILITY INDEXES: EXPECT 0 AFTER GFA-C.6 ==='
SELECT count(*) AS legacy_indexes
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'entities'
  AND indexname IN (
      'ix_entities_type_active',
      'ix_entities_country_or_jurisdiction'
  );
