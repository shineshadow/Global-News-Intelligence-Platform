import pytest

from app.content_formats import normalize_content_format


@pytest.mark.parametrize(
    ("media_type", "expected"),
    [
        (None, "unknown"),
        ("", "unknown"),
        ("text/html; charset=UTF-8", "html"),
        ("application/xhtml+xml", "html"),
        ("text/plain", "plain_text"),
        ("application/pdf", "pdf"),
        ("application/activity+json", "json"),
        ("application/atom+xml", "xml"),
        ("image/webp", "image"),
        ("audio/ogg", "audio"),
        ("video/mp4", "video"),
        ("application/x-unregistered", "other"),
    ],
)
def test_media_type_normalizes_to_content_format(
    media_type,
    expected,
):
    assert normalize_content_format(media_type) == expected
