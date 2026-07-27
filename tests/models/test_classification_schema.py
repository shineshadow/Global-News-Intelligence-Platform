from sqlalchemy import select, text

from app.models import DocumentType, Geography, Topic


EXPECTED_TOPIC_SLUGS = {
    "politics",
    "law-judiciary",
    "war-security",
    "foreign-affairs",
    "economy",
    "business",
    "technology",
    "energy",
    "health",
    "science",
    "environment",
    "society",
    "crime",
    "immigration",
    "media",
    "education",
    "religion",
    "arts-culture-entertainment",
    "disasters-emergencies",
    "labor-employment",
    "sports",
    "weather",
    "lifestyle-human-interest",
}

EXPECTED_GEOGRAPHY_SLUGS = {
    "united-states",
    "south-korea",
    "japan",
    "taiwan",
    "china",
    "north-korea",
    "philippines",
    "indo-pacific",
}


async def test_classification_tables_exist(database_session_factory):
    table_names = {
        "topics",
        "geographies",
        "entities",
        "entity_aliases",
        "document_types",
        "classification_runs",
        "document_topics",
        "document_geographies",
        "document_entities",
        "document_type_assignments",
    }

    async with database_session_factory() as session:
        rows = await session.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename = ANY(:table_names)
                """
            ),
            {"table_names": list(table_names)},
        )

    assert {row[0] for row in rows} == table_names


async def test_frozen_topic_roots_are_seeded(database_session_factory):
    async with database_session_factory() as session:
        rows = (
            await session.scalars(
                select(Topic)
                .where(Topic.parent_id.is_(None))
                .where(Topic.taxonomy_version == "1.0")
                .order_by(Topic.sort_order)
            )
        ).all()

    assert len(rows) == 23
    assert {row.slug for row in rows} == EXPECTED_TOPIC_SLUGS
    assert all(row.depth == 0 for row in rows)
    assert all(row.is_active for row in rows)


async def test_foundational_geographies_are_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        rows = (
            await session.scalars(
                select(Geography).where(
                    Geography.slug.in_(
                        EXPECTED_GEOGRAPHY_SLUGS
                    )
                )
            )
        ).all()

    assert {row.slug for row in rows} == EXPECTED_GEOGRAPHY_SLUGS
    assert all(row.is_active for row in rows)


async def test_initial_document_types_are_seeded(database_session_factory):
    async with database_session_factory() as session:
        rows = (await session.scalars(select(DocumentType))).all()

    assert len(rows) == 35
    assert "news_report" in {row.slug for row in rows}
    assert "court_decision" in {row.slug for row in rows}
    assert "social_post" in {row.slug for row in rows}
    assert "other" in {row.slug for row in rows}
