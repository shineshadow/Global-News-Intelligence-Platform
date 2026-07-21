from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.redis_client import redis_client


class HealthResponse(BaseModel):
    """Health status returned by the application."""

    status: str
    database: str
    redis: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Close shared resources when the application stops."""

    yield

    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="Global News Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check(response: Response) -> HealthResponse:
    """Check FastAPI, PostgreSQL, and Redis."""

    application_status = "ok"
    database_status = "ok"
    redis_status = "ok"

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        application_status = "degraded"
        database_status = "unavailable"

    try:
        await redis_client.ping()
    except RedisError:
        application_status = "degraded"
        redis_status = "unavailable"

    if application_status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=application_status,
        database=database_status,
        redis=redis_status,
    )