from fastapi import APIRouter

from app.api.routes import (
    alerts,
    calendar,
    ingestion,
    monitors,
    observability,
    source_endpoints,
    sources,
)

api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(
    alerts.router
)
api_router.include_router(
    sources.router
)

api_router.include_router(
    source_endpoints.router
)

api_router.include_router(
    ingestion.router
)

api_router.include_router(
    observability.router
)

api_router.include_router(
    monitors.router
)

api_router.include_router(
    calendar.router
)
