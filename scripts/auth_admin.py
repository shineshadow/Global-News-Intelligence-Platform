import argparse
import asyncio
import json
import sys

from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory, engine
from app.models import AuthUser, AuthUserRole
from app.services.auth_service import AuthService
from app.services.exceptions import InvalidUpdateError, ResourceConflictError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap and administer GNI site identities and authority."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    bootstrap = commands.add_parser(
        "bootstrap-owner", help="Create the first and highest-authority Owner identity."
    )
    bootstrap.add_argument("--username", required=True)
    bootstrap.add_argument("--display-name", required=True)
    bootstrap.add_argument("--reason", required=True)

    commands.add_parser("list", help="List identities and active roles without credential data.")
    return parser


async def _run(arguments: argparse.Namespace) -> int:
    service = AuthService(
        rp_id=settings.auth_rp_id,
        rp_name=settings.auth_rp_name,
        expected_origin=settings.auth_expected_origin,
    )
    if arguments.command == "bootstrap-owner":
        async with async_session_factory() as session, session.begin():
            user, token = await service.bootstrap_owner(
                session,
                username=arguments.username,
                display_name=arguments.display_name,
                reason=arguments.reason,
            )
            public_id = user.public_id
        print(
            json.dumps(
                {
                    "username": user.username,
                    "public_id": str(public_id),
                    "role": "owner",
                    "enrollment_url": f"{settings.auth_expected_origin.rstrip('/')}/auth/enroll?token={token}",
                    "warning": "This single-use URL is shown once and expires shortly.",
                }
            )
        )
        return 0

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(AuthUser, AuthUserRole.role_slug)
                .outerjoin(
                    AuthUserRole,
                    (AuthUserRole.user_id == AuthUser.id) & (AuthUserRole.status == "active"),
                )
                .order_by(AuthUser.username, AuthUserRole.role_slug)
            )
        ).all()
    grouped: dict[int, dict[str, object]] = {}
    for user, role in rows:
        record = grouped.setdefault(
            user.id,
            {
                "public_id": str(user.public_id),
                "username": user.username,
                "display_name": user.display_name,
                "status": user.status,
                "roles": [],
            },
        )
        if role:
            roles = record["roles"]
            assert isinstance(roles, list)
            roles.append(role)
    print(json.dumps(list(grouped.values()), indent=2))
    return 0


async def main() -> int:
    try:
        return await _run(build_parser().parse_args())
    except (InvalidUpdateError, ResourceConflictError) as exc:
        print(f"Authentication administration failed: {exc}", file=sys.stderr)
        return 2
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
