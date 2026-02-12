"""Router for chat session CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import verify_api_key
from app.models.schemas import (
    EnvironmentUpdate,
    MessageRecord,
    SessionCreate,
    SessionResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _session_to_response(session) -> SessionResponse:
    """Convert internal SessionData to the response model."""
    return SessionResponse(
        id=session.id,
        created_at=session.created_at,
        user_environment=session.user_environment,
        messages=session.messages,
    )


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
    dependencies=[Depends(verify_api_key)],
)
async def create_session(body: SessionCreate, request: Request):
    """Create a session with optional user environment (FR-2.1)."""
    store = request.app.state.session_store
    try:
        session = store.create_session(user_environment=body.user_environment)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    return _session_to_response(session)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session with message history",
    dependencies=[Depends(verify_api_key)],
)
async def get_session(session_id: str, request: Request):
    """Return full session with message history (FR-2.3)."""
    store = request.app.state.session_store
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return _session_to_response(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
    dependencies=[Depends(verify_api_key)],
)
async def delete_session(session_id: str, request: Request):
    """Remove a session and its history (FR-2.4)."""
    store = request.app.state.session_store
    deleted = store.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return None


@router.patch(
    "/{session_id}/environment",
    response_model=SessionResponse,
    summary="Update user environment",
    dependencies=[Depends(verify_api_key)],
)
async def update_environment(
    session_id: str, body: EnvironmentUpdate, request: Request
):
    """Update the user's technical environment for a session (FR-3.4)."""
    store = request.app.state.session_store
    session = store.update_environment(session_id, body.user_environment)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return _session_to_response(session)
