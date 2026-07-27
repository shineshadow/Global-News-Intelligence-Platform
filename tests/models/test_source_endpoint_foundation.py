from sqlalchemy import func, select

from app.models import (
    AcquisitionMethod,
    Document,
    EndpointFormat,
    EndpointType,
    Platform,
    SourceType,
)


async def test_global_source_reference_vocabularies_are_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        counts = {
            "source_types": await session.scalar(
                select(func.count(SourceType.id))
            ),
            "endpoint_types": await session.scalar(
                select(func.count(EndpointType.id))
            ),
            "endpoint_formats": await session.scalar(
                select(func.count(EndpointFormat.id))
            ),
            "acquisition_methods": await session.scalar(
                select(func.count(AcquisitionMethod.id))
            ),
            "platforms": await session.scalar(
                select(func.count(Platform.id))
            ),
        }

    assert counts == {
        "source_types": 41,
        "endpoint_types": 10,
        "endpoint_formats": 16,
        "acquisition_methods": 14,
        "platforms": 20,
    }


async def test_legacy_source_type_migration_targets_are_seeded(
    database_session_factory,
):
    expected = {
        "news_organization",
        "research_institute",
        "news_agency",
        "government",
        "legislature",
        "international_organization",
    }

    async with database_session_factory() as session:
        seeded = set(
            (
                await session.scalars(
                    select(SourceType.slug).where(
                        SourceType.slug.in_(expected)
                    )
                )
            ).all()
        )

    assert seeded == expected


async def test_feed_reference_values_are_seeded(
    database_session_factory,
):
    async with database_session_factory() as session:
        endpoint_types = set(
            (
                await session.scalars(
                    select(EndpointType.slug).where(
                        EndpointType.slug == "feed"
                    )
                )
            ).all()
        )
        endpoint_formats = set(
            (
                await session.scalars(
                    select(EndpointFormat.slug).where(
                        EndpointFormat.slug.in_(
                            {"rss", "atom"}
                        )
                    )
                )
            ).all()
        )
        acquisition_methods = set(
            (
                await session.scalars(
                    select(AcquisitionMethod.slug).where(
                        AcquisitionMethod.slug == "feed_parser"
                    )
                )
            ).all()
        )

    assert endpoint_types == {"feed"}
    assert endpoint_formats == {"rss", "atom"}
    assert acquisition_methods == {"feed_parser"}


def test_document_ingestion_format_is_required_and_reference_backed():
    column = Document.__table__.c.ingestion_format

    assert column.nullable is False

    foreign_keys = {
        (
            foreign_key.column.table.name,
            foreign_key.column.name,
        )
        for foreign_key in column.foreign_keys
    }

    assert foreign_keys == {
        ("endpoint_formats", "slug")
    }
