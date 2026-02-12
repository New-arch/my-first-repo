"""TDD tests for Claude Agent SDK migration.

Tests written BEFORE implementation to define expected behavior:
- New prompts exist (IM, TDL, Orchestrator)
- MCP server factory creates in-process server
- Orchestrator is async and uses SDK
- Chat router awaits async run_agent
"""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import API_KEY


# ---------------------------------------------------------------------------
# T1: Prompt existence and content tests (FR-5, FR-6, FR-7, FR-8, FR-11)
# ---------------------------------------------------------------------------


class TestPrompts:
    """All four agent prompts exist with required content."""

    def test_product_manager_prompt_exists(self):
        """FR-5: Product Manager prompt exists."""
        from app.agents.prompts import PRODUCT_MANAGER_PROMPT
        assert isinstance(PRODUCT_MANAGER_PROMPT, str)
        assert len(PRODUCT_MANAGER_PROMPT) > 100

    def test_integration_manager_prompt_exists(self):
        """FR-6: Integration Manager prompt exists."""
        from app.agents.prompts import INTEGRATION_MANAGER_PROMPT
        assert isinstance(INTEGRATION_MANAGER_PROMPT, str)
        assert len(INTEGRATION_MANAGER_PROMPT) > 100

    def test_technical_dev_lead_prompt_exists(self):
        """FR-7: Technical Dev Lead prompt exists."""
        from app.agents.prompts import TECHNICAL_DEV_LEAD_PROMPT
        assert isinstance(TECHNICAL_DEV_LEAD_PROMPT, str)
        assert len(TECHNICAL_DEV_LEAD_PROMPT) > 100

    def test_orchestrator_prompt_exists(self):
        """FR-8: Orchestrator prompt exists."""
        from app.agents.prompts import ORCHESTRATOR_PROMPT
        assert isinstance(ORCHESTRATOR_PROMPT, str)
        assert len(ORCHESTRATOR_PROMPT) > 100

    def test_pm_prompt_has_injection_resistance(self):
        """FR-11: PM prompt includes injection resistance."""
        from app.agents.prompts import PRODUCT_MANAGER_PROMPT
        assert "Security Rules" in PRODUCT_MANAGER_PROMPT
        assert "Refuse off-topic" in PRODUCT_MANAGER_PROMPT or "off-topic" in PRODUCT_MANAGER_PROMPT.lower()

    def test_im_prompt_has_injection_resistance(self):
        """FR-11: IM prompt includes injection resistance."""
        from app.agents.prompts import INTEGRATION_MANAGER_PROMPT
        assert "Security Rules" in INTEGRATION_MANAGER_PROMPT

    def test_tdl_prompt_has_injection_resistance(self):
        """FR-11: TDL prompt includes injection resistance."""
        from app.agents.prompts import TECHNICAL_DEV_LEAD_PROMPT
        assert "Security Rules" in TECHNICAL_DEV_LEAD_PROMPT

    def test_orchestrator_prompt_has_injection_resistance(self):
        """FR-11: Orchestrator prompt includes injection resistance."""
        from app.agents.prompts import ORCHESTRATOR_PROMPT
        assert "Security Rules" in ORCHESTRATOR_PROMPT

    def test_im_prompt_covers_auth_and_integration(self):
        """FR-6.1–6.5: IM prompt mentions auth, integration, error handling."""
        from app.agents.prompts import INTEGRATION_MANAGER_PROMPT
        prompt_lower = INTEGRATION_MANAGER_PROMPT.lower()
        assert "auth" in prompt_lower
        assert "integration" in prompt_lower or "integrate" in prompt_lower
        assert "error" in prompt_lower

    def test_tdl_prompt_covers_code_gen_and_secrets(self):
        """FR-7, FR-11.7: TDL prompt mentions code gen + no real secrets."""
        from app.agents.prompts import TECHNICAL_DEV_LEAD_PROMPT
        prompt_lower = TECHNICAL_DEV_LEAD_PROMPT.lower()
        assert "code" in prompt_lower
        assert "secret" in prompt_lower or "placeholder" in prompt_lower

    def test_orchestrator_prompt_covers_routing(self):
        """FR-8.1–8.4: Orchestrator prompt describes routing logic."""
        from app.agents.prompts import ORCHESTRATOR_PROMPT
        prompt_lower = ORCHESTRATOR_PROMPT.lower()
        assert "product manager" in prompt_lower or "product_manager" in prompt_lower
        assert "integration manager" in prompt_lower or "integration_manager" in prompt_lower
        assert "technical dev lead" in prompt_lower or "technical_dev_lead" in prompt_lower

    def test_build_full_prompt_exists(self):
        """build_full_prompt helper exists and formats history + message."""
        from app.agents.prompts import build_full_prompt
        result = build_full_prompt(
            message="Hello",
            history=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hey"}],
            user_environment=None,
            api_context=None,
            available_apis=["petstore"],
        )
        assert "Hello" in result
        assert "Hi" in result
        assert "Hey" in result
        assert "petstore" in result


# ---------------------------------------------------------------------------
# T2: MCP server factory tests (FR-9)
# ---------------------------------------------------------------------------


class TestMCPServerFactory:
    """create_docs_mcp_server produces an MCP server config."""

    def test_factory_function_exists(self):
        """FR-9: create_docs_mcp_server is importable."""
        from app.agents.tools import create_docs_mcp_server
        assert callable(create_docs_mcp_server)

    def test_factory_returns_mcp_config(self):
        """FR-9: Factory returns an McpSdkServerConfig dict-like."""
        from app.agents.tools import create_docs_mcp_server
        mock_store = MagicMock()
        mock_store.list_apis.return_value = ["petstore"]
        mock_store.get_api_info.return_value = {"name": "petstore", "available_docs": []}

        server = create_docs_mcp_server(mock_store)
        # SDK returns McpSdkServerConfig which is a TypedDict with type="sdk"
        assert server is not None

    def test_plain_tool_functions_still_work(self):
        """Existing plain functions remain importable and functional."""
        from app.agents.tools import list_available_apis, read_api_doc, search_api_docs
        assert callable(list_available_apis)
        assert callable(read_api_doc)
        assert callable(search_api_docs)


# ---------------------------------------------------------------------------
# T3: Orchestrator is async and uses SDK types (FR-8)
# ---------------------------------------------------------------------------


class TestOrchestratorAsync:
    """run_agent is now async and returns OrchestratorResult."""

    def test_run_agent_is_coroutine_function(self):
        """run_agent must be async (coroutine function)."""
        import asyncio
        from app.agents.orchestrator import run_agent
        assert asyncio.iscoroutinefunction(run_agent), \
            "run_agent must be an async function to use Claude Agent SDK"

    def test_orchestrator_result_still_has_expected_fields(self):
        """OrchestratorResult dataclass unchanged for backward compat."""
        from app.agents.orchestrator import OrchestratorResult
        result = OrchestratorResult(
            message="test", agent_used="pm", tokens_used=10, latency_ms=100.0,
        )
        assert result.message == "test"
        assert result.agent_used == "pm"
        assert result.tokens_used == 10
        assert result.latency_ms == 100.0


# ---------------------------------------------------------------------------
# T4: Chat router uses await on run_agent (FR-4)
# ---------------------------------------------------------------------------


def _create_session(auth_client, env=None):
    body = {}
    if env:
        body["user_environment"] = env
    resp = auth_client.post("/sessions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


def _mock_agent_result():
    from app.agents.orchestrator import OrchestratorResult
    return OrchestratorResult(
        message="SDK response works.",
        agent_used="product_manager",
        tokens_used=100,
        latency_ms=150.0,
    )


class TestChatWithAsyncAgent:
    """Chat endpoint works with async run_agent via AsyncMock."""

    @patch("app.routers.chat.run_agent", new_callable=AsyncMock)
    def test_chat_200_with_async_agent(self, mock_run, auth_client):
        """Chat endpoint returns 200 when async run_agent succeeds."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "What does the Petstore API do?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "SDK response works."
        assert data["agent_used"] == "product_manager"

    @patch("app.routers.chat.run_agent", new_callable=AsyncMock)
    def test_chat_records_messages_with_async_agent(self, mock_run, auth_client):
        """Session history updated after async agent call."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "Test message",
        })

        resp = auth_client.get(f"/sessions/{session_id}")
        data = resp.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    @patch("app.routers.chat.run_agent", new_callable=AsyncMock, side_effect=Exception("SDK error"))
    def test_chat_502_on_async_agent_error(self, mock_run, auth_client):
        """Agent error still returns 502 with async run_agent."""
        session_id = _create_session(auth_client)
        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "Hello",
        })
        assert resp.status_code == 502
        assert "Agent processing failed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# T5: SDK integration contract tests
# ---------------------------------------------------------------------------


class TestSDKIntegrationContract:
    """Verify the orchestrator uses SDK patterns correctly."""

    def test_orchestrator_does_not_import_raw_anthropic_client(self):
        """orchestrator.py should NOT directly instantiate anthropic.Anthropic."""
        import inspect
        from app.agents import orchestrator
        source = inspect.getsource(orchestrator)
        assert "anthropic.Anthropic(" not in source, \
            "Orchestrator should use claude_agent_sdk, not raw anthropic.Anthropic"

    def test_orchestrator_imports_sdk(self):
        """orchestrator.py should import from claude_agent_sdk."""
        import inspect
        from app.agents import orchestrator
        source = inspect.getsource(orchestrator)
        assert "claude_agent_sdk" in source, \
            "Orchestrator should import from claude_agent_sdk"

    def test_orchestrator_uses_agent_definitions(self):
        """orchestrator.py should define multiple agents (PM, IM, TDL)."""
        import inspect
        from app.agents import orchestrator
        source = inspect.getsource(orchestrator)
        assert "AgentDefinition" in source, \
            "Orchestrator should use AgentDefinition for sub-agents"

    def test_orchestrator_uses_query_function(self):
        """orchestrator.py should use query() from the SDK."""
        import inspect
        from app.agents import orchestrator
        source = inspect.getsource(orchestrator)
        assert "query(" in source, \
            "Orchestrator should use SDK query() function"
