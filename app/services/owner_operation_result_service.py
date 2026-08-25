from __future__ import annotations

import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


class OwnerOperationResultError(ValueError):
    """An operation result did not match the registered Owner information contract."""


_REASONS = {
    "acquisition.robots_cached_evidence": (
        "acquisition.robots_cached_evidence.v1",
        frozenset({"acquisition.retrieve_robots"}),
    ),
    "acquisition.robots_evidence_retrieved": (
        "acquisition.robots_evidence_retrieved.v1",
        frozenset({"acquisition.retrieve_robots"}),
    ),
    "acquisition.robots_path_allowed": (
        "acquisition.robots_path_allowed.v1",
        frozenset({"acquisition.evaluate_robots"}),
    ),
    "acquisition.robots_path_disallowed": (
        "acquisition.robots_path_disallowed.v1",
        frozenset({"acquisition.evaluate_robots"}),
    ),
    "acquisition.robots_evidence_unavailable": (
        "acquisition.robots_evidence_unavailable.v1",
        frozenset({"acquisition.retrieve_robots", "acquisition.evaluate_robots"}),
    ),
    "acquisition.robots_evidence_unreachable": (
        "acquisition.robots_evidence_unreachable.v1",
        frozenset({"acquisition.retrieve_robots"}),
    ),
    "acquisition.robots_evidence_stale": (
        "acquisition.robots_evidence_stale.v1",
        frozenset({"acquisition.retrieve_robots", "acquisition.evaluate_robots"}),
    ),
    "acquisition.robots_restriction_not_enforced": (
        "acquisition.robots_restriction_not_enforced.v1",
        frozenset({"acquisition.evaluate_robots"}),
    ),
    "acquisition.robots_crawl_delay": (
        "acquisition.robots_crawl_delay.v1",
        frozenset({"acquisition.retrieve_resource"}),
    ),
    "acquisition.resource_retrieval_authorized": (
        "acquisition.resource_retrieval_authorized.v1",
        frozenset({"acquisition.retrieve_resource"}),
    ),
}

OWNER_OPERATION_REASON_REGISTRY = MappingProxyType(_REASONS)
OWNER_OPERATION_TYPES = frozenset(
    {
        "acquisition.retrieve_robots",
        "acquisition.evaluate_robots",
        "acquisition.retrieve_resource",
    }
)
OWNER_OPERATION_OUTCOMES = frozenset(
    {"retrieved", "not_modified", "cached", "permitted", "denied", "delay", "allow", "deny", "unavailable", "delayed"}
)


@dataclass(frozen=True)
class OwnerOperationResult:
    operation_type: str
    outcome: str
    reason_code: str
    detail_schema: str
    details: dict[str, Any]

    def __post_init__(self) -> None:
        if self.operation_type not in OWNER_OPERATION_TYPES:
            raise OwnerOperationResultError("Owner operation type is not registered.")
        if self.outcome not in OWNER_OPERATION_OUTCOMES:
            raise OwnerOperationResultError("Owner operation outcome is not registered.")
        try:
            expected_schema, allowed_operations = OWNER_OPERATION_REASON_REGISTRY[
                self.reason_code
            ]
        except KeyError as exc:
            raise OwnerOperationResultError("Owner operation reason is not registered.") from exc
        if self.detail_schema != expected_schema:
            raise OwnerOperationResultError("Owner operation detail schema does not match reason.")
        if self.operation_type not in allowed_operations:
            raise OwnerOperationResultError("Owner operation reason does not apply to operation.")
        try:
            encoded = json.dumps(self.details, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise OwnerOperationResultError("Owner operation details must be JSON-safe.") from exc
        if len(encoded.encode()) > 65_536:
            raise OwnerOperationResultError("Owner operation details exceed the bounded size.")
