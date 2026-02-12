"""Router for the chat endpoint (FR-4).

Security controls:
- Input validation via Pydantic (message length, session_id format, api_context)
- Environment description sanitisation (FR-11.6)
- Structured error responses without internal details (SEC-7)
- Audit logging of every request (SEC-9 / FR-12.1)
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agents.orchestrator import OrchestratorResult, run_agent
from app.config import settings
from app.dependencies import verify_api_key
from app.models.schemas import ChatRequest, ChatResponse, MessageRecord

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the AI assistant",
    dependencies=[Depends(verify_api_key)],
)
async def chat(body: ChatRequest, request: Request):
    """Process a chat message through the orchestrator agent (FR-4.1).

    Validates the session, checks API context, runs the agent, records
    messages, and returns the response with metadata.
    """
    request_id = getattr(request.state, "request_id", None)
    session_store = request.app.state.session_store
    docs_store = request.app.state.docs_store

    # --- Validate session exists ---
    session = session_store.get_session(body.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{body.session_id}' not found",
        )

    # --- Validate api_context if provided ---
    if body.api_context:
        available = docs_store.list_apis()
        invalid = [name for name in body.api_context if name not in available]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown API(s) in api_context: {invalid}. "
                    f"Available: {available}"
                ),
            )

    # --- Check token budget ---
    if session.tokens_used >= settings.session_token_budget:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Session token budget exhausted. Start a new session.",
        )

    # --- Build conversation history for agent ---
    history = []
    for msg in session.messages:
        history.append({"role": msg.role, "content": msg.content})

    # --- Run the agent ---
    start_time = time.time()
    try:
        result: OrchestratorResult = await run_agent(
            message=body.message,
            session_id=body.session_id,
            docs_store=docs_store,
            session_store=session_store,
            history=history,
            user_environment=session.user_environment,
            api_context=body.api_context,
        )
    except Exception:
        logger.exception(
            "Agent error session_id=%s request_id=%s",
            body.session_id,
            request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent processing failed. Please try again.",
        )

    # --- Record messages in session ---
    session_store.add_message(
        body.session_id,
        MessageRecord(role="user", content=body.message),
    )
    session_store.add_message(
        body.session_id,
        MessageRecord(
            role="assistant",
            content=result.message,
            agent_used=result.agent_used,
        ),
    )

    # --- Audit log (FR-12.1): metadata only, no message content ---
    latency_ms = (time.time() - start_time) * 1000
    logger.info(
        "chat_request",
        extra={
            "session_id": body.session_id,
            "agent_used": result.agent_used,
            "tokens_used": result.tokens_used,
            "latency_ms": round(latency_ms, 1),
            "request_id": request_id,
        },
    )

    return ChatResponse(
        session_id=body.session_id,
        agent_used=result.agent_used,
        message=result.message,
        code_blocks=None,
        request_id=request_id,
    )
