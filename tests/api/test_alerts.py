async def test_alert_destination_api_and_web_pages(client) -> None:
    response = await client.post(
        "/api/v1/alert-destinations",
        json={
            "slug": "breaking_ntfy",
            "name": "Breaking ntfy",
            "base_url": "https://ntfy.example/",
            "topic": "breaking_news",
            "auth_token_env_var": "NTFY_BREAKING_TOKEN",
            "max_attempts": 4,
            "retry_base_seconds": 10,
            "retry_max_seconds": 60,
        },
    )
    assert response.status_code == 201
    destination = response.json()
    assert destination["base_url"] == "https://ntfy.example"
    assert destination["topic"] == "breaking_news"
    assert destination["auth_token_env_var"] == "NTFY_BREAKING_TOKEN"
    assert "token" not in destination

    response = await client.post(
        "/api/v1/monitors",
        json={
            "slug": "breaking_monitor",
            "name": "Breaking Monitor",
            "revision": {
                "criteria": {"text_query": "breaking"},
            },
        },
    )
    assert response.status_code == 201
    monitor_id = response.json()["id"]
    response = await client.put(
        (
            f"/api/v1/monitors/{monitor_id}/alert-destinations/"
            f"{destination['id']}"
        ),
        json={"is_enabled": True, "priority": "critical"},
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "critical"
    response = await client.get(
        f"/api/v1/monitors/{monitor_id}/alert-destinations"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get(f"/web/monitors/{monitor_id}")
    assert response.status_code == 200
    assert "Breaking ntfy" in response.text

    response = await client.get(
        f"/web/alert-destinations/{destination['id']}/edit"
    )
    assert response.status_code == 200
    assert "Save destination" in response.text
    response = await client.post(
        f"/web/alert-destinations/{destination['id']}/edit",
        data={
            "name": "Breaking ntfy updated",
            "base_url": "https://ntfy.example",
            "topic": "breaking_news",
            "auth_token_env_var": "NTFY_BREAKING_TOKEN",
            "is_active": "on",
            "request_timeout_seconds": "10",
            "max_attempts": "4",
            "retry_base_seconds": "10",
            "retry_max_seconds": "60",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = await client.patch(
        f"/api/v1/alert-destinations/{destination['id']}",
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = await client.get("/api/v1/alert-destinations")
    assert response.status_code == 200
    assert len(response.json()) == 1

    for path, marker in (
        ("/web/alerts", "No alerts have been created"),
        ("/web/alert-destinations", "Breaking ntfy updated"),
        ("/web/alert-destinations/new", "New ntfy Destination"),
    ):
        response = await client.get(path)
        assert response.status_code == 200
        assert marker in response.text


async def test_destination_validation_rejects_unsafe_or_invalid_config(
    client,
) -> None:
    response = await client.post(
        "/api/v1/alert-destinations",
        json={
            "slug": "unsafe",
            "name": "Unsafe",
            "base_url": "https://user:secret@ntfy.example/path?token=secret",
            "topic": "unsafe",
        },
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/v1/alert-destinations",
        json={
            "slug": "bad_retry",
            "name": "Bad retry",
            "base_url": "https://ntfy.example",
            "topic": "bad_retry",
            "retry_base_seconds": 100,
            "retry_max_seconds": 10,
        },
    )
    assert response.status_code == 422
