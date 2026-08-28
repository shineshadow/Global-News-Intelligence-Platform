from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

RETRY_AFTER_ENFORCEMENT = "acquisition.retry_after.enforce"
PROVIDER_HARD_LIMIT_ENFORCEMENT = "acquisition.provider_hard_limits.enforce"
MANUAL_POLL_RATE_ENFORCEMENT = "acquisition.rate_limit.manual_poll_enforce"
ARCHIVE_INSPECTION_LIMITS = "acquisition.archive.inspection_limits"

DEFAULT_ARCHIVE_INSPECTION_LIMITS = {
    "max_depth": 4,
    "max_members": 128,
    "max_total_uncompressed_bytes": 256 * 1024 * 1024,
    "max_member_bytes": 64 * 1024 * 1024,
    "max_expansion_ratio": 100,
    "max_member_path_bytes": 1024,
}

ALL_SCOPES = frozenset(
    {"global", "adapter", "platform", "credential", "origin", "source", "endpoint", "request"}
)


class OwnerPolicyDefinitionError(ValueError):
    """A registered Owner-policy definition rejected a value or scope."""


Validator = Callable[[Any], None]


@dataclass(frozen=True)
class OwnerPolicyDefinition:
    policy_key: str
    definition_version: str
    value_type: str
    _default: Any
    supported_scopes: frozenset[str]
    resolution_point: str
    restart_requirement: str
    external_consequences: str
    audit_evidence: str
    default_path_test: str
    override_path_test: str
    display_name: str
    risk_summary: str
    validator: Validator

    @property
    def default(self) -> Any:
        return deepcopy(self._default)

    def default_value(self) -> Any:
        return deepcopy(self._default)

    def validate(self, value: Any) -> Any:
        self.validator(value)
        return deepcopy(value)


def _boolean(value: Any) -> None:
    if not isinstance(value, bool):
        raise OwnerPolicyDefinitionError("value must be a boolean")


def _archive_limits(value: Any) -> None:
    if not isinstance(value, dict):
        raise OwnerPolicyDefinitionError("value must be a closed object")
    expected = set(DEFAULT_ARCHIVE_INSPECTION_LIMITS)
    if set(value) != expected:
        raise OwnerPolicyDefinitionError("archive limits must contain the exact registered fields")
    for field in expected:
        field_value = value[field]
        if not isinstance(field_value, int) or isinstance(field_value, bool) or field_value <= 0:
            raise OwnerPolicyDefinitionError(f"{field} must be a positive integer")
    if value["max_member_bytes"] > value["max_total_uncompressed_bytes"]:
        raise OwnerPolicyDefinitionError(
            "max_member_bytes cannot exceed max_total_uncompressed_bytes"
        )


def _definition(
    policy_key: str,
    *,
    value_type: str,
    default: Any,
    supported_scopes: frozenset[str] = ALL_SCOPES,
    resolution_point: str,
    consequences: str,
    display_name: str,
    risk_summary: str,
    validator: Validator,
) -> OwnerPolicyDefinition:
    return OwnerPolicyDefinition(
        policy_key=policy_key,
        definition_version="owner-policy-definition.v1",
        value_type=value_type,
        _default=deepcopy(default),
        supported_scopes=supported_scopes,
        resolution_point=resolution_point,
        restart_requirement="none",
        external_consequences=consequences,
        audit_evidence="OwnerPolicyDecisionContext plus selected override and runtime result",
        default_path_test="registered default controls with no matching override",
        override_path_test="exact audited Owner override controls at every supported scope",
        display_name=display_name,
        risk_summary=risk_summary,
        validator=validator,
    )


_DEFINITIONS = {
    RETRY_AFTER_ENFORCEMENT: _definition(
        RETRY_AFTER_ENFORCEMENT,
        value_type="boolean",
        default=True,
        resolution_point="when provider Retry-After evidence governs eligibility",
        consequences="false may retry before the observed provider time",
        display_name="Enforce Retry-After",
        risk_summary="Disabling enforcement may retry sooner than provider guidance.",
        validator=_boolean,
    ),
    PROVIDER_HARD_LIMIT_ENFORCEMENT: _definition(
        PROVIDER_HARD_LIMIT_ENFORCEMENT,
        value_type="boolean",
        default=True,
        resolution_point="when provider quota evidence governs eligibility",
        consequences="false may attempt work despite retained provider-limit evidence",
        display_name="Enforce provider limits",
        risk_summary="Disabling enforcement may cause provider rejection or throttling.",
        validator=_boolean,
    ),
    MANUAL_POLL_RATE_ENFORCEMENT: _definition(
        MANUAL_POLL_RATE_ENFORCEMENT,
        value_type="boolean",
        default=True,
        resolution_point="before manual acquisition rate reservation",
        consequences="false permits an Owner-authorized manual attempt despite local rate denial",
        display_name="Enforce local rates for manual polling",
        risk_summary="Disabling enforcement may exceed locally selected pacing.",
        validator=_boolean,
    ),
    ARCHIVE_INSPECTION_LIMITS: _definition(
        ARCHIVE_INSPECTION_LIMITS,
        value_type="object",
        default=DEFAULT_ARCHIVE_INSPECTION_LIMITS,
        resolution_point="before archive inspection",
        consequences="changes bounded archive depth, count, byte, ratio, and path behavior",
        display_name="Archive inspection limits",
        risk_summary="Larger limits can increase inspection resource use.",
        validator=_archive_limits,
    ),
}

OWNER_POLICY_DEFINITIONS: Mapping[str, OwnerPolicyDefinition] = MappingProxyType(_DEFINITIONS)


class _OwnerPolicyDefaults(Mapping[str, Any]):
    def __getitem__(self, key: str) -> Any:
        return _DEFINITIONS[key].default_value()

    def __iter__(self) -> Iterator[str]:
        return iter(_DEFINITIONS)

    def __len__(self) -> int:
        return len(_DEFINITIONS)


OWNER_POLICY_DEFAULTS: Mapping[str, Any] = _OwnerPolicyDefaults()


def get_policy_definition(policy_key: str) -> OwnerPolicyDefinition:
    try:
        return OWNER_POLICY_DEFINITIONS[policy_key]
    except KeyError as exc:
        raise OwnerPolicyDefinitionError(f"Owner policy {policy_key!r} is not registered") from exc
