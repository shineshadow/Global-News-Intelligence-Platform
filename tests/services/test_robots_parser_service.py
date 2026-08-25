from decimal import Decimal

import pytest

from app.services.robots_parser_service import (
    PARSER_SOURCE_COMMIT,
    PARSER_VERSION,
    PARSER_WHEEL_SHA256,
    RobotsParserError,
    evaluate_robots,
    parse_robots,
    restore_parsed_robots,
)


def test_pinned_protego_preserves_exact_allow_disallow_and_crawl_delay() -> None:
    parsed = parse_robots(
        b"""User-agent: *
Disallow: /private
Allow: /private/public
Crawl-delay: 2.5
"""
    )

    denied = evaluate_robots(
        parsed,
        canonical_target_url="https://publisher.example/private/report",
    )
    allowed = evaluate_robots(
        parsed,
        canonical_target_url="https://publisher.example/private/public/report",
    )

    assert denied.external_decision == "disallowed"
    assert denied.matched_group == "*"
    assert denied.matched_directive == "disallow"
    assert denied.matched_pattern == "/private"
    assert denied.crawl_delay_seconds == Decimal("2.5")
    assert allowed.external_decision == "allowed"
    assert allowed.matched_directive == "allow"
    assert allowed.matched_pattern == "/private/public"
    assert parsed.provenance["parser_version"] == PARSER_VERSION
    assert parsed.provenance["source_commit"] == PARSER_SOURCE_COMMIT
    assert parsed.provenance["wheel_sha256"] == PARSER_WHEEL_SHA256


def test_parser_rejects_empty_and_non_directive_bodies() -> None:
    with pytest.raises(RobotsParserError, match="robots_body_empty"):
        parse_robots(b"  \n")
    with pytest.raises(RobotsParserError, match="robots_body_malformed"):
        parse_robots(b"this is not robots evidence")


def test_persisted_normalized_evidence_restores_deterministically() -> None:
    parsed = parse_robots(
        b"User-agent: Global-News-Intelligence-Platform\nDisallow: /draft\n"
    )
    restored = restore_parsed_robots(dict(parsed.provenance))

    assert restored.directives_digest == parsed.directives_digest
    assert evaluate_robots(
        restored,
        canonical_target_url="https://publisher.example/draft/one",
    ).external_decision == "disallowed"


def test_tampered_normalized_evidence_is_rejected() -> None:
    parsed = parse_robots(b"User-agent: *\nAllow: /\n")
    provenance = dict(parsed.provenance)
    provenance["normalized_directives"] = "user-agent:*\ndisallow:/"

    with pytest.raises(RobotsParserError, match="evidence_untrusted"):
        restore_parsed_robots(provenance)
