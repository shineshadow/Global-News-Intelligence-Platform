from fastapi import APIRouter

from app.api.dependencies import CurrentPrincipal

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
async def current_identity(principal: CurrentPrincipal) -> dict[str, object]:
    return {
        "public_id": str(principal.public_id),
        "username": principal.username,
        "display_name": principal.display_name,
        "actor_ref": principal.actor_ref,
        "roles": list(principal.roles),
        "capabilities": sorted(principal.capabilities),
        "session_public_id": str(principal.session_public_id),
    }
