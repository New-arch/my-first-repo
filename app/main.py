"""FastAPI application — Marketplace API Assistant."""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.middleware.logging import setup_audit_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.routers import apis, chat, sessions
from app.services.docs_store import DocsStore
from app.services.session_store import SessionStore

# Structured JSON logging (FR-12)
setup_audit_logging()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — initialise stores on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init docs store + session store. Shutdown: cleanup."""
    # Docs store
    docs_store = DocsStore()
    docs_store.scan()
    app.state.docs_store = docs_store

    # Session store
    app.state.session_store = SessionStore()

    logger.info(
        "Startup complete — %d APIs indexed", len(docs_store.list_apis())
    )
    yield
    logger.info("Shutdown")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Marketplace API Assistant",
    description="AI-powered assistant for marketplace API documentation",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware stack (order matters: outermost first)
# ---------------------------------------------------------------------------

# 1. Request ID — must be outermost so every response gets the header
app.add_middleware(RequestIdMiddleware)

# 2. Rate limiter — only affects POST /chat (SEC-5, FR-10.10)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.chat_rate_limit_per_min,
    window_seconds=60,
)

# 3. CORS — env-based origins
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
# Routers
# ---------------------------------------------------------------------------

app.include_router(apis.router)
app.include_router(sessions.router)
app.include_router(chat.router)


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
