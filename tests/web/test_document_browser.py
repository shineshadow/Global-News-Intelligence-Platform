from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import uuid4

from sqlalchemy import select

from app.models import (
    CoverageProfile,
    CoverageProfileGeography,
    Document,
    DocumentEntity,
    DocumentGeography,
    DocumentTopic,
    DocumentType,
    DocumentTypeAssignment,
    DocumentVersion,
    Entity,
    Geography,
    IngestionRun,
    Topic,
)


def token() -> str:
    return uuid4().hex[:10]


async def create_source_endpoint(
    client,
    *,
    country: str = "United States",
    language: str = "en",
    source_type: str = "news",
) -> tuple[int, int]:
    value = token()

    source_response = await client.post(
        "/api/v1/sources",
        json={
            "name":
                f"Document Test {value}",

            "country": country,

            "primary_language":
                language,

            "source_type": source_type,

            "website_url":
                f"https://example.com/{value}",
        },
    )

    assert (
        source_response.status_code
        == 201
    )

    source_id = (
        source_response.json()["id"]
    )

    endpoint_response = await client.post(
        f"/api/v1/sources/"
        f"{source_id}/endpoints",
        json={
            "name": "RSS",

            "endpoint_type":
                "rss",

            "url":
                f"https://example.com/"
                f"{value}/feed.xml",

            "poll_interval_seconds":
                900,
        },
    )

    assert (
        endpoint_response.status_code
        == 201
    )

    return (
        source_id,
        endpoint_response.json()["id"],
    )


async def create_document(
    database_session_factory,
    *,
    source_id: int,
    endpoint_id: int,
    title: str,
    country: str,
    language: str,
    published_at: datetime,
) -> int:
    value = token()

    async with database_session_factory() as session, session.begin():
        document = Document(
            source_id=source_id,
            source_endpoint_id=endpoint_id,
            ingestion_format="rss",
            content_format="plain_text",
            external_id=f"external-{value}",
            canonical_url=f"https://example.com/articles/{value}",
            title_original=title,
            summary_original=f"Summary for {title}",
            content_original=f"Content for {title}",
            language=language,
            country=country,
            author="Test Author",
            published_at=published_at,
            source_updated_at=None,
            retrieved_at=datetime.now(UTC),
            content_hash=value.ljust(64, "a")[:64],
            document_metadata={"test": True},
        )
        session.add(document)
        await session.flush()
        return document.id


async def add_document_classifications(
    database_session_factory,
    *,
    document_id: int,
    geography_slugs: tuple[str, ...] = (),
    topic_slug: str | None = None,
    document_type_slug: str | None = None,
    entity_name: str | None = None,
    entity_role: str = "mentioned",
    confidence: float = 0.9,
) -> dict[str, int]:
    result: dict[str, int] = {}
    async with database_session_factory() as session, session.begin():
        for geography_slug in geography_slugs:
            geography_id = await session.scalar(
                select(Geography.id).where(
                    Geography.slug == geography_slug
                )
            )
            result[geography_slug] = geography_id
            session.add(
                DocumentGeography(
                    document_id=document_id,
                    geography_id=geography_id,
                    relationship_role="primary_subject",
                    taxonomy_version="1.0",
                    confidence=confidence,
                    classification_method="deterministic_rule",
                    classifier_version="test",
                )
            )
        if topic_slug is not None:
            topic_id = await session.scalar(
                select(Topic.id).where(Topic.slug == topic_slug)
            )
            result[topic_slug] = topic_id
            session.add(
                DocumentTopic(
                    document_id=document_id,
                    topic_id=topic_id,
                    relationship_role="primary",
                    taxonomy_version="1.0",
                    confidence=confidence,
                    classification_method="deterministic_rule",
                    classifier_version="test",
                )
            )
        if document_type_slug is not None:
            document_type_id = await session.scalar(
                select(DocumentType.id).where(
                    DocumentType.slug == document_type_slug
                )
            )
            result[document_type_slug] = document_type_id
            session.add(
                DocumentTypeAssignment(
                    document_id=document_id,
                    document_type_id=document_type_id,
                    is_primary=True,
                    confidence=confidence,
                    classification_method="deterministic_rule",
                    classifier_version="test",
                )
            )
        if entity_name is not None:
            entity = Entity(
                canonical_name=entity_name,
                entity_metadata={},
            )
            session.add(entity)
            await session.flush()
            result["entity"] = entity.id
            session.add(
                DocumentEntity(
                    document_id=document_id,
                    entity_id=entity.id,
                    entity_role=entity_role,
                    mention_text=entity_name,
                    confidence=confidence,
                    classification_method="deterministic_rule",
                    classifier_version="test",
                )
            )
    return result


async def test_document_browser_page(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client
        )
    )

    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Browser Test Article",
        country="United States",
        language="en",
        published_at=
            datetime.now(UTC),
    )

    response = await client.get(
        "/web/documents"
    )

    assert response.status_code == 200

    assert (
        "Browser Test Article"
        in response.text
    )

    assert "News Feed" in response.text


async def test_document_browser_filters_canonical_geography(
    client,
    database_session_factory,
) -> None:
    us_source, us_endpoint = (
        await create_source_endpoint(
            client,
            country="United States",
            language="en",
        )
    )

    jp_source, jp_endpoint = (
        await create_source_endpoint(
            client,
            country="Japan",
            language="ja",
        )
    )

    now = datetime.now(UTC)

    us_document_id = await create_document(
        database_session_factory,
        source_id=us_source,
        endpoint_id=us_endpoint,
        title="US Article",
        country="United States",
        language="en",
        published_at=now,
    )

    japan_document_id = await create_document(
        database_session_factory,
        source_id=jp_source,
        endpoint_id=jp_endpoint,
        title="Japan Article",
        country="Japan",
        language="ja",
        published_at=now,
    )

    async with database_session_factory() as session, session.begin():
        united_states_id = await session.scalar(
            select(Geography.id).where(
                Geography.slug == "united-states"
            )
        )
        south_korea_id = await session.scalar(
            select(Geography.id).where(
                Geography.slug == "south-korea"
            )
        )
        session.add_all(
            [
                DocumentGeography(
                    document_id=us_document_id,
                    geography_id=united_states_id,
                    relationship_role="primary_subject",
                    taxonomy_version="1.0",
                    confidence=0.9,
                    classification_method="deterministic_rule",
                    classifier_version="test",
                ),
                DocumentGeography(
                    document_id=japan_document_id,
                    geography_id=south_korea_id,
                    relationship_role="primary_subject",
                    taxonomy_version="1.0",
                    confidence=0.9,
                    classification_method="deterministic_rule",
                    classifier_version="test",
                ),
            ]
        )

    response = await client.get(
        "/web/documents",
        params={
            "geography_id": south_korea_id,
            "time": "all",
        },
    )

    assert response.status_code == 200

    # The publisher is Japanese, but the canonical document subject is
    # South Korea. Source.country must not drive this filter.
    assert "Japan Article" in response.text
    assert "US Article" not in response.text


async def test_document_browser_geography_descendants_and_confidence(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = await create_source_endpoint(
        client,
        country="Japan",
        language="ja",
    )
    document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Japan Confidence Article",
        country="Japan",
        language="ja",
        published_at=datetime.now(UTC),
    )
    await add_document_classifications(
        database_session_factory,
        document_id=document_id,
        geography_slugs=("japan",),
        confidence=0.65,
    )
    async with database_session_factory() as session:
        eastern_asia_id = await session.scalar(
            select(Geography.id).where(
                Geography.slug == "eastern-asia"
            )
        )

    exact_response = await client.get(
        "/web/documents",
        params={
            "geography_id": eastern_asia_id,
            "time": "all",
        },
    )
    high_confidence_response = await client.get(
        "/web/documents",
        params={
            "geography_id": eastern_asia_id,
            "geography_descendants": "true",
            "minimum_confidence": "0.70",
            "time": "all",
        },
    )
    matching_response = await client.get(
        "/web/documents",
        params={
            "geography_id": eastern_asia_id,
            "geography_descendants": "true",
            "minimum_confidence": "0.60",
            "time": "all",
        },
    )

    assert "Japan Confidence Article" not in exact_response.text
    assert "Japan Confidence Article" not in high_confidence_response.text
    assert "Japan Confidence Article" in matching_response.text


async def test_document_browser_combines_canonical_dimensions(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = await create_source_endpoint(client)
    document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Combined Classification Article",
        country="United States",
        language="en",
        published_at=datetime.now(UTC),
    )
    identifiers = await add_document_classifications(
        database_session_factory,
        document_id=document_id,
        geography_slugs=("south-korea",),
        topic_slug="politics",
        document_type_slug="news_report",
        entity_name="Combined Test Entity",
        entity_role="subject",
        confidence=0.91,
    )

    response = await client.get(
        "/web/documents",
        params={
            "geography_id": identifiers["south-korea"],
            "topic_id": identifiers["politics"],
            "entity_id": identifiers["entity"],
            "entity_role": "subject",
            "document_type_id": identifiers["news_report"],
            "content_format": "plain_text",
            "source_type": "news_organization",
            "language": "en",
            "minimum_confidence": "0.90",
            "q": "Classification Article",
            "time": "all",
        },
    )
    wrong_role_response = await client.get(
        "/web/documents",
        params={
            "entity_id": identifiers["entity"],
            "entity_role": "location",
            "time": "all",
        },
    )

    assert response.status_code == 200
    assert "Combined Classification Article" in response.text
    assert "Combined Classification Article" not in wrong_role_response.text


async def test_document_browser_source_type_descendants_are_explicit(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = await create_source_endpoint(
        client,
        source_type="newspaper",
    )
    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Newspaper Descendant Article",
        country="United States",
        language="en",
        published_at=datetime.now(UTC),
    )

    exact_response = await client.get(
        "/web/documents",
        params={
            "source_type": "news_organization",
            "time": "all",
        },
    )
    descendant_response = await client.get(
        "/web/documents",
        params={
            "source_type": "news_organization",
            "source_type_descendants": "true",
            "time": "all",
        },
    )

    assert "Newspaper Descendant Article" not in exact_response.text
    assert "Newspaper Descendant Article" in descendant_response.text


async def test_document_browser_applies_coverage_profile_scope(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = await create_source_endpoint(client)
    korea_document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Profile Korea Article",
        country="Japan",
        language="en",
        published_at=datetime.now(UTC),
    )
    japan_document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Profile Japan Article",
        country="Japan",
        language="en",
        published_at=datetime.now(UTC),
    )
    korea_ids = await add_document_classifications(
        database_session_factory,
        document_id=korea_document_id,
        geography_slugs=("south-korea",),
    )
    await add_document_classifications(
        database_session_factory,
        document_id=japan_document_id,
        geography_slugs=("japan",),
    )
    async with database_session_factory() as session, session.begin():
        profile = CoverageProfile(
            slug="korea_feed_test",
            name="Korea Feed Test",
        )
        session.add(profile)
        await session.flush()
        session.add(
            CoverageProfileGeography(
                profile_id=profile.id,
                geography_id=korea_ids["south-korea"],
            )
        )
        profile_id = profile.id

    response = await client.get(
        "/web/documents",
        params={
            "profile_id": profile_id,
            "time": "all",
        },
    )

    assert "Profile Korea Article" in response.text
    assert "Profile Japan Article" not in response.text


async def test_document_browser_descendant_matches_do_not_duplicate_rows(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = await create_source_endpoint(client)
    document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Multi Geography Article",
        country="Japan",
        language="en",
        published_at=datetime.now(UTC),
    )
    await add_document_classifications(
        database_session_factory,
        document_id=document_id,
        geography_slugs=("japan", "south-korea"),
    )
    async with database_session_factory() as session:
        eastern_asia_id = await session.scalar(
            select(Geography.id).where(
                Geography.slug == "eastern-asia"
            )
        )

    response = await client.get(
        "/web/documents",
        params={
            "geography_id": eastern_asia_id,
            "geography_descendants": "true",
            "time": "all",
        },
    )

    assert response.text.count('class="fw-bold document-title"') == 1
    assert "1\n            Documents" in response.text


async def test_document_browser_pagination_preserves_active_criteria(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = await create_source_endpoint(client)
    geography_id = None
    for index in range(11):
        document_id = await create_document(
            database_session_factory,
            source_id=source_id,
            endpoint_id=endpoint_id,
            title=f"Paged Korea Article {index}",
            country="Japan",
            language="en",
            published_at=datetime.now(UTC),
        )
        identifiers = await add_document_classifications(
            database_session_factory,
            document_id=document_id,
            geography_slugs=("south-korea",),
            confidence=0.91,
        )
        geography_id = identifiers["south-korea"]

    response = await client.get(
        "/web/documents",
        params={
            "geography_id": geography_id,
            "geography_descendants": "true",
            "minimum_confidence": "0.90",
            "q": "Paged Korea",
            "time": "all",
            "page_size": 10,
        },
    )

    assert response.status_code == 200
    assert "Next →" in response.text
    assert f"geography_id={geography_id}" in response.text
    assert "geography_descendants=true" in response.text
    assert "minimum_confidence=0.90" in response.text
    assert "q=Paged+Korea" in response.text
    assert "page=2" in response.text


async def test_document_browser_treats_search_wildcards_literally(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = await create_source_endpoint(client)
    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Growth reached 10% today",
        country="United States",
        language="en",
        published_at=datetime.now(UTC),
    )
    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Ordinary report",
        country="United States",
        language="en",
        published_at=datetime.now(UTC),
    )
    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Identifier A_B",
        country="United States",
        language="en",
        published_at=datetime.now(UTC),
    )
    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Identifier AXB",
        country="United States",
        language="en",
        published_at=datetime.now(UTC),
    )

    percent_response = await client.get(
        "/web/documents",
        params={"q": "%", "time": "all"},
    )
    underscore_response = await client.get(
        "/web/documents",
        params={"q": "_", "time": "all"},
    )

    assert "Growth reached 10% today" in percent_response.text
    assert "Ordinary report" not in percent_response.text
    assert "Identifier A_B" in underscore_response.text
    assert "Identifier AXB" not in underscore_response.text


async def test_document_browser_time_filter(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client
        )
    )

    now = datetime.now(UTC)

    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Recent Article",
        country="United States",
        language="en",
        published_at=
            now - timedelta(hours=1),
    )

    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Old Article",
        country="United States",
        language="en",
        published_at=
            now - timedelta(days=10),
    )

    response = await client.get(
        "/web/documents",
        params={
            "time": "24h",
        },
    )

    assert response.status_code == 200

    assert "Recent Article" in response.text

    assert "Old Article" not in response.text


async def test_document_browser_search(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client
        )
    )

    now = datetime.now(UTC)

    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="China Trade Negotiations",
        country="United States",
        language="en",
        published_at=now,
    )

    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Local Weather Report",
        country="United States",
        language="en",
        published_at=now,
    )

    response = await client.get(
        "/web/documents",
        params={
            "q": "China",
            "time": "all",
        },
    )

    assert response.status_code == 200

    assert (
        "China Trade Negotiations"
        in response.text
    )

    assert (
        "Local Weather Report"
        not in response.text
    )    


async def test_document_browser_accepts_blank_source_filter(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client,
            country="Japan",
            language="ja",
        )
    )

    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Blank Source Filter Test",
        country="Japan",
        language="ja",
        published_at=datetime.now(UTC),
    )

    response = await client.get(
        "/web/documents",
        params={
            "source_id": "",
            "geography_id": "",
            "language": "",
            "time": "all",
            "q": "",
        },
    )

    assert response.status_code == 200

    assert (
        "Blank Source Filter Test"
        in response.text
    )


async def test_document_detail_page(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client
        )
    )

    document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Detailed Article",
        country="United States",
        language="en",
        published_at=
            datetime.now(UTC),
    )

    response = await client.get(
        f"/web/documents/{document_id}"
    )

    assert response.status_code == 200

    assert "Detailed Article" in response.text
    assert "Original Content" in response.text
    assert "Test Author" in response.text
    assert "Stored Metadata" in response.text


async def test_document_version_history(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client
        )
    )

    document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Current Headline",
        country="United States",
        language="en",
        published_at=
            datetime.now(UTC),
    )

    async with (
        database_session_factory()
        as session
    ):
        async with session.begin():

            version = DocumentVersion(
                document_id=document_id,

                version_number=1,

                canonical_url=
                    "https://example.com/old",

                title_original=
                    "Old Headline",

                summary_original=
                    "Old summary",

                content_original=
                    "Old content",

                content_format=
                    "plain_text",

                language="en",

                country=
                    "United States",

                author=
                    "Test Author",

                published_at=
                    datetime.now(UTC),

                source_updated_at=None,

                retrieved_at=
                    datetime.now(UTC),

                content_hash=
                    "b" * 64,

                changed_fields=[
                    "title_original",
                    "content_original",
                ],

                version_metadata={
                    "test": True,
                },
            )

            session.add(version)

    response = await client.get(
        f"/web/documents/{document_id}"
    )

    assert response.status_code == 200

    assert "Version History" in response.text
    assert "Version 1" in response.text
    assert "Old Headline" in response.text


async def test_document_detail_latest_endpoint_run(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client
        )
    )

    document_id = await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="Run Metadata Article",
        country="United States",
        language="en",
        published_at=
            datetime.now(UTC),
    )

    now = datetime.now(UTC)

    async with (
        database_session_factory()
        as session
    ):
        async with session.begin():

            session.add(
                IngestionRun(
                    source_id=source_id,

                    source_endpoint_id=
                        endpoint_id,

                    endpoint_url=
                        "https://example.com/feed.xml",

                    trigger_type=
                        "scheduled",

                    status=
                        "succeeded",

                    started_at=now,

                    finished_at=now,

                    duration_ms=125,

                    http_status=200,

                    response_bytes=500,

                    items_seen=10,

                    items_created=2,

                    items_updated=1,

                    items_unchanged=7,

                    items_failed=0,

                    error_details={},

                    run_metadata={},
                )
            )

    response = await client.get(
        f"/web/documents/{document_id}"
    )

    assert response.status_code == 200

    assert "Latest Endpoint Run" in response.text
    assert "Succeeded" in response.text
    assert "Items Seen" in response.text


async def test_htmx_document_filter_returns_partial(
    client,
    database_session_factory,
) -> None:
    source_id, endpoint_id = (
        await create_source_endpoint(
            client
        )
    )

    await create_document(
        database_session_factory,
        source_id=source_id,
        endpoint_id=endpoint_id,
        title="HTMX Article",
        country="United States",
        language="en",
        published_at=
            datetime.now(UTC),
    )

    response = await client.get(
        "/web/documents",
        params={
            "time": "all",
        },
        headers={
            "HX-Request": "true",
        },
    )

    assert response.status_code == 200

    assert "HTMX Article" in response.text

    # Partial response, not the entire layout.
    assert "<!doctype html>" not in (
        response.text.lower()
    )
