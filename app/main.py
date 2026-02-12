"""FastAPI application — Marketplace API Assistant."""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.middleware.request_id import RequestIdMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Marketplace API Assistant",
    description="AI-powered assistant for marketplace API documentation",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Middleware stack (order matters: outermost first)
# ---------------------------------------------------------------------------

# 1. Request ID — must be outermost so every response gets the header
app.add_middleware(RequestIdMiddleware)

# 2. CORS — env-based origins
_origins = settings.cors_allowed_origins
if settings.env == "production" and _origins == ["*"]:
    _origins = []  # deny-all by default in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)


# ---------------------------------------------------------------------------
# Global exception handler — no stack traces in responses (SEC-7)
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Unhandled exception request_id=%s: %s",
        request_id,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Health endpoint — unauthenticated
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Health check — returns 200 if the service is running."""
    return {"status": "ok"}
