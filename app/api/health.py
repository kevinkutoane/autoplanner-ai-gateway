"""Health check API route."""

import time
from fastapi import APIRouter
from app.config import settings
from app.models.responses import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns gateway operational health status without leaking configuration or secrets."""
    return HealthResponse(
        status="healthy",
        version=settings.GATEWAY_VERSION,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
