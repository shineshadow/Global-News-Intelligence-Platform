"""seed the GFA-C.5 standards-derived vocabulary

Revision ID: c51d8e2f4a90
Revises: a84c1d9e7f32
Create Date: 2026-07-26

This migration seeds the reviewed GFA-C.5 entity-type DAG,
entity-geography relationship vocabulary, external semantic authorities
and schemes, and conservative IPTC/Schema.org mappings.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c51d8e2f4a90"
down_revision: str | Sequence[str] | None = "a84c1d9e7f32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_SET = "gfa_c_5"
VERIFIED_AT = datetime(2026, 7, 26, tzinfo=UTC)

ENTITY_TYPES = (
    ("person", "Person", "An individual human being."),
    ("organization", "Organization", "A structured group with a persistent identity."),
    ("animal", "Animal", "An individually identifiable non-human animal."),
    ("object", "Object", "An identifiable real-world non-agentive thing."),
    ("other", "Other", "An entity that cannot yet be assigned a more specific canonical type."),
    (
        "government_organization",
        "Government organization",
        "A government body, agency, authority, or other governmental organization.",
    ),
    ("legislature", "Legislature", "A law-making assembly or legislative body."),
    ("court", "Court", "A judicial institution or tribunal."),
    (
        "election_authority",
        "Election authority",
        "An organization responsible for administering or supervising elections.",
    ),
    ("military", "Military", "An armed service, force, command, or military organization."),
    (
        "law_enforcement",
        "Law enforcement",
        "An organization with policing or other law-enforcement authority.",
    ),
    ("company", "Company", "A commercial business organization."),
    ("political_party", "Political party", "An organization formed for political activity."),
    (
        "international_organization",
        "International organization",
        "An organization whose membership or mandate spans multiple countries.",
    ),
    (
        "non_governmental_organization",
        "Non-governmental organization",
        "A non-governmental and generally non-profit organization.",
    ),
    ("university", "University", "A degree-granting higher-education organization."),
    ("think_tank", "Think tank", "An organization conducting policy-oriented research."),
    ("labor_union", "Labor union", "An organization representing workers."),
    (
        "news_media_organization",
        "News media organization",
        "An organization that produces or publishes journalistic news.",
    ),
    (
        "facility",
        "Facility",
        "An identifiable constructed site or operational facility; geography and POI remain separate.",
    ),
    (
        "legal_instrument",
        "Legal instrument",
        "An identifiable instrument that creates, records, or governs legal rights or duties.",
    ),
    ("court_case", "Court case", "An identifiable judicial proceeding or case."),
    ("treaty", "Treaty", "An identifiable agreement governed by international law."),
    (
        "technology_product",
        "Technology product",
        "An identifiable technology, technical product, or product family.",
    ),
    ("software", "Software", "An identifiable software system, package, or application."),
    ("ai_model", "AI model", "An identifiable artificial-intelligence model or model family."),
    (
        "weapon_system",
        "Weapon system",
        "An identifiable weapon, weapon platform, or integrated weapon system.",
    ),
    ("vehicle", "Vehicle", "An identifiable means or model of transport."),
    ("aircraft", "Aircraft", "An identifiable aircraft or aircraft model."),
    ("vessel", "Vessel", "An identifiable waterborne vessel or vessel model."),
    ("spacecraft", "Spacecraft", "An identifiable spacecraft or spacecraft model."),
    (
        "program_initiative",
        "Program or initiative",
        "An identifiable organized program, initiative, or campaign.",
    ),
)

ENTITY_TYPE_EDGES = (
    ("organization", "government_organization"),
    ("government_organization", "legislature"),
    ("government_organization", "court"),
    ("government_organization", "election_authority"),
    ("government_organization", "military"),
    ("government_organization", "law_enforcement"),
    ("organization", "company"),
    ("organization", "political_party"),
    ("organization", "international_organization"),
    ("organization", "non_governmental_organization"),
    ("organization", "university"),
    ("organization", "think_tank"),
    ("organization", "labor_union"),
    ("organization", "news_media_organization"),
    ("object", "facility"),
    ("object", "legal_instrument"),
    ("legal_instrument", "treaty"),
    ("object", "court_case"),
    ("object", "technology_product"),
    ("technology_product", "software"),
    ("software", "ai_model"),
    ("technology_product", "weapon_system"),
    ("object", "vehicle"),
    ("vehicle", "aircraft"),
    ("vehicle", "vessel"),
    ("vehicle", "spacecraft"),
    ("object", "program_initiative"),
)

RELATIONSHIP_TYPES = (
    (
        "located_in",
        "Located in",
        "The entity is physically located in the geography.",
        ("object", "organization"),
    ),
    (
        "headquartered_in",
        "Headquartered in",
        "The organization maintains a headquarters in the geography.",
        ("organization",),
    ),
    (
        "based_in",
        "Based in",
        "The entity has an established operating base in the geography.",
        ("organization", "person"),
    ),
    (
        "jurisdiction_in",
        "Jurisdiction in",
        "The entity exercises or is governed by jurisdiction in the geography.",
        ("government_organization", "legal_instrument", "court_case"),
    ),
    (
        "operates_in",
        "Operates in",
        "The organization conducts operations in the geography.",
        ("organization",),
    ),
    (
        "incorporated_in",
        "Incorporated in",
        "The organization is legally incorporated in the geography.",
        ("organization",),
    ),
    (
        "founded_in",
        "Founded in",
        "The organization was founded in the geography.",
        ("organization",),
    ),
    (
        "born_in",
        "Born in",
        "The person was born in the geography.",
        ("person",),
    ),
    (
        "resident_in",
        "Resident in",
        "The person resides in the geography during the assertion validity interval.",
        ("person",),
    ),
    (
        "citizen_of",
        "Citizen of",
        "The person holds citizenship or nationality associated with the geography.",
        ("person",),
    ),
)

AUTHORITIES = (
    ("iptc", "International Press Telecommunications Council", "https://iptc.org/"),
    ("schema_org", "Schema.org", "https://schema.org/"),
    ("wikidata", "Wikidata", "https://www.wikidata.org/"),
    ("w3c", "World Wide Web Consortium", "https://www.w3.org/"),
)

SCHEMES = (
    (
        "iptc",
        "iptc_cpnature",
        "IPTC Nature of a Concept",
        "http://cv.iptc.org/newscodes/cpnature/",
        "cpnat",
        None,
        None,
    ),
    (
        "schema_org",
        "schema_org",
        "Schema.org vocabulary",
        "https://schema.org/",
        "schema",
        "30.0",
        date(2026, 3, 19),
    ),
    (
        "wikidata",
        "wikidata",
        "Wikidata knowledge graph",
        "http://www.wikidata.org/entity/",
        "wd",
        None,
        None,
    ),
    (
        "w3c",
        "skos",
        "Simple Knowledge Organization System",
        "http://www.w3.org/2004/02/skos/core#",
        "skos",
        "W3C Recommendation 18 August 2009",
        date(2009, 8, 18),
    ),
)

EXTERNAL_RESOURCES = (
    (
        "iptc_cpnature",
        "concept",
        "cpnat:person",
        "http://cv.iptc.org/newscodes/cpnature/person",
        "person",
    ),
    (
        "iptc_cpnature",
        "concept",
        "cpnat:organisation",
        "http://cv.iptc.org/newscodes/cpnature/organisation",
        "organisation",
    ),
    (
        "iptc_cpnature",
        "concept",
        "cpnat:animal",
        "http://cv.iptc.org/newscodes/cpnature/animal",
        "animal",
    ),
    (
        "iptc_cpnature",
        "concept",
        "cpnat:object",
        "http://cv.iptc.org/newscodes/cpnature/object",
        "object",
    ),
    ("schema_org", "class", "Person", "https://schema.org/Person", "Person"),
    ("schema_org", "class", "Thing", "https://schema.org/Thing", "Thing"),
    ("schema_org", "class", "Organization", "https://schema.org/Organization", "Organization"),
    (
        "schema_org",
        "class",
        "GovernmentOrganization",
        "https://schema.org/GovernmentOrganization",
        "GovernmentOrganization",
    ),
    ("schema_org", "class", "Corporation", "https://schema.org/Corporation", "Corporation"),
    (
        "schema_org",
        "class",
        "PoliticalParty",
        "https://schema.org/PoliticalParty",
        "PoliticalParty",
    ),
    ("schema_org", "class", "NGO", "https://schema.org/NGO", "NGO"),
    (
        "schema_org",
        "class",
        "CollegeOrUniversity",
        "https://schema.org/CollegeOrUniversity",
        "CollegeOrUniversity",
    ),
    (
        "schema_org",
        "class",
        "ResearchOrganization",
        "https://schema.org/ResearchOrganization",
        "ResearchOrganization",
    ),
    ("schema_org", "class", "WorkersUnion", "https://schema.org/WorkersUnion", "WorkersUnion"),
    (
        "schema_org",
        "class",
        "NewsMediaOrganization",
        "https://schema.org/NewsMediaOrganization",
        "NewsMediaOrganization",
    ),
    ("schema_org", "class", "Place", "https://schema.org/Place", "Place"),
    ("schema_org", "class", "Legislation", "https://schema.org/Legislation", "Legislation"),
    ("schema_org", "class", "Product", "https://schema.org/Product", "Product"),
    (
        "schema_org",
        "class",
        "SoftwareApplication",
        "https://schema.org/SoftwareApplication",
        "SoftwareApplication",
    ),
    ("schema_org", "class", "Vehicle", "https://schema.org/Vehicle", "Vehicle"),
    ("schema_org", "property", "location", "https://schema.org/location", "location"),
    (
        "schema_org",
        "property",
        "foundingLocation",
        "https://schema.org/foundingLocation",
        "foundingLocation",
    ),
    ("schema_org", "property", "birthPlace", "https://schema.org/birthPlace", "birthPlace"),
)

ENTITY_TYPE_MAPPINGS = (
    ("person", "iptc_cpnature", "cpnat:person", "exact_match", "concept"),
    ("organization", "iptc_cpnature", "cpnat:organisation", "exact_match", "concept"),
    ("animal", "iptc_cpnature", "cpnat:animal", "exact_match", "concept"),
    ("object", "iptc_cpnature", "cpnat:object", "exact_match", "concept"),
    ("person", "schema_org", "Person", "subclass_of", "class"),
    ("organization", "schema_org", "Organization", "equivalent_class", "class"),
    ("object", "schema_org", "Thing", "subclass_of", "class"),
    (
        "government_organization",
        "schema_org",
        "GovernmentOrganization",
        "equivalent_class",
        "class",
    ),
    ("legislature", "schema_org", "GovernmentOrganization", "subclass_of", "class"),
    ("court", "schema_org", "GovernmentOrganization", "subclass_of", "class"),
    ("election_authority", "schema_org", "GovernmentOrganization", "subclass_of", "class"),
    ("military", "schema_org", "GovernmentOrganization", "subclass_of", "class"),
    ("law_enforcement", "schema_org", "GovernmentOrganization", "subclass_of", "class"),
    ("company", "schema_org", "Corporation", "superclass_of", "class"),
    ("political_party", "schema_org", "PoliticalParty", "equivalent_class", "class"),
    ("international_organization", "schema_org", "Organization", "subclass_of", "class"),
    (
        "non_governmental_organization",
        "schema_org",
        "NGO",
        "equivalent_class",
        "class",
    ),
    ("university", "schema_org", "CollegeOrUniversity", "subclass_of", "class"),
    ("think_tank", "schema_org", "ResearchOrganization", "subclass_of", "class"),
    ("labor_union", "schema_org", "WorkersUnion", "equivalent_class", "class"),
    (
        "news_media_organization",
        "schema_org",
        "NewsMediaOrganization",
        "equivalent_class",
        "class",
    ),
    ("facility", "schema_org", "Place", "subclass_of", "class"),
    ("legal_instrument", "schema_org", "Legislation", "superclass_of", "class"),
    ("technology_product", "schema_org", "Product", "subclass_of", "class"),
    ("software", "schema_org", "SoftwareApplication", "superclass_of", "class"),
    ("vehicle", "schema_org", "Vehicle", "equivalent_class", "class"),
    ("aircraft", "schema_org", "Vehicle", "subclass_of", "class"),
    ("vessel", "schema_org", "Vehicle", "subclass_of", "class"),
    ("spacecraft", "schema_org", "Vehicle", "subclass_of", "class"),
)

RELATIONSHIP_MAPPINGS = (
    ("located_in", "location", "subproperty_of"),
    ("headquartered_in", "location", "subproperty_of"),
    ("based_in", "location", "subproperty_of"),
    ("founded_in", "foundingLocation", "subproperty_of"),
    ("born_in", "birthPlace", "subproperty_of"),
)


def _seed_reference_rows() -> None:
    entity_types = sa.table(
        "entity_types",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("metadata", postgresql.JSONB()),
    )
    op.bulk_insert(
        entity_types,
        [
            {
                "slug": slug,
                "name": name,
                "description": description,
                "metadata": {"seed_set": SEED_SET},
            }
            for slug, name, description in ENTITY_TYPES
        ],
    )

    relationship_types = sa.table(
        "entity_geography_relationship_types",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("metadata", postgresql.JSONB()),
    )
    op.bulk_insert(
        relationship_types,
        [
            {
                "slug": slug,
                "name": name,
                "description": description,
                "metadata": {
                    "seed_set": SEED_SET,
                    "domain_entity_types": list(domain),
                    "domain_includes_descendants": True,
                    "range": "geography",
                    "cardinality": "many",
                },
            }
            for slug, name, description, domain in RELATIONSHIP_TYPES
        ],
    )


def _seed_external_catalog() -> None:
    authorities = sa.table(
        "external_semantic_authorities",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("authority_uri", sa.Text()),
        sa.column("metadata", postgresql.JSONB()),
    )
    op.bulk_insert(
        authorities,
        [
            {
                "slug": slug,
                "name": name,
                "authority_uri": uri,
                "metadata": {"seed_set": SEED_SET, "verified_at": "2026-07-26"},
            }
            for slug, name, uri in AUTHORITIES
        ],
    )

    schemes = sa.table(
        "external_semantic_schemes",
        sa.column("authority_slug", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("scheme_uri", sa.Text()),
        sa.column("preferred_prefix", sa.String()),
        sa.column("version_label", sa.String()),
        sa.column("version_date", sa.Date()),
        sa.column("last_retrieved_at", sa.DateTime(timezone=True)),
        sa.column("metadata", postgresql.JSONB()),
    )
    op.bulk_insert(
        schemes,
        [
            {
                "authority_slug": authority_slug,
                "slug": slug,
                "name": name,
                "scheme_uri": uri,
                "preferred_prefix": prefix,
                "version_label": version_label,
                "version_date": version_date,
                "last_retrieved_at": VERIFIED_AT,
                "metadata": {"seed_set": SEED_SET},
            }
            for (
                authority_slug,
                slug,
                name,
                uri,
                prefix,
                version_label,
                version_date,
            ) in SCHEMES
        ],
    )

    resources = sa.table(
        "external_semantic_resources",
        sa.column("scheme_id", sa.BigInteger()),
        sa.column("resource_kind", sa.String()),
        sa.column("external_identifier", sa.String()),
        sa.column("external_uri", sa.Text()),
        sa.column("name", sa.String()),
        sa.column("metadata", postgresql.JSONB()),
        sa.column("first_retrieved_at", sa.DateTime(timezone=True)),
        sa.column("last_retrieved_at", sa.DateTime(timezone=True)),
    )
    connection = op.get_bind()
    scheme_ids = {
        slug: scheme_id
        for slug, scheme_id in connection.execute(
            sa.text("SELECT slug, id FROM external_semantic_schemes")
        ).tuples()
    }
    op.bulk_insert(
        resources,
        [
            {
                "scheme_id": scheme_ids[scheme_slug],
                "resource_kind": resource_kind,
                "external_identifier": identifier,
                "external_uri": uri,
                "name": name,
                "metadata": {"seed_set": SEED_SET},
                "first_retrieved_at": VERIFIED_AT,
                "last_retrieved_at": VERIFIED_AT,
            }
            for scheme_slug, resource_kind, identifier, uri, name in EXTERNAL_RESOURCES
        ],
    )


def _seed_edges_and_mappings() -> None:
    connection = op.get_bind()
    type_ids = {
        slug: entity_type_id
        for slug, entity_type_id in connection.execute(
            sa.text("SELECT slug, id FROM entity_types")
        ).tuples()
    }
    resource_ids = {
        (scheme_slug, identifier): resource_id
        for scheme_slug, identifier, resource_id in connection.execute(
            sa.text(
                """
                SELECT schemes.slug, resources.external_identifier, resources.id
                FROM external_semantic_resources AS resources
                JOIN external_semantic_schemes AS schemes
                  ON schemes.id = resources.scheme_id
                """
            )
        )
    }

    edges = sa.table(
        "entity_type_hierarchy_edges",
        sa.column("parent_entity_type_id", sa.BigInteger()),
        sa.column("child_entity_type_id", sa.BigInteger()),
    )
    op.bulk_insert(
        edges,
        [
            {
                "parent_entity_type_id": type_ids[parent_slug],
                "child_entity_type_id": type_ids[child_slug],
            }
            for parent_slug, child_slug in ENTITY_TYPE_EDGES
        ],
    )

    entity_mappings = sa.table(
        "entity_type_external_mappings",
        sa.column("entity_type_id", sa.BigInteger()),
        sa.column("external_resource_id", sa.BigInteger()),
        sa.column("mapping_relation", sa.String()),
        sa.column("resource_kind", sa.String()),
        sa.column("provenance", postgresql.JSONB()),
    )
    op.bulk_insert(
        entity_mappings,
        [
            {
                "entity_type_id": type_ids[type_slug],
                "external_resource_id": resource_ids[(scheme_slug, identifier)],
                "mapping_relation": relation,
                "resource_kind": resource_kind,
                "provenance": {"seed_set": SEED_SET, "reviewed_at": "2026-07-26"},
            }
            for type_slug, scheme_slug, identifier, relation, resource_kind in ENTITY_TYPE_MAPPINGS
        ],
    )

    relationship_mappings = sa.table(
        "entity_geography_relationship_type_external_mappings",
        sa.column("relationship_type", sa.String()),
        sa.column("external_resource_id", sa.BigInteger()),
        sa.column("mapping_relation", sa.String()),
        sa.column("resource_kind", sa.String()),
        sa.column("provenance", postgresql.JSONB()),
    )
    op.bulk_insert(
        relationship_mappings,
        [
            {
                "relationship_type": relationship_slug,
                "external_resource_id": resource_ids[("schema_org", identifier)],
                "mapping_relation": relation,
                "resource_kind": "property",
                "provenance": {"seed_set": SEED_SET, "reviewed_at": "2026-07-26"},
            }
            for relationship_slug, identifier, relation in RELATIONSHIP_MAPPINGS
        ],
    )


def upgrade() -> None:
    _seed_reference_rows()
    _seed_external_catalog()
    _seed_edges_and_mappings()


def downgrade() -> None:
    connection = op.get_bind()
    parameters = {"seed_set": SEED_SET}
    statements = (
        """
        DELETE FROM entity_geography_relationship_type_external_mappings
        WHERE provenance ->> 'seed_set' = :seed_set
        """,
        """
        DELETE FROM entity_type_external_mappings
        WHERE provenance ->> 'seed_set' = :seed_set
        """,
        """
        DELETE FROM entity_type_hierarchy_edges
        WHERE parent_entity_type_id IN (
            SELECT id
            FROM entity_types
            WHERE metadata ->> 'seed_set' = :seed_set
        )
        OR child_entity_type_id IN (
            SELECT id
            FROM entity_types
            WHERE metadata ->> 'seed_set' = :seed_set
        )
        """,
        """
        DELETE FROM entity_geography_relationship_types
        WHERE metadata ->> 'seed_set' = :seed_set
        """,
        """
        DELETE FROM entity_types
        WHERE metadata ->> 'seed_set' = :seed_set
        """,
        """
        DELETE FROM external_semantic_resources
        WHERE metadata ->> 'seed_set' = :seed_set
        """,
        """
        DELETE FROM external_semantic_schemes
        WHERE metadata ->> 'seed_set' = :seed_set
        """,
        """
        DELETE FROM external_semantic_authorities
        WHERE metadata ->> 'seed_set' = :seed_set
        """,
    )
    for statement in statements:
        connection.execute(sa.text(statement), parameters)
