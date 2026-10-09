from fastapi import APIRouter
from app.core.runtime_version import RUNTIME_REVISION

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "backendRevision": RUNTIME_REVISION}
