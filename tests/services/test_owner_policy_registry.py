import pytest

from app.services.owner_policy_registry import (
    DEFAULT_ROBOTS_FETCH_LIMITS,
    OWNER_POLICY_DEFAULTS,
    OWNER_POLICY_DEFINITIONS,
    ROBOTS_CACHE_MAX_AGE_SECONDS,
    ROBOTS_CACHE_MAX_STALE_SECONDS,
    ROBOTS_CRAWL_DELAY_ENFORCEMENT,
    ROBOTS_ENFORCEMENT,
    ROBOTS_FETCH_LIMITS,
    ROBOTS_UNAVAILABLE_ACTION,
    OwnerPolicyDefinitionError,
)


def test_owner_approved_robots_defaults_are_registered_exactly() -> None:
    assert OWNER_POLICY_DEFINITIONS[ROBOTS_ENFORCEMENT].default is True
    assert OWNER_POLICY_DEFINITIONS[ROBOTS_UNAVAILABLE_ACTION].default == "delay"
    assert OWNER_POLICY_DEFINITIONS[ROBOTS_CRAWL_DELAY_ENFORCEMENT].default is True
    assert OWNER_POLICY_DEFINITIONS[ROBOTS_CACHE_MAX_AGE_SECONDS].default == 86_400
    assert OWNER_POLICY_DEFINITIONS[ROBOTS_CACHE_MAX_STALE_SECONDS].default == 604_800
    assert OWNER_POLICY_DEFINITIONS[ROBOTS_FETCH_LIMITS].default == {
        "max_response_bytes": 524_288,
        "max_redirects": 5,
        "connect_timeout_seconds": 10,
        "read_timeout_seconds": 30,
    }
    assert DEFAULT_ROBOTS_FETCH_LIMITS == OWNER_POLICY_DEFINITIONS[ROBOTS_FETCH_LIMITS].default


@pytest.mark.parametrize(
    ("policy_key", "accepted"),
    [
        (ROBOTS_CACHE_MAX_AGE_SECONDS, (300, 86_400)),
        (ROBOTS_CACHE_MAX_STALE_SECONDS, (0, 2_592_000)),
    ],
)
def test_owner_approved_integer_bounds_are_closed_and_reject_booleans(
    policy_key: str,
    accepted: tuple[int, int],
) -> None:
    definition = OWNER_POLICY_DEFINITIONS[policy_key]
    assert definition.validate(accepted[0]) == accepted[0]
    assert definition.validate(accepted[1]) == accepted[1]
    for rejected in (accepted[0] - 1, accepted[1] + 1, True, False):
        with pytest.raises(OwnerPolicyDefinitionError):
            definition.validate(rejected)


def test_fetch_limits_are_closed_bounded_and_defensively_copied() -> None:
    definition = OWNER_POLICY_DEFINITIONS[ROBOTS_FETCH_LIMITS]
    lower = {
        "max_response_bytes": 524_288,
        "max_redirects": 5,
        "connect_timeout_seconds": 1,
        "read_timeout_seconds": 1,
    }
    upper = {
        "max_response_bytes": 2_097_152,
        "max_redirects": 10,
        "connect_timeout_seconds": 30,
        "read_timeout_seconds": 60,
    }
    assert definition.validate(lower) == lower
    assert definition.validate(upper) == upper

    rejected_values = [
        {**lower, "unknown": 1},
        {key: value for key, value in lower.items() if key != "max_redirects"},
        {**lower, "max_response_bytes": 524_287},
        {**lower, "max_redirects": 11},
        {**lower, "connect_timeout_seconds": True},
        {**lower, "read_timeout_seconds": 61},
    ]
    for rejected in rejected_values:
        with pytest.raises(OwnerPolicyDefinitionError):
            definition.validate(rejected)

    copy = definition.default_value()
    copy["max_redirects"] = 9
    assert definition.default_value()["max_redirects"] == 5
    catalog_copy = OWNER_POLICY_DEFAULTS[ROBOTS_FETCH_LIMITS]
    catalog_copy["max_redirects"] = 9
    assert OWNER_POLICY_DEFAULTS[ROBOTS_FETCH_LIMITS]["max_redirects"] == 5


def test_unavailable_action_preserves_all_owner_choices() -> None:
    definition = OWNER_POLICY_DEFINITIONS[ROBOTS_UNAVAILABLE_ACTION]
    assert {definition.validate(value) for value in ("allow", "delay", "deny")} == {
        "allow",
        "delay",
        "deny",
    }
    with pytest.raises(OwnerPolicyDefinitionError):
        definition.validate("service-decides")


def test_robots_policy_scope_preserves_complete_owner_precedence_family() -> None:
    expected = {
        "global",
        "adapter",
        "platform",
        "credential",
        "origin",
        "source",
        "endpoint",
        "request",
    }
    for policy_key in (
        ROBOTS_ENFORCEMENT,
        ROBOTS_UNAVAILABLE_ACTION,
        ROBOTS_CRAWL_DELAY_ENFORCEMENT,
        ROBOTS_CACHE_MAX_AGE_SECONDS,
        ROBOTS_CACHE_MAX_STALE_SECONDS,
        ROBOTS_FETCH_LIMITS,
    ):
        assert OWNER_POLICY_DEFINITIONS[policy_key].supported_scopes == expected
