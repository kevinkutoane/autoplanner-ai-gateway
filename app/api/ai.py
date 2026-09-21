"""AI execution route compatible with Flutter CloudAIProvider."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, Response

from app.models.requests import AIInvocationRequest
from app.models.responses import AIInvocationResponse
from app.security.auth import AuthenticatedIdentity, get_current_identity
from app.services.request import RequestService, get_request_service

router = APIRouter(prefix="/v1/ai", tags=["AI"])


@router.post("/complete", response_model=AIInvocationResponse)
async def complete_invocation(
    request: AIInvocationRequest,
    response: Response,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
    x_client_version: Optional[str] = Header(default=None, alias="X-Client-Version"),
    request_service: RequestService = Depends(get_request_service),
) -> AIInvocationResponse:
    """Executes a semantic AI invocation with server-owned prompt templates and model routing."""
    # Resolve correlation trace ID: X-Request-ID -> body.id -> new UUID
    correlation_id = (x_request_id or request.id or str(uuid.uuid4())).strip()

    # Pass correlation ID back in response headers for tracing
    response.headers["X-Request-ID"] = correlation_id

    return await request_service.execute_invocation(
        request=request,
        identity=identity,
        correlation_id=correlation_id,
    )
