from app.services.source_endpoint_service import (
    _normalize_endpoint_values,
)
from app.services.source_service import (
    _normalize_source_values,
)


def test_legacy_source_type_news_is_normalized():
    values = _normalize_source_values(
        {"source_type": "news"}
    )
    assert values["source_type"] == "news_organization"


def test_legacy_source_type_research_is_normalized():
    values = _normalize_source_values(
        {"source_type": "research"}
    )
    assert values["source_type"] == "research_institute"


def test_legacy_rss_endpoint_is_normalized():
    values = _normalize_endpoint_values(
        {"endpoint_type": "rss"}
    )
    assert values == {
        "endpoint_type": "feed",
        "endpoint_format": "rss",
        "acquisition_method": "feed_parser",
    }


def test_legacy_atom_endpoint_is_normalized():
    values = _normalize_endpoint_values(
        {"endpoint_type": "atom"}
    )
    assert values == {
        "endpoint_type": "feed",
        "endpoint_format": "atom",
        "acquisition_method": "feed_parser",
    }


def test_feed_defaults_preserve_current_rss_behavior():
    values = _normalize_endpoint_values(
        {"endpoint_type": "feed"}
    )
    assert values == {
        "endpoint_type": "feed",
        "endpoint_format": "rss",
        "acquisition_method": "feed_parser",
    }
