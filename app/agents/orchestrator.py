"""Simplified orchestrator — routes all queries to the Product Manager agent.

MVP-2 scope: single agent only.  MVP-3 will add routing to IM + TDL.

Security / governance controls:
- max_tokens per call (SEC-5)
- configurable timeout (NFR-1)
- per-session token tracking (SEC-5)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import anthropic

from app.agents.prompts import PRODUCT_MANAGER_PROMPT, build_user_context
from app.agents.tools import list_available_apis, read_api_doc, search_api_docs
from app.config import settings
from app.models.schemas import UserEnvironment
from app.services.docs_store import DocsStore
from app.services.session_store import SessionStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions for Claude (function-calling format)
# ---------------------------------------------------------------------------

_TOOL_DEFINITIONS = [
    {
        "name": "list_available_apis",
        "description": "Return all indexed marketplace APIs with their documentation file inventory.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "read_api_doc",
        "description": (
            "Read a specific documentation file for a given API. "
            "Use list_available_apis first to discover valid API names and filenames."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "api_name": {
                    "type": "string",
                    "description": "The API folder name (e.g. 'petstore')",
                },
                "filename": {
                    "type": "string",
                    "description": "The doc filename (e.g. 'swagger.md')",
                },
            },
            "required": ["api_name", "filename"],
        },
    },
    {
        "name": "search_api_docs",
        "description": "Search across all API documentation for a keyword or phrase. Returns matching lines with context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The keyword or phrase to search for",
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


def _dispatch_tool(
    tool_name: str, tool_input: Dict[str, Any], docs_store: DocsStore
) -> str:
    """Execute a tool call and return the result as a string."""
    if tool_name == "list_available_apis":
        result = list_available_apis(docs_store)
    elif tool_name == "read_api_doc":
        result = read_api_doc(
            docs_store,
            tool_input.get("api_name", ""),
            tool_input.get("filename", ""),
        )
    elif tool_name == "search_api_docs":
        result = search_api_docs(docs_store, tool_input.get("query", ""))
    else:
        result = f"Error: Unknown tool '{tool_name}'"

    if isinstance(result, str):
        return result
    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Orchestrator result
# ---------------------------------------------------------------------------


@dataclass
class OrchestratorResult:
    """Result from an orchestrator call."""

    message: str
    agent_used: str
    tokens_used: int
    latency_ms: float


# ---------------------------------------------------------------------------
# Main orchestrator function
# ---------------------------------------------------------------------------


def run_agent(
    *,
    message: str,
    session_id: str,
    docs_store: DocsStore,
    session_store: SessionStore,
    history: Optional[List[Dict[str, str]]] = None,
    user_environment: Optional[UserEnvironment] = None,
    api_context: Optional[List[str]] = None,
) -> OrchestratorResult:
    """Run the PM agent with tool use support.

    This is a synchronous function that handles the full tool-use loop:
    1. Send user message to Claude with tool definitions
    2. If Claude wants to use a tool, execute it and send the result back
    3. Repeat until Claude produces a final text response

    Args:
        message: The user's message text.
        session_id: Session ID for token tracking.
        docs_store: DocsStore instance for tool access.
        session_store: SessionStore for token tracking.
        history: Previous messages in the conversation.
        user_environment: User's technical environment context.
        api_context: Optional list of API names to restrict to.

    Returns:
        OrchestratorResult with the agent's response and metadata.

    Raises:
        anthropic.APIError: On API failures (caller should handle).
    """
    start_time = time.time()

    # Build the contextualised user message
    available_apis = api_context or docs_store.list_apis()
    user_content = build_user_context(message, user_environment, available_apis)

    # Build message list
    messages: List[Dict[str, Any]] = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    # Create client
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    total_tokens = 0

    # Tool-use loop (max 10 iterations to prevent infinite loops)
    for _ in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=settings.max_tokens_per_call,
            system=PRODUCT_MANAGER_PROMPT,
            tools=_TOOL_DEFINITIONS,
            messages=messages,
            timeout=60.0,
        )

        # Track tokens
        if response.usage:
            total_tokens += response.usage.input_tokens + response.usage.output_tokens

        # Check if we need to handle tool use
        if response.stop_reason == "tool_use":
            # Process all tool use blocks
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result = _dispatch_tool(
                        block.name, block.input, docs_store
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result,
                        }
                    )

            # Add assistant message and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        # Extract final text response
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)

        final_message = "\n".join(text_parts) if text_parts else ""
        break
    else:
        final_message = "I apologize, but I was unable to complete the request within the allowed number of steps."

    # Track tokens on the session
    session_store.track_tokens(session_id, total_tokens)

    latency_ms = (time.time() - start_time) * 1000

    return OrchestratorResult(
        message=final_message,
        agent_used="product_manager",
        tokens_used=total_tokens,
        latency_ms=latency_ms,
    )
