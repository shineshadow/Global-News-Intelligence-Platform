from datetime import UTC, datetime

from app.models import Document, Source


async def _create_document(
    database_session_factory,
    *,
    title: str,
) -> int:
    async with database_session_factory() as session, session.begin():
        source = Source(
            name=f"API Monitor Source {title}",
            country="Japan",
            primary_language="en",
            source_type="news_organization",
            status="active",
            website_url=f"https://api-monitor-{title.lower()}.example",
            source_metadata={},
        )
        session.add(source)
        await session.flush()
        document = Document(
            source_id=source.id,
            source_endpoint_id=None,
            ingestion_format="rss",
            content_format="plain_text",
            external_id=title,
            canonical_url=None,
            title_original=title,
            summary_original=None,
            content_original=None,
            language="en",
            country=None,
            author=None,
            published_at=datetime.now(UTC),
            source_updated_at=None,
            retrieved_at=datetime.now(UTC),
            content_hash=title.encode().hex().ljust(64, "0")[:64],
            document_metadata={},
        )
        session.add(document)
        await session.flush()
        return document.id


def _payload(
    *,
    slug: str,
    query: str | None,
    match_all_in_profile: bool = False,
) -> dict:
    return {
        "slug": slug,
        "name": slug.replace("_", " ").title(),
        "revision": {
            "criteria": {
                "text_query": query,
            },
            "match_all_in_profile": match_all_in_profile,
        },
    }


async def test_monitor_api_lifecycle_revision_and_idempotent_match(
    client,
    database_session_factory,
) -> None:
    document_id = await _create_document(
        database_session_factory,
        title="Korea API Monitor",
    )
    create_response = await client.post(
        "/api/v1/monitors",
        json=_payload(
            slug="korea_api_monitor",
            query="Korea",
        ),
    )
    assert create_response.status_code == 201
    monitor_id = create_response.json()["id"]
    assert create_response.json()["status"] == "draft"
    assert create_response.json()["criteria"]["coverage_profile_id"] is not None

    activate_response = await client.post(f"/api/v1/monitors/{monitor_id}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["status"] == "active"

    first_evaluation = await client.post(
        f"/api/v1/monitors/{monitor_id}/evaluate",
        params={"document_id": document_id},
    )
    second_evaluation = await client.post(
        f"/api/v1/monitors/{monitor_id}/evaluate",
        params={"document_id": document_id},
    )
    assert first_evaluation.json()["new_match_count"] == 1
    assert second_evaluation.json()["new_match_count"] == 0

    matches_response = await client.get(f"/api/v1/monitors/{monitor_id}/matches")
    assert matches_response.status_code == 200
    assert len(matches_response.json()) == 1
    assert matches_response.json()[0]["observation_count"] == 2

    assert (await client.post(f"/api/v1/monitors/{monitor_id}/pause")).status_code == 200
    revision_response = await client.post(
        f"/api/v1/monitors/{monitor_id}/revisions",
        json={
            "criteria": {"text_query": "Monitor"},
            "change_reason": "Broaden phrase",
        },
    )
    assert revision_response.status_code == 201
    assert revision_response.json()["current_revision_number"] == 2
    assert revision_response.json()["criteria"]["text_query"] == "Monitor"

    archive_response = await client.post(f"/api/v1/monitors/{monitor_id}/archive")
    assert archive_response.json()["status"] == "archived"
    rejected = await client.post(f"/api/v1/monitors/{monitor_id}/activate")
    assert rejected.status_code == 422


async def test_monitor_api_rejects_unacknowledged_profile_wide_activation(
    client,
) -> None:
    response = await client.post(
        "/api/v1/monitors",
        json=_payload(
            slug="profile_wide_api",
            query=None,
        ),
    )
    monitor_id = response.json()["id"]

    rejected = await client.post(f"/api/v1/monitors/{monitor_id}/activate")
    assert rejected.status_code == 422
    assert "match_all_in_profile" in rejected.json()["error"]["message"]
