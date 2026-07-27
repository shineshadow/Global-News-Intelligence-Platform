from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import uuid4

from sqlalchemy import select

from app.models import (
    Document,
    DocumentVersion,
    IngestionRun,
)


def token() -> str:
    return uuid4().hex[:10]


async def create_source_endpoint(
    client,
    *,
    country: str = "United States",
    language: str = "en",
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

            "source_type": "news",

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

    async with (
        database_session_factory()
        as session
    ):
        async with session.begin():

            document = Document(
                source_id=source_id,

                source_endpoint_id=
                    endpoint_id,

                ingestion_format="rss",

                content_format="plain_text",

                external_id=
                    f"external-{value}",

                canonical_url=
                    f"https://example.com/"
                    f"articles/{value}",

                title_original=title,

                summary_original=
                    f"Summary for {title}",

                content_original=
                    f"Content for {title}",

                language=language,

                country=country,

                author="Test Author",

                published_at=
                    published_at,

                source_updated_at=None,

                retrieved_at=
                    datetime.now(UTC),

                content_hash=
                    value.ljust(
                        64,
                        "a",
                    )[:64],

                document_metadata={
                    "test": True,
                },
            )

            session.add(document)

            await session.flush()

            return document.id


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


async def test_document_browser_filters_country(
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

    await create_document(
        database_session_factory,
        source_id=us_source,
        endpoint_id=us_endpoint,
        title="US Article",
        country="United States",
        language="en",
        published_at=now,
    )

    await create_document(
        database_session_factory,
        source_id=jp_source,
        endpoint_id=jp_endpoint,
        title="Japan Article",
        country="Japan",
        language="ja",
        published_at=now,
    )

    response = await client.get(
        "/web/documents",
        params={
            "country": "Japan",
            "time": "all",
        },
    )

    assert response.status_code == 200

    assert "Japan Article" in response.text
    assert "US Article" not in response.text


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
            "country": "Japan",
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
