import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.database import engine


T = TypeVar("T")


def run_async(
    operation: Callable[[], Awaitable[T]],
) -> T:
    """
    Run one async operation from a synchronous Celery task.

    Dispose SQLAlchemy's async connection pool before destroying the
    event loop so pooled connections are never reused by another
    asyncio.run() loop.
    """

    async def runner() -> T:
        try:
            return await operation()
        finally:
            await engine.dispose()

    return asyncio.run(runner())