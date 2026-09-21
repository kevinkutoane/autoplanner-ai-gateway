"""Main FastAPI application entrypoint for AutoPlanner AI Gateway."""

import logging
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.ai import router as ai_router
from app.api.health import router as health_router
from app.config import settings
from app.exceptions import GatewayException

# Configure basic logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gateway")

app = FastAPI(
    title="AutoPlanner AI Gateway",
    version=settings.GATEWAY_VERSION,
    description="Secure, server-side AI boundary and prompt orchestration gateway for AutoPlanner.",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Client-Version",
        "Accept",
    ],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_guard_and_correlation_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware enforcing payload size limits and propagating X-Request-ID."""
    # 1. Resolve trace ID
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id

    # 2. Enforce HTTP request payload size limit before consuming full body
    content_length = request.headers.get("Content-Length")
    if content_length and content_length.isdigit():
        if int(content_length) > settings.MAX_REQUEST_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": f"Payload exceeds maximum allowed size of {settings.MAX_REQUEST_BYTES} bytes.",
                        "requestId": req_id,
                    }
                },
                headers={"X-Request-ID": req_id},
            )

    # 3. Process request
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# --- Exception Handlers ---


@app.exception_handler(GatewayException)
async def gateway_exception_handler(request: Request, exc: GatewayException) -> JSONResponse:
    req_id = exc.request_id or getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "requestId": req_id,
            }
        },
        headers={"X-Request-ID": req_id} if req_id else None,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    # Extract simplified human-readable validation error
    errors = exc.errors()
    msg = errors[0].get("msg", "Invalid request parameters.") if errors else "Validation error."
    if "Value error," in msg:
        msg = msg.replace("Value error,", "").strip()

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": msg,
                "requestId": req_id,
            }
        },
        headers={"X-Request-ID": req_id} if req_id else None,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    code_map = {
        400: "INVALID_REQUEST",
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "UNKNOWN_OPERATION" if "/v1/ai" in request.url.path else "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        413: "REQUEST_TOO_LARGE",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "AI_PROVIDER_ERROR",
        503: "AI_SERVICE_UNAVAILABLE",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code_map.get(exc.status_code, "HTTP_ERROR"),
                "message": str(exc.detail),
                "requestId": req_id,
            }
        },
        headers={"X-Request-ID": req_id} if req_id else None,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None)
    logger.exception(f"Unhandled exception [request_id={req_id}]: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal server error occurred.",
                "requestId": req_id,
            }
        },
        headers={"X-Request-ID": req_id} if req_id else None,
    )


# Register routes
app.include_router(health_router)
app.include_router(ai_router)
