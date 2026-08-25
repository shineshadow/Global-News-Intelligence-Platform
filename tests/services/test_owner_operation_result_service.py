import pytest

from app.services.owner_operation_result_service import (
    OwnerOperationResult,
    OwnerOperationResultError,
)


def test_registered_robots_operation_result_is_json_safe_and_bounded() -> None:
    result = OwnerOperationResult(
        operation_type="acquisition.evaluate_robots",
        outcome="denied",
        reason_code="acquisition.robots_path_disallowed",
        detail_schema="acquisition.robots_path_disallowed.v1",
        details={"external_decision": "disallowed"},
    )

    assert result.details["external_decision"] == "disallowed"


def test_reason_cannot_be_used_for_wrong_operation_or_schema() -> None:
    with pytest.raises(OwnerOperationResultError, match="does not apply"):
        OwnerOperationResult(
            operation_type="acquisition.retrieve_resource",
            outcome="denied",
            reason_code="acquisition.robots_path_disallowed",
            detail_schema="acquisition.robots_path_disallowed.v1",
            details={},
        )
    with pytest.raises(OwnerOperationResultError, match="schema"):
        OwnerOperationResult(
            operation_type="acquisition.evaluate_robots",
            outcome="denied",
            reason_code="acquisition.robots_path_disallowed",
            detail_schema="wrong.v1",
            details={},
        )
