from __future__ import annotations

import asyncio

from app.database import async_session_factory
from app.services.artifact_signature_service import import_repository_pinned_release


async def _run() -> None:
    async with async_session_factory() as session, session.begin():
        release = await import_repository_pinned_release(session)
        print(
            "active artifact signature release "
            f"{release.authority_slug}/{release.release_identifier} "
            f"sha256={release.sha256}"
        )


if __name__ == "__main__":
    asyncio.run(_run())

