"""Router for API documentation discovery endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import verify_admin_key, verify_api_key
from app.models.schemas import ApiInfo

router = APIRouter(prefix="/apis", tags=["apis"])


@router.get(
    "",
    response_model=List[ApiInfo],
    summary="List all available APIs",
    dependencies=[Depends(verify_api_key)],
)
async def list_apis(request: Request):
    """Return all indexed APIs with their doc file inventory (FR-1.3)."""
    store = request.app.state.docs_store
    apis = store.list_apis()
    return [
        ApiInfo(name=name, available_docs=store.get_api_info(name)["available_docs"])
        for name in apis
    ]


@router.get(
    "/{api_name}",
    response_model=ApiInfo,
    summary="Get single API detail",
    dependencies=[Depends(verify_api_key)],
)
async def get_api(api_name: str, request: Request):
    """Return metadata and doc listing for a single API (FR-1.4)."""
    store = request.app.state.docs_store
    info = store.get_api_info(api_name)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API '{api_name}' not found. Available: {store.list_apis()}",
        )
    return ApiInfo(**info)


@router.post(
    "/refresh",
    summary="Hot-reload API documentation (admin only)",
    dependencies=[Depends(verify_api_key), Depends(verify_admin_key)],
)
async def refresh_apis(request: Request):
    """Re-scan the docs directory without restarting the server (FR-1.5)."""
    store = request.app.state.docs_store
    count = store.refresh()
    return {"status": "refreshed", "api_count": count}
