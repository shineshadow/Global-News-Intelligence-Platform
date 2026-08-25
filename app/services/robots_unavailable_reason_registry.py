from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

RobotsFailurePhase = Literal[
    "retrieval",
    "validation",
    "parsing",
    "evaluation",
    "evidence_binding",
]
RobotsRetryable = Literal["true", "false", "unknown"]

ROBOTS_FAILURE_PHASES = frozenset(
    {"retrieval", "validation", "parsing", "evaluation", "evidence_binding"}
)
ROBOTS_RETRYABLE_VALUES = frozenset({"true", "false", "unknown"})
ROBOTS_UNAVAILABLE_INFORMATION_SCHEMA_VERSION = "acquisition.robots.unavailable-information.v1"


class RobotsUnavailableReasonError(ValueError):
    """Unavailable-evidence information failed its registered contract."""


@dataclass(frozen=True)
class RobotsUnavailableReasonDefinition:
    code: str
    display_label: str
    description: str
    failure_phase: RobotsFailurePhase
    default_retryable: RobotsRetryable
    schema_version: str = ROBOTS_UNAVAILABLE_INFORMATION_SCHEMA_VERSION
    internal_information: bool = True
    owner_information: bool = True
    future_ui_surface: str = "admin"


def _reason(
    code: str,
    display_label: str,
    description: str,
    failure_phase: RobotsFailurePhase,
    default_retryable: RobotsRetryable,
) -> RobotsUnavailableReasonDefinition:
    return RobotsUnavailableReasonDefinition(
        code=code,
        display_label=display_label,
        description=description,
        failure_phase=failure_phase,
        default_retryable=default_retryable,
    )


_DEFINITIONS = {
    definition.code: definition
    for definition in (
        _reason(
            "http_not_found",
            "HTTP not found",
            "The publisher returned HTTP 404 or 410 for /robots.txt.",
            "retrieval",
            "unknown",
        ),
        _reason(
            "http_client_error",
            "HTTP client error",
            "The publisher returned another HTTP 4xx response for /robots.txt.",
            "retrieval",
            "unknown",
        ),
        _reason(
            "http_server_error",
            "HTTP server error",
            "The publisher returned an HTTP 5xx response for /robots.txt.",
            "retrieval",
            "true",
        ),
        _reason(
            "dns_failure",
            "DNS failure",
            "The publisher hostname could not be resolved.",
            "retrieval",
            "true",
        ),
        _reason(
            "connection_failure",
            "Connection failure",
            "A network connection to the publisher could not be established.",
            "retrieval",
            "true",
        ),
        _reason(
            "connection_timeout",
            "Connection timeout",
            "The publisher connection was not established within the configured limit.",
            "retrieval",
            "true",
        ),
        _reason(
            "read_timeout",
            "Read timeout",
            "The publisher did not provide the robots response within the configured limit.",
            "retrieval",
            "true",
        ),
        _reason(
            "tls_failure",
            "TLS failure",
            "The publisher TLS connection could not be validated or completed.",
            "retrieval",
            "unknown",
        ),
        _reason(
            "redirect_limit_reached",
            "Redirect limit reached",
            "The robots request exceeded the effective Owner-selected redirect limit.",
            "retrieval",
            "unknown",
        ),
        _reason(
            "redirect_destination_rejected",
            "Redirect destination rejected",
            "A robots redirect resolved to a destination rejected by the egress guard.",
            "validation",
            "false",
        ),
        _reason(
            "egress_guard_rejected",
            "Destination rejected",
            "The robots destination was rejected by the effective egress policy.",
            "validation",
            "false",
        ),
        _reason(
            "response_too_large",
            "Response too large",
            "The robots response exceeded the effective Owner-selected byte limit.",
            "retrieval",
            "unknown",
        ),
        _reason(
            "robots_body_empty",
            "Robots body empty",
            "The received robots response contained no usable body.",
            "parsing",
            "unknown",
        ),
        _reason(
            "robots_body_malformed",
            "Robots body malformed",
            "The received robots body could not produce trustworthy directives.",
            "parsing",
            "unknown",
        ),
        _reason(
            "parser_failure",
            "Parser failure",
            "The registered robots parser did not complete successfully.",
            "parsing",
            "unknown",
        ),
        _reason(
            "evaluation_failure",
            "Evaluation failure",
            "The exact robots evaluation could not produce a trustworthy decision.",
            "evaluation",
            "unknown",
        ),
        _reason(
            "parser_provenance_untrusted",
            "Parser provenance untrusted",
            "The parser identity or provenance did not match the Owner-approved registration.",
            "validation",
            "false",
        ),
        _reason(
            "evidence_missing",
            "Evidence missing",
            "Required robots evidence was not available for the exact request.",
            "evidence_binding",
            "true",
        ),
        _reason(
            "evidence_stale",
            "Evidence stale",
            "The available robots evidence was outside its permitted freshness window.",
            "evidence_binding",
            "true",
        ),
        _reason(
            "evidence_target_mismatch",
            "Target mismatch",
            "The robots evidence was not bound to the exact publisher target.",
            "evidence_binding",
            "false",
        ),
        _reason(
            "evidence_user_agent_mismatch",
            "User-agent mismatch",
            "The robots evidence was produced for a different selected user agent.",
            "evidence_binding",
            "false",
        ),
        _reason(
            "evidence_untrusted",
            "Evidence untrusted",
            "The robots evidence failed provenance or integrity validation.",
            "evidence_binding",
            "false",
        ),
    )
}

ROBOTS_UNAVAILABLE_REASON_DEFINITIONS = MappingProxyType(_DEFINITIONS)


def get_robots_unavailable_reason(code: str) -> RobotsUnavailableReasonDefinition:
    try:
        return ROBOTS_UNAVAILABLE_REASON_DEFINITIONS[code]
    except KeyError as exc:
        raise RobotsUnavailableReasonError(
            f"Robots unavailable reason {code!r} is not registered"
        ) from exc


def owner_summary_for_unavailable_reason(
    code: str,
    *,
    http_status: int | None = None,
) -> str:
    definition = get_robots_unavailable_reason(code)
    if code == "http_not_found":
        if http_status not in {404, 410}:
            raise RobotsUnavailableReasonError("http_not_found requires HTTP status 404 or 410")
        return f"The publisher returned HTTP {http_status} for /robots.txt."
    if code == "http_client_error":
        if http_status is None or not 400 <= http_status <= 499 or http_status in {404, 410}:
            raise RobotsUnavailableReasonError("http_client_error requires another HTTP 4xx status")
        return f"The publisher returned HTTP {http_status} for /robots.txt."
    if code == "http_server_error":
        if http_status is None or not 500 <= http_status <= 599:
            raise RobotsUnavailableReasonError("http_server_error requires an HTTP 5xx status")
        return f"The publisher returned HTTP {http_status} for /robots.txt."
    return definition.description


def validate_unavailable_information(
    *,
    failure_phase: str,
    unavailable_reason: str,
    retryable: str,
    owner_summary: str,
    http_status: int | None = None,
) -> RobotsUnavailableReasonDefinition:
    definition = get_robots_unavailable_reason(unavailable_reason)
    if failure_phase != definition.failure_phase:
        raise RobotsUnavailableReasonError(
            f"{unavailable_reason} belongs to {definition.failure_phase}, not {failure_phase}"
        )
    if retryable not in ROBOTS_RETRYABLE_VALUES:
        raise RobotsUnavailableReasonError("retryable must be true, false, or unknown")
    expected_summary = owner_summary_for_unavailable_reason(
        unavailable_reason,
        http_status=http_status,
    )
    if owner_summary != expected_summary:
        raise RobotsUnavailableReasonError(
            "owner_summary must be generated from the registered reason definition"
        )
    if not 1 <= len(owner_summary) <= 500:
        raise RobotsUnavailableReasonError("owner_summary must contain 1 through 500 characters")
    return definition


__all__ = [
    "ROBOTS_FAILURE_PHASES",
    "ROBOTS_RETRYABLE_VALUES",
    "ROBOTS_UNAVAILABLE_INFORMATION_SCHEMA_VERSION",
    "ROBOTS_UNAVAILABLE_REASON_DEFINITIONS",
    "RobotsFailurePhase",
    "RobotsRetryable",
    "RobotsUnavailableReasonDefinition",
    "RobotsUnavailableReasonError",
    "get_robots_unavailable_reason",
    "owner_summary_for_unavailable_reason",
    "validate_unavailable_information",
]
