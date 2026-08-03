from datetime import UTC, datetime

from sqlalchemy import select

from app.models import (
    Document,
    DocumentGeography,
    DocumentTopic,
    Geography,
    Source,
    Topic,
)
from app.schemas.document_match import (
    DocumentMatchCriteria,
    HierarchyIdMatch,
    HierarchySlugMatch,
)
from app.services.document_browser_service import browse_documents
from app.services.document_matching_service import build_document_match_plan


def _document(
    *,
    source_id: int,
    title: str,
    token: str,
) -> Document:
    return Document(
        source_id=source_id,
        source_endpoint_id=None,
        ingestion_format="rss",
        content_format="plain_text",
        external_id=f"step24-{token}",
        canonical_url=f"https://step24.example/{token}",
        title_original=title,
        summary_original=None,
        content_original=None,
        language="en",
        country=None,
        author=None,
        published_at=datetime.now(UTC),
        source_updated_at=None,
        retrieved_at=datetime.now(UTC),
        content_hash=token.ljust(64, "0"),
        document_metadata={},
    )


async def test_matching_contract_ors_within_dimension_and_ands_across(
    database_session_factory,
):
    async with database_session_factory() as session, session.begin():
        source = Source(
            name="Step 24 Matching Source",
            country="Japan",
            primary_language="en",
            source_type="news_organization",
            status="active",
            website_url="https://step24.example",
            source_metadata={},
        )
        session.add(source)
        await session.flush()

        politics = await session.scalar(select(Topic).where(Topic.slug == "politics"))
        economy = await session.scalar(select(Topic).where(Topic.slug == "economy"))
        south_korea = await session.scalar(select(Geography).where(Geography.slug == "south-korea"))
        japan = await session.scalar(select(Geography).where(Geography.slug == "japan"))

        first = _document(
            source_id=source.id,
            title="Politics in Korea",
            token="a",
        )
        second = _document(
            source_id=source.id,
            title="Economy in Japan",
            token="b",
        )
        session.add_all([first, second])
        await session.flush()
        session.add_all(
            [
                DocumentTopic(
                    document_id=first.id,
                    topic_id=politics.id,
                    relationship_role="primary",
                    taxonomy_version="1.0",
                    confidence=0.9,
                    classification_method="deterministic_rule",
                ),
                DocumentTopic(
                    document_id=second.id,
                    topic_id=economy.id,
                    relationship_role="primary",
                    taxonomy_version="1.0",
                    confidence=0.9,
                    classification_method="deterministic_rule",
                ),
                DocumentGeography(
                    document_id=first.id,
                    geography_id=south_korea.id,
                    relationship_role="primary_subject",
                    taxonomy_version="1.0",
                    confidence=0.9,
                    classification_method="deterministic_rule",
                ),
                DocumentGeography(
                    document_id=second.id,
                    geography_id=japan.id,
                    relationship_role="primary_subject",
                    taxonomy_version="1.0",
                    confidence=0.9,
                    classification_method="deterministic_rule",
                ),
            ]
        )

    async with database_session_factory() as session:
        page = await browse_documents(
            session,
            criteria=DocumentMatchCriteria(
                topics=HierarchyIdMatch(ids=(politics.id, economy.id)),
                geographies=HierarchyIdMatch(ids=(south_korea.id,)),
            ),
        )

    assert page.total == 1
    assert [item.title for item in page.items] == ["Politics in Korea"]


async def test_matching_contract_ignores_inactive_assertions(
    database_session_factory,
):
    async with database_session_factory() as session, session.begin():
        source = Source(
            name="Step 24 Inactive Assertion Source",
            country="Japan",
            primary_language="en",
            source_type="news_organization",
            status="active",
            website_url="https://step24-inactive.example",
            source_metadata={},
        )
        session.add(source)
        await session.flush()
        politics = await session.scalar(select(Topic).where(Topic.slug == "politics"))
        document = _document(
            source_id=source.id,
            title="Historical Politics Assertion",
            token="inactive",
        )
        session.add(document)
        await session.flush()
        session.add(
            DocumentTopic(
                document_id=document.id,
                topic_id=politics.id,
                relationship_role="primary",
                taxonomy_version="1.0",
                confidence=0.99,
                classification_method="deterministic_rule",
                is_active=False,
                superseded_at=datetime.now(UTC),
            )
        )

    async with database_session_factory() as session:
        page = await browse_documents(
            session,
            criteria=DocumentMatchCriteria(topics=HierarchyIdMatch(ids=(politics.id,))),
        )

    assert page.total == 0
    assert page.items == []


async def test_matching_contract_source_predicates_need_no_outer_source_join(
    database_session_factory,
):
    async with database_session_factory() as session, session.begin():
        source = Source(
            name="Step 24 Correlated Source",
            country="Japan",
            primary_language="ja",
            source_type="newspaper",
            status="active",
            website_url="https://step24-correlated.example",
            source_metadata={},
        )
        session.add(source)
        await session.flush()
        document = _document(
            source_id=source.id,
            title="Correlated Source Match",
            token="correlated",
        )
        document.language = None
        session.add(document)
        await session.flush()
        document_id = document.id

    async with database_session_factory() as session:
        plan = await build_document_match_plan(
            session,
            DocumentMatchCriteria(
                source_types=HierarchySlugMatch(
                    slugs=("news_organization",),
                    include_descendants=True,
                ),
                language_tags=("ja",),
            ),
        )
        matched_ids = list(
            (await session.scalars(select(Document.id).where(*plan.predicates))).all()
        )

    assert matched_ids == [document_id]
