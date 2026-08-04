import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.database import async_session_factory, engine
from app.models import OwnerPolicyOverride, OwnerPolicyOverrideEvent
from app.services.owner_policy_service import (
    OWNER_POLICY_DEFAULTS,
    OwnerPolicyContext,
    OwnerPolicyError,
    OwnerPolicyService,
)

SCOPES = ("global", "adapter", "platform", "credential", "origin", "source", "endpoint", "request")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, inspect, consume, and revoke owner-authorized policy overrides."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    set_command = commands.add_parser("set", help="Create or replace one scoped override.")
    set_command.add_argument("policy_key")
    set_command.add_argument("value", help="JSON value, such as false, 10, or '\"custom\"'.")
    set_command.add_argument("--scope-type", choices=SCOPES, default="global")
    set_command.add_argument("--scope-identity", default="*")
    set_command.add_argument("--actor", required=True)
    set_command.add_argument("--reason", required=True)
    set_command.add_argument("--acknowledge-risk", required=True)
    set_command.add_argument("--priority", type=int, default=0)
    set_command.add_argument("--valid-from", type=_instant)
    set_command.add_argument("--valid-until", type=_instant)
    set_command.add_argument("--max-uses", type=int)
    set_command.add_argument("--once", action="store_true")

    revoke = commands.add_parser("revoke", help="Revoke an active override by database ID.")
    revoke.add_argument("override_id", type=int)
    revoke.add_argument("--actor", required=True)
    revoke.add_argument("--reason", required=True)

    listing = commands.add_parser("list", help="List retained overrides.")
    listing.add_argument("--policy-key")
    listing.add_argument("--active-only", action="store_true")

    effective = commands.add_parser("effective", help="Resolve one effective policy value.")
    effective.add_argument("policy_key")
    effective.add_argument("--default", help="JSON default; registered defaults are automatic.")
    effective.add_argument("--adapter")
    effective.add_argument("--platform")
    effective.add_argument("--credential-id", type=int, action="append", default=[])
    effective.add_argument("--origin")
    effective.add_argument("--source-id", type=int)
    effective.add_argument("--endpoint-id", type=int)
    effective.add_argument("--request-identity")

    history = commands.add_parser("history", help="List append-only events for an override.")
    history.add_argument("override_id", type=int)
    return parser


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("Timestamp must include a UTC offset or Z.")
    return parsed


def _json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise OwnerPolicyError(f"Policy value must be valid JSON: {exc.msg}.") from exc


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


async def _run(arguments: argparse.Namespace) -> int:
    service = OwnerPolicyService()
    if arguments.command == "set":
        max_uses = 1 if arguments.once else arguments.max_uses
        if arguments.once and arguments.max_uses is not None:
            raise OwnerPolicyError("Use either --once or --max-uses, not both.")
        async with async_session_factory() as session, session.begin():
            override = await service.set_override(
                session,
                policy_key=arguments.policy_key,
                value=_json(arguments.value),
                scope_type=arguments.scope_type,
                scope_identity=arguments.scope_identity,
                actor=arguments.actor,
                reason=arguments.reason,
                risk_acknowledgement=arguments.acknowledge_risk,
                priority=arguments.priority,
                valid_from=arguments.valid_from,
                valid_until=arguments.valid_until,
                max_uses=max_uses,
            )
            result = _override_dict(override)
        _print(result)
        return 0
    if arguments.command == "revoke":
        async with async_session_factory() as session, session.begin():
            override = await service.revoke_override(
                session,
                override_id=arguments.override_id,
                actor=arguments.actor,
                reason=arguments.reason,
            )
            result = _override_dict(override)
        _print(result)
        return 0
    if arguments.command == "list":
        statement = select(OwnerPolicyOverride).order_by(OwnerPolicyOverride.id)
        if arguments.policy_key:
            statement = statement.where(OwnerPolicyOverride.policy_key == arguments.policy_key)
        if arguments.active_only:
            statement = statement.where(OwnerPolicyOverride.status == "active")
        async with async_session_factory() as session:
            rows = (await session.scalars(statement)).all()
        _print([_override_dict(row) for row in rows])
        return 0
    if arguments.command == "effective":
        if arguments.default is None and arguments.policy_key not in OWNER_POLICY_DEFAULTS:
            raise OwnerPolicyError("Unknown policy requires an explicit JSON --default value.")
        default = (
            OWNER_POLICY_DEFAULTS[arguments.policy_key]
            if arguments.default is None
            else _json(arguments.default)
        )
        async with async_session_factory() as session:
            decision = await service.resolve(
                session,
                policy_key=arguments.policy_key,
                default=default,
                context=OwnerPolicyContext(
                    adapter=arguments.adapter,
                    platform=arguments.platform,
                    credential_ids=tuple(arguments.credential_id),
                    origin=arguments.origin,
                    source_id=arguments.source_id,
                    endpoint_id=arguments.endpoint_id,
                    request_identity=arguments.request_identity,
                ),
            )
        _print(decision.__dict__)
        return 0
    async with async_session_factory() as session:
        rows = (
            await session.scalars(
                select(OwnerPolicyOverrideEvent)
                .where(OwnerPolicyOverrideEvent.override_id == arguments.override_id)
                .order_by(OwnerPolicyOverrideEvent.id)
            )
        ).all()
    _print(
        [
            {
                "id": row.id,
                "event_type": row.event_type,
                "actor": row.actor,
                "reason": row.reason,
                "details": row.details,
                "recorded_at": row.recorded_at,
            }
            for row in rows
        ]
    )
    return 0


def _override_dict(row: OwnerPolicyOverride) -> dict[str, Any]:
    return {
        "id": row.id,
        "public_id": row.public_id,
        "policy_key": row.policy_key,
        "value": row.policy_value,
        "scope_type": row.scope_type,
        "scope_identity": row.scope_identity,
        "priority": row.priority,
        "status": row.status,
        "valid_from": row.valid_from,
        "valid_until": row.valid_until,
        "max_uses": row.max_uses,
        "uses_consumed": row.uses_consumed,
        "actor": row.actor,
        "reason": row.reason,
        "risk_acknowledgement": row.risk_acknowledgement,
    }


async def main() -> int:
    try:
        return await _run(build_parser().parse_args())
    except OwnerPolicyError as exc:
        print(f"Owner policy command failed: {exc}", file=sys.stderr)
        return 2
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
