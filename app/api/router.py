from fastapi import APIRouter

from app.api.routes import (
    source_endpoints,
    sources,
)


api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(sources.router)
api_router.include_router(source_endpoints.router)