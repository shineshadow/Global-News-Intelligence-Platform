-- Platform-governed geography foundation verification.

SELECT geography_type, COUNT(*) AS rows
FROM geographies
GROUP BY geography_type
ORDER BY geography_type;

-- Expected total: 286.
SELECT COUNT(*) AS total_geographies
FROM geographies;

-- Taiwan must be a first-class country.
SELECT
    child.slug,
    child.name,
    child.geography_type,
    child.iso_alpha2,
    child.iso_alpha3,
    parent.slug AS geographic_parent,
    child.metadata
FROM geographies child
LEFT JOIN geographies parent
    ON parent.id = child.parent_id
WHERE child.slug = 'taiwan';

-- All must be separately present.
SELECT
    slug,
    name,
    geography_type,
    metadata->>'platform_status' AS platform_status
FROM geographies
WHERE slug IN (
    'taiwan',
    'hong-kong',
    'macao',
    'tibet',
    'east-turkistan',
    'southern-mongolia',
    'palestine',
    'western-sahara',
    'kosovo',
    'kurdistan',
    'somaliland'
)
ORDER BY slug;

-- Expected: zero.
SELECT slug, name
FROM geographies
WHERE slug <> 'world'
  AND parent_id IS NULL;

-- Expected: no duplicate ISO codes.
SELECT iso_alpha2, COUNT(*)
FROM geographies
WHERE iso_alpha2 IS NOT NULL
GROUP BY iso_alpha2
HAVING COUNT(*) > 1;

SELECT iso_alpha3, COUNT(*)
FROM geographies
WHERE iso_alpha3 IS NOT NULL
GROUP BY iso_alpha3
HAVING COUNT(*) > 1;

-- Confirm corrected source jurisdictions/defaults.
SELECT
    id,
    name,
    country,
    metadata->'classification_defaults'
        AS classification_defaults
FROM sources
WHERE name IN (
    'The Diplomat',
    'ASPI / The Strategist',
    'Lowy Institute / The Interpreter',
    'Naval News',
    'International Atomic Energy Agency (IAEA)',
    'Daily NK',
    'NK Leadership Watch',
    'North Korea Tech',
    '38 North'
)
ORDER BY name;
