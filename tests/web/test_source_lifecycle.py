from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from app.models import (
    Source,
    SourceEndpoint,
)


def value() -> str:
    return uuid4().hex[:10]


async def create_test_source(
    client,
) -> int:
    token = value()

    response = await client.post(
        "/api/v1/sources",
        json={
            "name": f"Lifecycle {token}",
            "country": "United States",
            "primary_language": "en",
            "source_type": "news",
            "website_url":
                f"https://example.com/{token}",
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


async def test_new_source_form(
    client,
) -> None:
    response = await client.get(
        "/web/sources/new"
    )

    assert response.status_code == 200
    assert "New Source" in response.text
    assert "Save Source" in response.text


async def test_create_source_from_web(
    client,
    database_session_factory,
) -> None:
    token = value()

    response = await client.post(
        "/web/sources",
        data={
            "name": f"Web Source {token}",
            "native_name": "",
            "country": "Japan",
            "primary_language": "ja",
            "source_type": "news",
            "priority": "high",
            "website_url":
                f"https://example.com/{token}",
        },
    )

    assert response.status_code == 303

    async with database_session_factory() as session:
        source = await session.scalar(
            select(Source).where(
                Source.name
                == f"Web Source {token}"
            )
        )

        assert source is not None
        assert source.country == "Japan"
        assert source.priority == "high"
        assert source.status == "active"


async def test_disable_and_enable_source(
    client,
    database_session_factory,
) -> None:
    source_id = await create_test_source(
        client
    )

    response = await client.post(
        f"/web/sources/{source_id}/disable"
    )

    assert response.status_code == 303

    async with database_session_factory() as session:
        source = await session.get(
            Source,
            source_id,
        )

        assert source.status == "disabled"

    response = await client.post(
        f"/web/sources/{source_id}/enable"
    )

    assert response.status_code == 303

    async with database_session_factory() as session:
        source = await session.get(
            Source,
            source_id,
        )

        assert source.status == "active"


async def test_new_endpoint_starts_disabled(
    client,
    database_session_factory,
) -> None:
    source_id = await create_test_source(
        client
    )

    token = value()

    response = await client.post(
        f"/web/sources/{source_id}/endpoints",
        data={
            "name": "Test RSS",
            "endpoint_type": "rss",
            "url":
                f"https://example.com/{token}/feed.xml",
            "poll_interval_seconds": "900",
            "action": "save",
        },
    )

    assert response.status_code == 303

    async with database_session_factory() as session:
        endpoint = await session.scalar(
            select(SourceEndpoint).where(
                SourceEndpoint.source_id
                == source_id
            )
        )

        assert endpoint is not None
        assert endpoint.status == "disabled"

        assert (
            endpoint.endpoint_metadata[
                "verification_status"
            ]
            == "pending_health_check"
        )


async def test_endpoint_url_change_resets_health(
    client,
    database_session_factory,
) -> None:
    source_id = await create_test_source(
        client
    )

    token = value()

    create_response = await client.post(
        f"/api/v1/sources/{source_id}/endpoints",
        json={
            "name": "RSS",
            "endpoint_type": "rss",
            "url":
                f"https://example.com/{token}/old.xml",
            "poll_interval_seconds": 900,
        },
    )

    assert create_response.status_code == 201

    endpoint_id = create_response.json()["id"]

    async with database_session_factory() as session:
        async with session.begin():
            endpoint = await session.get(
                SourceEndpoint,
                endpoint_id,
            )

            endpoint.etag = '"old-etag"'
            endpoint.last_http_status = 200
            endpoint.consecutive_failures = 3
            endpoint.last_error = "old error"

    response = await client.post(
        f"/web/source-endpoints/{endpoint_id}",
        data={
            "name": "RSS",
            "endpoint_type": "rss",
            "url":
                f"https://example.com/{token}/new.xml",
            "poll_interval_seconds": "900",
            "action": "save",
        },
    )

    assert response.status_code == 303

    async with database_session_factory() as session:
        endpoint = await session.get(
            SourceEndpoint,
            endpoint_id,
        )

        assert endpoint.status == "disabled"
        assert endpoint.etag is None
        assert endpoint.last_http_status is None
        assert endpoint.consecutive_failures == 0
        assert endpoint.last_error is None

        assert (
            endpoint.endpoint_metadata[
                "verification_status"
            ]
            == "pending_health_check"
        )


async def test_unverified_endpoint_cannot_enable(
    client,
    database_session_factory,
) -> None:
    source_id = await create_test_source(
        client
    )

    token = value()

    await client.post(
        f"/web/sources/{source_id}/endpoints",
        data={
            "name": "RSS",
            "endpoint_type": "rss",
            "url":
                f"https://example.com/{token}/feed.xml",
            "poll_interval_seconds": "900",
            "action": "save",
        },
    )

    async with database_session_factory() as session:
        endpoint = await session.scalar(
            select(SourceEndpoint).where(
                SourceEndpoint.source_id
                == source_id
            )
        )

        endpoint_id = endpoint.id

    response = await client.post(
        f"/web/source-endpoints/"
        f"{endpoint_id}/enable"
    )

    assert response.status_code == 303
    assert (
        "endpoint_enable_blocked=1"
        in response.headers["location"]
    )


async def test_verify_route(
    client,
    database_session_factory,
    monkeypatch,
) -> None:
    source_id = await create_test_source(
        client
    )

    token = value()

    await client.post(
        f"/web/sources/{source_id}/endpoints",
        data={
            "name": "RSS",
            "endpoint_type": "rss",
            "url":
                f"https://example.com/{token}/feed.xml",
            "poll_interval_seconds": "900",
            "action": "save",
        },
    )

    async with database_session_factory() as session:
        endpoint = await session.scalar(
            select(SourceEndpoint).where(
                SourceEndpoint.source_id
                == source_id
            )
        )

        endpoint_id = endpoint.id

    from app.web import lifecycle_routes

    async def fake_healthcheck(
        requested_endpoint_id: int,
        *,
        activate_on_success: bool,
    ):
        assert requested_endpoint_id == endpoint_id
        assert activate_on_success is True

        return SimpleNamespace(
            passed=True,
        )

    monkeypatch.setattr(
        lifecycle_routes,
        "healthcheck_rss_endpoint",
        fake_healthcheck,
    )

    response = await client.post(
        f"/web/source-endpoints/"
        f"{endpoint_id}/verify"
    )

    assert response.status_code == 303
    assert (
        "verified=1"
        in response.headers["location"]
    )