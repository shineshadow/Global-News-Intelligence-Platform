from app.schemas.document_match import (
    DocumentMatchCriteria,
    HierarchySlugMatch,
)


async def test_news_feed_can_save_frozen_criteria_as_monitor(
    client,
) -> None:
    feed_response = await client.get(
        "/web/documents",
        params={
            "source_type": "news_organization",
            "source_type_descendants": "true",
            "language": "en",
            "q": "Korea",
            "time": "all",
        },
    )
    assert feed_response.status_code == 200
    assert "Save as Monitor" in feed_response.text
    assert 'formaction="http://test/web/monitors/new"' in feed_response.text

    form_response = await client.get(
        "/web/monitors/new",
        params={
            "source_type": "news_organization",
            "source_type_descendants": "true",
            "language": "en",
            "q": "Korea",
            "time": "all",
        },
    )
    assert form_response.status_code == 200
    assert "Save News Feed criteria" in form_response.text
    assert "news_organization" in form_response.text
    assert "Korea" in form_response.text

    criteria = DocumentMatchCriteria(
        source_types=HierarchySlugMatch(
            slugs=("news_organization",),
            include_descendants=True,
        ),
        language_tags=("en",),
        text_query="Korea",
    )
    create_response = await client.post(
        "/web/monitors/new",
        data={
            "name": "Korea Web Monitor",
            "slug": "korea_web_monitor",
            "criteria_payload": criteria.model_dump_json(),
            "match_existing_on_activation": "true",
        },
        follow_redirects=False,
    )
    assert create_response.status_code == 303
    detail_url = create_response.headers["location"]

    detail_response = await client.get(detail_url)
    assert detail_response.status_code == 200
    assert "Korea Web Monitor" in detail_response.text
    assert "draft" in detail_response.text
    assert "news_organization" in detail_response.text

    list_response = await client.get("/web/monitors")
    assert list_response.status_code == 200
    assert "Korea Web Monitor" in list_response.text
