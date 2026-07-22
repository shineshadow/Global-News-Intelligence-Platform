from uuid import uuid4

from httpx import AsyncClient


def unique_token() -> str:
    return uuid4().hex[:12]


async def create_test_source(
    client: AsyncClient,
    *,
    token: str | None = None,
) -> dict:
    """Create and return a valid source through the API."""

    token = token or unique_token()

    response = await client.post(
        "/api/v1/sources",
        json={
            "name": f"Test Source {token}",
            "country": "United States",
            "primary_language": "en",
            "source_type": "news",
            "priority": "normal",
            "website_url": (
                f"https://example.com/sources/{token}"
            ),
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


async def create_test_endpoint(
    client: AsyncClient,
    source_id: int,
    *,
    token: str | None = None,
) -> dict:
    """Create and return a valid endpoint through the API."""

    token = token or unique_token()

    response = await client.post(
        f"/api/v1/sources/{source_id}/endpoints",
        json={
            "name": f"Test RSS {token}",
            "endpoint_type": "rss",
            "url": (
                f"https://example.com/feeds/{token}.xml"
            ),
            "poll_interval_seconds": 900,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


async def test_source_crud_and_disable(
    client: AsyncClient,
) -> None:
    source = await create_test_source(client)
    source_id = source["id"]

    assert source["status"] == "active"
    assert source["priority"] == "normal"

    get_response = await client.get(
        f"/api/v1/sources/{source_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == source_id

    list_response = await client.get(
        "/api/v1/sources",
        params={"status": "active"},
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [
        source_id
    ]

    update_response = await client.patch(
        f"/api/v1/sources/{source_id}",
        json={
            "priority": "high",
            "native_name": "Updated Test Source",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["priority"] == "high"
    assert (
        update_response.json()["native_name"]
        == "Updated Test Source"
    )

    disable_response = await client.post(
        f"/api/v1/sources/{source_id}/disable"
    )

    assert disable_response.status_code == 200
    assert disable_response.json()["status"] == "disabled"

    active_response = await client.get(
        "/api/v1/sources",
        params={"status": "active"},
    )

    assert active_response.status_code == 200
    assert active_response.json() == []

    disabled_response = await client.get(
        "/api/v1/sources",
        params={"status": "disabled"},
    )

    assert disabled_response.status_code == 200
    assert disabled_response.json()[0]["id"] == source_id


async def test_duplicate_source_url_returns_409(
    client: AsyncClient,
) -> None:
    token = unique_token()

    first_source = await create_test_source(
        client,
        token=token,
    )

    response = await client.post(
        "/api/v1/sources",
        json={
            "name": "Duplicate URL Source",
            "country": "Canada",
            "primary_language": "en",
            "source_type": "news",
            "website_url": first_source["website_url"],
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "resource_conflict",
            "message": (
                "A source with this website URL already exists."
            ),
            "details": None,
        }
    }


async def test_source_not_found_returns_standard_404(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/sources/999999999"
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "resource_not_found",
            "message": "Source 999999999 was not found.",
            "details": None,
        }
    }


async def test_invalid_source_returns_standard_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/sources",
        json={
            "name": "",
            "country": "United States",
            "primary_language": "en",
            "source_type": "news",
        },
    )

    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == (
        "request_validation_error"
    )
    assert body["error"]["message"] == (
        "The request data failed validation."
    )
    assert body["error"]["details"]


async def test_endpoint_crud_and_disable(
    client: AsyncClient,
) -> None:
    source = await create_test_source(client)
    source_id = source["id"]

    endpoint = await create_test_endpoint(
        client,
        source_id,
    )

    endpoint_id = endpoint["id"]

    assert endpoint["source_id"] == source_id
    assert endpoint["status"] == "active"
    assert endpoint["poll_interval_seconds"] == 900

    get_response = await client.get(
        f"/api/v1/source-endpoints/{endpoint_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == endpoint_id

    list_response = await client.get(
        f"/api/v1/sources/{source_id}/endpoints",
        params={"status": "active"},
    )

    assert list_response.status_code == 200
    assert [
        item["id"]
        for item in list_response.json()
    ] == [endpoint_id]

    update_response = await client.patch(
        f"/api/v1/source-endpoints/{endpoint_id}",
        json={
            "name": "Updated RSS Feed",
            "poll_interval_seconds": 1800,
        },
    )

    assert update_response.status_code == 200

    updated_endpoint = update_response.json()

    assert updated_endpoint["name"] == "Updated RSS Feed"
    assert updated_endpoint["poll_interval_seconds"] == 1800

    disable_response = await client.post(
        f"/api/v1/source-endpoints/{endpoint_id}/disable"
    )

    assert disable_response.status_code == 200
    assert disable_response.json()["status"] == "disabled"

    disabled_list_response = await client.get(
        f"/api/v1/sources/{source_id}/endpoints",
        params={"status": "disabled"},
    )

    assert disabled_list_response.status_code == 200

    disabled_endpoints = disabled_list_response.json()

    assert len(disabled_endpoints) == 1
    assert disabled_endpoints[0]["id"] == endpoint_id
    assert disabled_endpoints[0]["status"] == "disabled"

async def test_duplicate_endpoint_url_returns_409(
    client: AsyncClient,
) -> None:
    source = await create_test_source(client)
    token = unique_token()

    first_endpoint = await create_test_endpoint(
        client,
        source["id"],
        token=token,
    )

    response = await client.post(
        f"/api/v1/sources/{source['id']}/endpoints",
        json={
            "name": "Duplicate RSS Feed",
            "endpoint_type": "rss",
            "url": first_endpoint["url"],
            "poll_interval_seconds": 900,
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "resource_conflict"
    )


async def test_invalid_endpoint_interval_returns_422(
    client: AsyncClient,
) -> None:
    source = await create_test_source(client)

    response = await client.post(
        f"/api/v1/sources/{source['id']}/endpoints",
        json={
            "name": "Invalid Poll Interval",
            "endpoint_type": "rss",
            "url": "https://example.com/invalid.xml",
            "poll_interval_seconds": 10,
        },
    )

    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == (
        "request_validation_error"
    )
    assert body["error"]["details"]


async def test_endpoint_requires_existing_source(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/sources/999999999/endpoints",
        json={
            "name": "Orphan RSS Feed",
            "endpoint_type": "rss",
            "url": "https://example.com/orphan.xml",
            "poll_interval_seconds": 900,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "resource_not_found",
            "message": "Source 999999999 was not found.",
            "details": None,
        }
    }