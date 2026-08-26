from fastapi import APIRouter, Depends

from app.api.dependencies import require_site_access
from app.api.routes import (
    alerts,
    auth,
    calendar,
    calendar_administration,
    ingestion,
    monitors,
    observability,
    source_endpoints,
    sources,
)

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_site_access)],
)

api_router.include_router(auth.router)
api_router.include_router(alerts.router)
api_router.include_router(sources.router)

api_router.include_router(source_endpoints.router)

api_router.include_router(ingestion.router)

api_router.include_router(observability.router)

api_router.include_router(monitors.router)

api_router.include_router(calendar.router)

api_router.include_router(calendar_administration.router)
