from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from importlib.metadata import version
from typing import Any

from protego import Protego
from protego._utils import _quote_path

PARSER_DISTRIBUTION = "protego"
PARSER_NAME = "protego"
PARSER_VERSION = "0.6.2"
PARSER_SOURCE_COMMIT = "efe5039d39ee51f117acd0b01ffd8109ae265c22"
PARSER_WHEEL_SHA256 = "714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff"
ROBOTS_USER_AGENT = "Global-News-Intelligence-Platform"


class RobotsParserError(RuntimeError):
    """The approved parser could not produce trustworthy robots evidence."""


@dataclass(frozen=True)
class RobotsParseResult:
    parser: Protego
    text: str
    parse_state: str
    warnings: tuple[dict[str, Any], ...]
    directives_digest: str
    provenance: dict[str, Any]


@dataclass(frozen=True)
class RobotsRuleMatch:
    external_decision: str
    matched_group: str
    matched_directive: str
    matched_pattern: str
    matched_line_or_location: str | None
    match_specificity: int
    crawl_delay_seconds: Decimal | None


def verify_approved_parser() -> None:
    """Fail closed when the installed distribution differs from Owner approval."""

    installed = version(PARSER_DISTRIBUTION)
    if installed != PARSER_VERSION:
        raise RobotsParserError(
            f"Installed Protego version {installed!r} does not match {PARSER_VERSION!r}."
        )
    required = ("parse", "can_fetch", "crawl_delay")
    if any(not hasattr(Protego, name) for name in required):
        raise RobotsParserError("Installed Protego API does not match the approved adapter.")


def parse_robots(content: bytes) -> RobotsParseResult:
    verify_approved_parser()
    if not content or not content.strip():
        raise RobotsParserError("robots_body_empty")

    warnings: list[dict[str, Any]] = []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")
        warnings.append(
            {
                "code": "invalid_utf8_replaced",
                "summary": "Invalid UTF-8 bytes were replaced before robots parsing.",
            }
        )
    try:
        parser = Protego.parse(text)
    except Exception as exc:  # Protego intentionally exposes one parse entry point.
        raise RobotsParserError("parser_failure") from exc

    valid_count = getattr(parser, "_valid_directive_seen", None)
    total_count = getattr(parser, "_total_directive_seen", None)
    invalid_count = getattr(parser, "_invalid_directive_seen", None)
    if not isinstance(valid_count, int) or not isinstance(total_count, int):
        raise RobotsParserError("parser_failure")
    if valid_count == 0:
        raise RobotsParserError("robots_body_malformed")
    if isinstance(invalid_count, int) and invalid_count:
        warnings.append(
            {
                "code": "invalid_directives_ignored",
                "count": invalid_count,
                "summary": "Protego ignored unrecognized robots directives.",
            }
        )

    normalized = _normalized_directives(parser)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return RobotsParseResult(
        parser=parser,
        text=text,
        parse_state="parsed",
        warnings=tuple(warnings),
        directives_digest=digest,
        provenance={
            "schema_version": "acquisition.robots.parser-provenance.v1",
            "distribution": f"{PARSER_DISTRIBUTION}=={PARSER_VERSION}",
            "parser_name": PARSER_NAME,
            "parser_version": PARSER_VERSION,
            "source_commit": PARSER_SOURCE_COMMIT,
            "wheel_sha256": PARSER_WHEEL_SHA256,
            "valid_directive_count": valid_count,
            "total_directive_count": total_count,
            "normalized_directives": normalized,
            "robots_text": text,
        },
    )


def evaluate_robots(
    parsed: RobotsParseResult,
    *,
    canonical_target_url: str,
    selected_user_agent: str = ROBOTS_USER_AGENT,
) -> RobotsRuleMatch:
    try:
        allowed = parsed.parser.can_fetch(canonical_target_url, selected_user_agent)
        delay = parsed.parser.crawl_delay(selected_user_agent)
        rule_set = parsed.parser._get_matching_rule_set(selected_user_agent)  # type: ignore[attr-defined]
    except Exception as exc:
        raise RobotsParserError("evaluation_failure") from exc

    matched_group = "none"
    matched_directive = "none"
    matched_pattern = ""
    specificity = 0
    if rule_set is not None:
        matched_group = str(rule_set.user_agent or "none")
        quoted_target = _quote_path(canonical_target_url)
        for rule in rule_set._rules:  # type: ignore[attr-defined]
            if rule.value.match(quoted_target):
                matched_directive = str(rule.field)
                matched_pattern = str(rule.value._pattern)  # type: ignore[attr-defined]
                specificity = int(rule.value.priority)
                break

    decision = "allowed" if allowed else "disallowed"
    if decision == "disallowed" and matched_directive != "disallow":
        raise RobotsParserError("evaluation_failure")
    if decision == "allowed" and matched_directive not in {"allow", "none"}:
        raise RobotsParserError("evaluation_failure")
    return RobotsRuleMatch(
        external_decision=decision,
        matched_group=matched_group,
        matched_directive=matched_directive,
        matched_pattern=matched_pattern,
        matched_line_or_location=None,
        match_specificity=specificity,
        crawl_delay_seconds=(Decimal(str(delay)) if delay is not None else None),
    )


def restore_parsed_robots(provenance: dict[str, Any]) -> RobotsParseResult:
    expected_provenance = {
        "distribution": f"{PARSER_DISTRIBUTION}=={PARSER_VERSION}",
        "parser_name": PARSER_NAME,
        "parser_version": PARSER_VERSION,
        "source_commit": PARSER_SOURCE_COMMIT,
        "wheel_sha256": PARSER_WHEEL_SHA256,
    }
    if any(provenance.get(key) != value for key, value in expected_provenance.items()):
        raise RobotsParserError("evidence_untrusted")
    text = provenance.get("robots_text")
    if not isinstance(text, str):
        raise RobotsParserError("evidence_untrusted")
    parsed = parse_robots(text.encode("utf-8"))
    expected = provenance.get("normalized_directives")
    if expected != parsed.provenance["normalized_directives"]:
        raise RobotsParserError("evidence_untrusted")
    return parsed


def _normalized_directives(parser: Protego) -> str:
    rows: list[str] = []
    user_agents = getattr(parser, "_user_agents", None)
    if not isinstance(user_agents, dict):
        raise RobotsParserError("parser_failure")
    for user_agent in sorted(user_agents):
        rule_set = user_agents[user_agent]
        rows.append(f"user-agent:{user_agent}")
        for rule in rule_set._rules:  # type: ignore[attr-defined]
            rows.append(f"{rule.field}:{rule.value._pattern}")  # type: ignore[attr-defined]
        if rule_set.crawl_delay is not None:
            rows.append(f"crawl-delay:{rule_set.crawl_delay}")
    return "\n".join(rows)
