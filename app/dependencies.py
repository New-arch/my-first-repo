"""FastAPI dependencies for authentication and shared state."""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_api_key(
    x_api_key: str = Header(..., description="API key for endpoint access"),
) -> str:
    """Validate the X-API-Key header against the configured APP_API_KEY.

    Returns the validated key on success; raises 401 on failure.
    """
    if not settings.app_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server API key not configured",
        )
    if not secrets.compare_digest(x_api_key, settings.app_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key


async def verify_admin_key(
    x_admin_key: str = Header(
        ...,
        alias="X-Admin-Key",
        description="Admin API key for privileged endpoints",
    ),
) -> str:
    """Validate the X-Admin-Key header for admin-only endpoints.

    Returns the validated key on success; raises 403 on failure.
    """
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured",
        )
    if not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )
    return x_admin_key
