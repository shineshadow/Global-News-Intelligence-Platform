from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)


async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    Provide a database session to a FastAPI route.

    The route or service controls when the transaction commits.
    Any unhandled exception causes the active transaction to roll back.
    """

    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def transaction_session() -> AsyncIterator[AsyncSession]:
    """
    Provide an automatically managed transaction.

    Successful completion commits the transaction.
    An exception rolls the transaction back.
    """

    async with async_session_factory() as session:
        async with session.begin():
            yield session