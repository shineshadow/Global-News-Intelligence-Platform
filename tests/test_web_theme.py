async def test_dark_theme_banner_and_assets_are_available(client) -> None:
    response = await client.get("/web/")

    assert response.status_code == 200
    assert '<html lang="en" data-bs-theme="dark">' in response.text
    assert 'class="gni-theme-dark-operations"' in response.text
    assert "/themes/dark_operations/theme.css" in response.text
    assert "/static/img/GNI-1288.png" in response.text
    assert "/static/img/GNI.png" in response.text

    theme = await client.get("/themes/dark_operations/theme.css")
    assert theme.status_code == 200
    assert "width: 80.5rem;" in theme.text
    assert "height: 26.8125rem;" in theme.text

    banner = await client.get("/static/img/GNI-1288.png")
    assert banner.status_code == 200
    assert banner.headers["content-type"] == "image/png"
