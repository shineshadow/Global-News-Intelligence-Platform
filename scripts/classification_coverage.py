import asyncio

from sqlalchemy import text

from app.database import async_session_factory


QUERY = text(
    """
    SELECT
        (SELECT count(*) FROM documents) AS documents,
        (
            SELECT count(DISTINCT document_id)
            FROM classification_runs
            WHERE status = 'succeeded'
              AND pipeline_version = 'deterministic-v1'
        ) AS deterministically_classified,
        (
            SELECT count(DISTINCT document_id)
            FROM document_topics
            WHERE is_active
        ) AS with_topics,
        (
            SELECT count(DISTINCT document_id)
            FROM document_geographies
            WHERE is_active
              AND relationship_role <> 'publisher_context'
        ) AS with_substantive_geography,
        (
            SELECT count(DISTINCT document_id)
            FROM document_geographies
            WHERE is_active
        ) AS with_any_geography,
        (
            SELECT count(DISTINCT document_id)
            FROM document_entities
            WHERE is_active
        ) AS with_entities,
        (
            SELECT count(DISTINCT document_id)
            FROM document_type_assignments
            WHERE is_active
        ) AS with_document_type
    """
)


async def run() -> None:
    async with async_session_factory() as session:
        row = (await session.execute(QUERY)).one()

    labels = [
        "documents",
        "deterministically_classified",
        "with_topics",
        "with_substantive_geography",
        "with_any_geography",
        "with_entities",
        "with_document_type",
    ]

    for label, value in zip(labels, row, strict=True):
        print(f"{label}: {value}")


if __name__ == "__main__":
    asyncio.run(run())
