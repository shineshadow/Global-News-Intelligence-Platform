from types import SimpleNamespace
from uuid import uuid4


async def create_source(
    client,
) -> tuple[int, int]:
    token = uuid4().hex[:10]

    source_response = await client.post(
        "/api/v1/sources",
        json={
            "name": f"Web Test {token}",
            "country": "United States",
            "primary_language": "en",
            "source_type": "news",
            "website_url": (f"https://example.com/{token}"),
        },
    )

    assert source_response.status_code == 201

    source_id = source_response.json()["id"]

    endpoint_response = await client.post(
        f"/api/v1/sources/{source_id}/endpoints",
        json={
            "name": "RSS",
            "endpoint_type": "rss",
            "url": (f"https://example.com/{token}/feed.xml"),
            "poll_interval_seconds": 900,
        },
    )

    assert endpoint_response.status_code == 201

    return (
        source_id,
        endpoint_response.json()["id"],
    )


async def test_dashboard_page(
    client,
) -> None:
    response = await client.get("/web/")

    assert response.status_code == 200
    assert "Operations Dashboard" in response.text
    assert "Active Endpoints" in response.text


async def test_sources_page(
    client,
) -> None:
    source_id, _ = await create_source(client)

    response = await client.get("/web/sources")

    assert response.status_code == 200
    assert "Sources" in response.text
    assert f"/web/sources/{source_id}" in (response.text)


async def test_source_detail_page(
    client,
) -> None:
    source_id, _ = await create_source(client)

    response = await client.get(f"/web/sources/{source_id}")

    assert response.status_code == 200
    assert "Endpoint Health" in response.text
    assert "Poll now" in response.text


async def test_runs_page(
    client,
) -> None:
    response = await client.get("/web/runs")

    assert response.status_code == 200
    assert "Ingestion Runs" in response.text


async def test_failures_page(
    client,
) -> None:
    response = await client.get("/web/failures")

    assert response.status_code == 200
    assert "Feed Diagnostics" in response.text


async def test_acquisition_health_page(
    client,
) -> None:
    response = await client.get("/web/acquisition-health")

    assert response.status_code == 200
    assert "Acquisition Health" in response.text
    assert "Path / Configuration" not in response.text
    assert "Feed history" not in response.text
    assert "Cutover Control" not in response.text
    assert "Phase 3 proof" not in response.text
    assert "Runtime storage" not in response.text
    assert (await client.post("/web/acquisition-health/1/activate")).status_code == 404
    assert (await client.post("/web/acquisition-health/1/rollback")).status_code == 404


async def test_web_manual_poll(
    client,
    monkeypatch,
) -> None:
    _, endpoint_id = await create_source(client)

    from app.web import routes

    async def fake_queue(
        _session,
        requested_endpoint_id: int,
    ):
        return SimpleNamespace(
            endpoint_id=requested_endpoint_id,
            task_id=("1234567890abcdef1234567890abcdef"),
        )

    monkeypatch.setattr(
        routes,
        "queue_source_endpoint_poll",
        fake_queue,
    )

    response = await client.post(
        f"/web/source-endpoints/{endpoint_id}/poll",
        headers={
            "HX-Request": "true",
        },
    )

    assert response.status_code == 200
    assert "Queued task" in response.text
    assert response.headers.get("HX-Trigger") == "pollQueued"
