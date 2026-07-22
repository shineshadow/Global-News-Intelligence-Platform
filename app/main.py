from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session_factory, engine
from app.redis_client import redis_client

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from app.web.routes import router as web_router


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

register_exception_handlers(app)
app.include_router(web_router)
app.include_router(api_router)

@app.get("/health", response_model=HealthResponse)
async def health_check(response: Response) -> HealthResponse:
    """Check FastAPI, PostgreSQL, and Redis."""

    application_status = "ok"
    database_status = "ok"
    redis_status = "ok"

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
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

WEB_DIR = (
    Path(__file__).resolve().parent
    / "web"
)

app.mount(
    "/static",
    StaticFiles(
        directory=WEB_DIR / "static",
    ),
    name="static",
)