from decimal import Decimal

import pytest
from sqlalchemy import select

from app.classification.normalization import normalize_alias
from app.models import (
    Document,
    DocumentEntity,
    DocumentGeography,
    DocumentTopic,
    DocumentType,
    DocumentTypeAssignment,
    Entity,
    EntityAlias,
    Geography,
    Source,
    SourceEndpoint,
    Topic,
)
from app.services.classification_service import (
    classify_document_deterministically,
)


async def _create_document(
    session,
    *,
    title: str,
    source_country: str = "South Korea",
    source_metadata: dict | None = None,
    endpoint_metadata: dict | None = None,
    document_metadata: dict | None = None,
) -> Document:
    source = Source(
        name=f"Test Source {title[:20]}",
        country=source_country,
        primary_language="en",
        source_type="news_organization",
        status="active",
        priority="normal",
        source_metadata=source_metadata or {},
    )
    session.add(source)
    await session.flush()

    endpoint = SourceEndpoint(
        source_id=source.id,
        name="Test Endpoint",
        endpoint_type="feed",
        endpoint_format="rss",
        acquisition_method="feed_parser",
        url=f"https://example.com/{source.id}/feed.xml",
        status="active",
        endpoint_metadata=endpoint_metadata or {},
    )
    session.add(endpoint)
    await session.flush()

    document = Document(
        source_id=source.id,
        source_endpoint_id=endpoint.id,
        source_type="rss",
        ingestion_format="rss",
        external_id=f"item-{source.id}",
        canonical_url=f"https://example.com/{source.id}/item",
        title_original=title,
        summary_original=None,
        content_original=None,
        language="en",
        country=source_country,
        author=None,
        content_hash=(f"{source.id:064x}"[-64:]),
        document_metadata=document_metadata or {},
    )
    session.add(document)
    await session.flush()

    return document


@pytest.mark.asyncio
async def test_source_country_and_keyword_topic_are_persisted(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            document = await _create_document(
                session,
                title="Central bank raises interest rate",
            )

            summary = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )

            assert summary.status == "succeeded"

            topic_row = (
                await session.execute(
                    select(DocumentTopic, Topic)
                    .join(
                        Topic,
                        Topic.id
                        == DocumentTopic.topic_id,
                    )
                    .where(
                        DocumentTopic.document_id
                        == document.id,
                        DocumentTopic.is_active.is_(
                            True
                        ),
                    )
                )
            ).one()

            assert topic_row.Topic.slug == "economy"
            assert (
                topic_row.DocumentTopic
                .classification_method
                == "deterministic_rule"
            )

            geography_row = (
                await session.execute(
                    select(
                        DocumentGeography,
                        Geography,
                    )
                    .join(
                        Geography,
                        Geography.id
                        == DocumentGeography.geography_id,
                    )
                    .where(
                        DocumentGeography.document_id
                        == document.id,
                        DocumentGeography.is_active.is_(
                            True
                        ),
                    )
                )
            ).one()

            assert (
                geography_row.Geography.slug
                == "south-korea"
            )
            assert (
                geography_row.DocumentGeography
                .relationship_role
                == "publisher_context"
            )
            assert (
                geography_row.DocumentGeography
                .classification_method
                == "source_default"
            )


@pytest.mark.asyncio
async def test_explicit_source_and_endpoint_defaults(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            document = await _create_document(
                session,
                title="Routine official update",
                source_metadata={
                    "classification_defaults": {
                        "topics": [
                            {
                                "slug": "foreign-affairs",
                                "role": "primary",
                                "confidence": 0.96,
                            }
                        ]
                    }
                },
                endpoint_metadata={
                    "classification_defaults": {
                        "document_types": [
                            {
                                "slug": "government_release",
                                "primary": True,
                                "confidence": 0.99,
                            }
                        ]
                    }
                },
            )

            summary = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )

            assert summary.status == "succeeded"

            topic = (
                await session.execute(
                    select(DocumentTopic, Topic)
                    .join(
                        Topic,
                        Topic.id
                        == DocumentTopic.topic_id,
                    )
                    .where(
                        DocumentTopic.document_id
                        == document.id,
                        DocumentTopic.is_active.is_(
                            True
                        ),
                        Topic.slug
                        == "foreign-affairs",
                    )
                )
            ).one()

            assert (
                topic.DocumentTopic
                .classification_method
                == "source_default"
            )

            assignment = (
                await session.execute(
                    select(
                        DocumentTypeAssignment,
                        DocumentType,
                    )
                    .join(
                        DocumentType,
                        DocumentType.id
                        == DocumentTypeAssignment
                        .document_type_id,
                    )
                    .where(
                        DocumentTypeAssignment.document_id
                        == document.id,
                        DocumentTypeAssignment.is_active.is_(
                            True
                        ),
                    )
                )
            ).one()

            assert (
                assignment.DocumentType.slug
                == "government_release"
            )
            assert (
                assignment.DocumentTypeAssignment
                .classification_method
                == "endpoint_default"
            )
            assert (
                assignment.DocumentTypeAssignment
                .is_primary
                is True
            )


@pytest.mark.asyncio
async def test_entity_alias_matching(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            entity = Entity(
                canonical_name=(
                    "National Election Commission "
                    "of South Korea"
                ),
                entity_metadata={},
            )
            session.add(entity)
            await session.flush()

            alias_text = "National Election Commission"
            alias = EntityAlias(
                entity_id=entity.id,
                alias=alias_text,
                language="en",
                alias_type="name",
                normalized_alias=normalize_alias(
                    alias_text
                ),
            )
            session.add(alias)
            await session.flush()

            document = await _create_document(
                session,
                title=(
                    "National Election Commission "
                    "announces new guidance"
                ),
            )

            summary = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )

            assert summary.status == "succeeded"
            assert summary.entities == 1

            row = await session.scalar(
                select(DocumentEntity).where(
                    DocumentEntity.document_id
                    == document.id,
                    DocumentEntity.is_active.is_(True),
                )
            )

            assert row is not None
            assert row.entity_id == entity.id
            assert (
                row.classification_method
                == "deterministic_rule"
            )
            assert row.mention_text == alias_text


@pytest.mark.asyncio
async def test_manual_topic_override_is_preserved(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            document = await _create_document(
                session,
                title="Election campaign begins",
            )
            politics = await session.scalar(
                select(Topic).where(
                    Topic.slug == "politics"
                )
            )
            assert politics is not None

            manual = DocumentTopic(
                document_id=document.id,
                topic_id=politics.id,
                confidence=Decimal("1.0000"),
                relationship_role="primary",
                classification_method="manual",
                classifier_version=None,
                taxonomy_version="1.0",
                classification_run_id=None,
                is_manual_override=True,
                override_actor_type="operator",
                override_actor_key="local",
                override_reason="Test correction",
                evidence={},
                is_active=True,
            )
            session.add(manual)
            await session.flush()

            summary = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )

            assert summary.status == "succeeded"

            active_politics = (
                await session.scalars(
                    select(DocumentTopic)
                    .where(
                        DocumentTopic.document_id
                        == document.id,
                        DocumentTopic.topic_id
                        == politics.id,
                        DocumentTopic.is_active.is_(
                            True
                        ),
                    )
                )
            ).all()

            assert len(active_politics) == 1
            assert (
                active_politics[0].is_manual_override
                is True
            )
            assert (
                active_politics[0].override_actor_key
                == "local"
            )


@pytest.mark.asyncio
async def test_matching_successful_run_is_skipped(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            document = await _create_document(
                session,
                title="Semiconductor industry update",
            )

            first = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )
            second = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )

            assert first.status == "succeeded"
            assert second.status == "skipped"
            assert second.run_id == first.run_id
            assert (
                second.skipped_reason
                == "matching_successful_run"
            )


@pytest.mark.asyncio
async def test_only_one_active_primary_document_type(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            document = await _create_document(
                session,
                title="Breaking News: Press Release on new policy",
            )

            summary = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )

            assert summary.status == "succeeded"

            assignments = (
                await session.scalars(
                    select(
                        DocumentTypeAssignment
                    ).where(
                        DocumentTypeAssignment.document_id
                        == document.id,
                        DocumentTypeAssignment.is_active.is_(
                            True
                        ),
                    )
                )
            ).all()

            assert len(assignments) >= 1
            assert sum(
                1
                for row in assignments
                if row.is_primary
            ) == 1


@pytest.mark.asyncio
async def test_bad_default_fails_classification_not_document(
    database_session_factory,
):
    async with database_session_factory() as session:
        async with session.begin():
            document = await _create_document(
                session,
                title="Routine update",
                source_metadata={
                    "classification_defaults": {
                        "topics": [
                            {
                                "slug": "not-a-real-topic",
                                "role": "primary",
                            }
                        ]
                    }
                },
            )

            summary = await classify_document_deterministically(
                session,
                document.id,
                trigger="test",
            )

            assert summary.status == "failed"
            assert "not-a-real-topic" in (
                summary.error or ""
            )

            preserved = await session.get(
                Document,
                document.id,
            )
            assert preserved is not None
