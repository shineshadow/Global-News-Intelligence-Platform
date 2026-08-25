import pytest

from app.services.robots_unavailable_reason_registry import (
    ROBOTS_FAILURE_PHASES,
    ROBOTS_RETRYABLE_VALUES,
    ROBOTS_UNAVAILABLE_INFORMATION_SCHEMA_VERSION,
    ROBOTS_UNAVAILABLE_REASON_DEFINITIONS,
    RobotsUnavailableReasonError,
    owner_summary_for_unavailable_reason,
    validate_unavailable_information,
)


def test_version_one_unavailable_taxonomy_is_closed_and_useful() -> None:
    assert (
        ROBOTS_UNAVAILABLE_INFORMATION_SCHEMA_VERSION
        == "acquisition.robots.unavailable-information.v1"
    )
    assert ROBOTS_FAILURE_PHASES == {
        "retrieval",
        "validation",
        "parsing",
        "evaluation",
        "evidence_binding",
    }
    assert ROBOTS_RETRYABLE_VALUES == {"true", "false", "unknown"}
    assert set(ROBOTS_UNAVAILABLE_REASON_DEFINITIONS) == {
        "http_not_found",
        "http_client_error",
        "http_server_error",
        "dns_failure",
        "connection_failure",
        "connection_timeout",
        "read_timeout",
        "tls_failure",
        "redirect_limit_reached",
        "redirect_destination_rejected",
        "egress_guard_rejected",
        "response_too_large",
        "robots_body_empty",
        "robots_body_malformed",
        "parser_failure",
        "evaluation_failure",
        "parser_provenance_untrusted",
        "evidence_missing",
        "evidence_stale",
        "evidence_target_mismatch",
        "evidence_user_agent_mismatch",
        "evidence_untrusted",
    }
    assert "unavailable" not in ROBOTS_UNAVAILABLE_REASON_DEFINITIONS
    assert "unknown" not in ROBOTS_UNAVAILABLE_REASON_DEFINITIONS
    assert {
        definition.failure_phase for definition in ROBOTS_UNAVAILABLE_REASON_DEFINITIONS.values()
    } == ROBOTS_FAILURE_PHASES
    assert all(
        definition.internal_information
        and definition.owner_information
        and definition.future_ui_surface == "admin"
        for definition in ROBOTS_UNAVAILABLE_REASON_DEFINITIONS.values()
    )


def test_http_status_is_preserved_in_registered_owner_summary() -> None:
    assert owner_summary_for_unavailable_reason("http_not_found", http_status=404) == (
        "The publisher returned HTTP 404 for /robots.txt."
    )
    assert owner_summary_for_unavailable_reason("http_server_error", http_status=503) == (
        "The publisher returned HTTP 503 for /robots.txt."
    )
    with pytest.raises(RobotsUnavailableReasonError):
        owner_summary_for_unavailable_reason("http_not_found", http_status=500)


def test_phase_reason_retryability_and_summary_are_registry_validated() -> None:
    summary = owner_summary_for_unavailable_reason("connection_timeout")
    definition = validate_unavailable_information(
        failure_phase="retrieval",
        unavailable_reason="connection_timeout",
        retryable="true",
        owner_summary=summary,
    )
    assert definition.display_label == "Connection timeout"

    with pytest.raises(RobotsUnavailableReasonError):
        validate_unavailable_information(
            failure_phase="parsing",
            unavailable_reason="connection_timeout",
            retryable="true",
            owner_summary=summary,
        )
    with pytest.raises(RobotsUnavailableReasonError):
        validate_unavailable_information(
            failure_phase="retrieval",
            unavailable_reason="connection_timeout",
            retryable="sometimes",
            owner_summary=summary,
        )


def test_owner_summary_cannot_be_replaced_with_raw_exception_or_secret_text() -> None:
    with pytest.raises(RobotsUnavailableReasonError):
        validate_unavailable_information(
            failure_phase="retrieval",
            unavailable_reason="connection_failure",
            retryable="true",
            owner_summary="Authorization: Bearer secret raw socket exception",
        )


def test_unregistered_reason_fails_explicitly() -> None:
    with pytest.raises(RobotsUnavailableReasonError, match="not registered"):
        owner_summary_for_unavailable_reason("network_problem")
