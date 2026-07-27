from app.classification.rules import (
    load_deterministic_ruleset,
)


def test_keyword_rules_are_multilabel():
    ruleset = load_deterministic_ruleset()

    result = ruleset.classify(
        title=(
            "Central bank warns semiconductor investment "
            "could affect interest rates"
        ),
        summary=None,
        content=None,
        canonical_url=None,
        document_metadata={},
    )

    topic_slugs = {
        candidate.slug
        for candidate in result.topics
    }

    assert "economy" in topic_slugs
    assert "technology" in topic_slugs


def test_rss_tag_metadata_maps_to_canonical_topic():
    ruleset = load_deterministic_ruleset()

    result = ruleset.classify(
        title="Ordinary item",
        summary=None,
        content=None,
        canonical_url=None,
        document_metadata={
            "tags": [
                {
                    "term": "정치",
                    "scheme": None,
                    "label": None,
                }
            ]
        },
    )

    assert any(
        candidate.slug == "politics"
        and candidate.classification_method
        == "metadata_mapping"
        for candidate in result.topics
    )


def test_breaking_news_document_type_rule():
    ruleset = load_deterministic_ruleset()

    result = ruleset.classify(
        title="속보: Major announcement expected today",
        summary=None,
        content=None,
        canonical_url=None,
        document_metadata={},
    )

    assert any(
        candidate.slug == "breaking_news"
        for candidate in result.document_types
    )
