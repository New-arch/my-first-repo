"""Orchestrator — routes queries to specialised sub-agents via Claude Agent SDK.

Uses the Claude Agent SDK's query() function with AgentDefinition to
orchestrate three sub-agents: Product Manager, Integration Manager, and
Technical Dev Lead.

Security / governance controls:
- max_turns limit per call (SEC-5)
- per-session token tracking (SEC-5)
- permission_mode="bypassPermissions" for automated backend (no interactive prompts)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from app.agents.prompts import (
    INTEGRATION_MANAGER_PROMPT,
    ORCHESTRATOR_PROMPT,
    PRODUCT_MANAGER_PROMPT,
    TECHNICAL_DEV_LEAD_PROMPT,
    build_full_prompt,
)
from app.agents.tools import create_docs_mcp_server
from app.config import settings
from app.models.schemas import UserEnvironment
from app.services.docs_store import DocsStore
from app.services.session_store import SessionStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP tool names (prefixed with mcp__{server_name}__{tool_name})
# ---------------------------------------------------------------------------

MCP_TOOLS = [
    "mcp__marketplace-docs__list_available_apis",
    "mcp__marketplace-docs__read_api_doc",
    "mcp__marketplace-docs__search_api_docs",
]


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


async def run_agent(
    *,
    message: str,
    session_id: str,
    docs_store: DocsStore,
    session_store: SessionStore,
    history: Optional[List[Dict[str, str]]] = None,
    user_environment: Optional[UserEnvironment] = None,
    api_context: Optional[List[str]] = None,
) -> OrchestratorResult:
    """Run the orchestrator via Claude Agent SDK.

    This is an async function that:
    1. Creates an in-process MCP server for doc tools
    2. Defines three sub-agents (PM, IM, TDL) via AgentDefinition
    3. Runs the SDK's query() with the orchestrator prompt
    4. Collects the final response and token usage from ResultMessage

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
    """
    start_time = time.time()

    # Build MCP server for documentation tools
    docs_server = create_docs_mcp_server(docs_store)

    # Build the full prompt with history and context
    available_apis = api_context or docs_store.list_apis()
    prompt = build_full_prompt(
        message=message,
        history=history,
        user_environment=user_environment,
        api_context=api_context,
        available_apis=available_apis,
    )

    # Configure the SDK with orchestrator + sub-agents
    options = ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        model="claude-sonnet-4-5-20250929",
        mcp_servers={"marketplace-docs": docs_server},
        allowed_tools=MCP_TOOLS + ["Task"],
        permission_mode="bypassPermissions",
        max_turns=10,
        env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
        agents={
            "product_manager": AgentDefinition(
                description="Answers business/product questions about marketplace APIs",
                prompt=PRODUCT_MANAGER_PROMPT,
                tools=MCP_TOOLS,
            ),
            "integration_manager": AgentDefinition(
                description="Advises on API integration, auth, config, error handling",
                prompt=INTEGRATION_MANAGER_PROMPT,
                tools=MCP_TOOLS,
            ),
            "technical_dev_lead": AgentDefinition(
                description="Writes production-quality code tailored to user's stack",
                prompt=TECHNICAL_DEV_LEAD_PROMPT,
                tools=MCP_TOOLS,
            ),
        },
    )

    # Run agent and collect result from async iterator
    final_text = ""
    agent_used = "orchestrator"
    tokens_used = 0

    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    final_text = block.text
                # Detect which sub-agent was invoked via Task tool
                if hasattr(block, "name") and block.name == "Task":
                    subagent = getattr(block, "input", {}).get(
                        "subagent_type", "orchestrator"
                    )
                    agent_used = subagent
        elif isinstance(msg, ResultMessage):
            usage = msg.usage or {}
            tokens_used = usage.get("input_tokens", 0) + usage.get(
                "output_tokens", 0
            )

    # Track tokens on the session
    session_store.track_tokens(session_id, tokens_used)

    latency_ms = (time.time() - start_time) * 1000

    return OrchestratorResult(
        message=final_text,
        agent_used=agent_used,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
