"""Tests for the /chat endpoint with mocked agent (MVP-2).

Covers G2.8–G2.13: request validation, response shape, session updates.
The agent is mocked so no ANTHROPIC_API_KEY is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import API_KEY


def _create_session(auth_client, env=None):
    """Helper: create a session and return its ID."""
    body = {}
    if env:
        body["user_environment"] = env
    resp = auth_client.post("/sessions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


def _mock_agent_result():
    """Return a mock OrchestratorResult."""
    from app.agents.orchestrator import OrchestratorResult

    return OrchestratorResult(
        message="The Petstore API allows you to manage pets in a store.",
        agent_used="product_manager",
        tokens_used=150,
        latency_ms=200.0,
    )


# ---------------------------------------------------------------------------
# Chat endpoint tests (G2.8 – G2.13)
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    """G2.8–G2.13: /chat endpoint with mocked agent."""

    @patch("app.routers.chat.run_agent")
    def test_valid_chat_request(self, mock_run, auth_client):
        """G2.8: POST /chat with valid session + message returns 200."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "What does the Petstore API do?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["message"] == "The Petstore API allows you to manage pets in a store."

    @patch("app.routers.chat.run_agent")
    def test_invalid_session_id(self, mock_run, auth_client):
        """G2.9: POST /chat with invalid session_id returns 404."""
        resp = auth_client.post("/chat", json={
            "session_id": "00000000-0000-4000-8000-000000000000",
            "message": "Hello",
        })
        assert resp.status_code == 404

    def test_empty_message(self, auth_client):
        """G2.10: POST /chat with empty message returns 422."""
        session_id = _create_session(auth_client)
        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "",
        })
        assert resp.status_code == 422

    def test_message_too_long(self, auth_client):
        """G2.11: POST /chat with message > 10k chars returns 422."""
        session_id = _create_session(auth_client)
        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "x" * 10_001,
        })
        assert resp.status_code == 422

    @patch("app.routers.chat.run_agent")
    def test_response_shape(self, mock_run, auth_client):
        """G2.12: Response has session_id, agent_used, message, request_id."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "What does this API do?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "agent_used" in data
        assert "message" in data
        assert "request_id" in data
        assert data["agent_used"] == "product_manager"
        # request_id should be present
        assert data["request_id"] is not None

    @patch("app.routers.chat.run_agent")
    def test_message_history_updated(self, mock_run, auth_client):
        """G2.13: Session history includes user + assistant messages after chat."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "What does this API do?",
        })

        # Fetch session and check messages
        resp = auth_client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        messages = data["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What does this API do?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["agent_used"] == "product_manager"


class TestChatEdgeCases:
    """Additional edge-case tests for the chat endpoint."""

    @patch("app.routers.chat.run_agent")
    def test_invalid_api_context(self, mock_run, auth_client):
        """Chat with non-existent API in api_context returns 400."""
        session_id = _create_session(auth_client)
        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "Tell me about it",
            "api_context": ["nonexistent_api"],
        })
        assert resp.status_code == 400
        assert "nonexistent_api" in resp.json()["detail"]

    @patch("app.routers.chat.run_agent")
    def test_valid_api_context(self, mock_run, auth_client):
        """Chat with valid api_context proceeds normally."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)
        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "Tell me about petstore",
            "api_context": ["petstore"],
        })
        assert resp.status_code == 200

    @patch("app.routers.chat.run_agent", side_effect=Exception("boom"))
    def test_agent_error_returns_502(self, mock_run, auth_client):
        """Agent SDK exception returns 502, not 500 with stack trace."""
        session_id = _create_session(auth_client)
        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "Hello",
        })
        assert resp.status_code == 502
        data = resp.json()
        assert "Agent processing failed" in data["detail"]
        # Should not contain stack trace
        assert "boom" not in data["detail"]
        assert "Traceback" not in data["detail"]

    def test_no_auth_returns_401(self, client):
        """Chat without API key returns 401."""
        resp = client.post("/chat", json={
            "session_id": "00000000-0000-4000-8000-000000000000",
            "message": "Hello",
        })
        assert resp.status_code in (401, 422)

    @patch("app.routers.chat.run_agent")
    def test_token_budget_exhausted(self, mock_run, auth_client):
        """Chat returns 429 when session token budget is exhausted."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        # Manually exhaust the token budget
        session_store = auth_client.app.state.session_store
        session_store.track_tokens(session_id, 999_999)

        resp = auth_client.post("/chat", json={
            "session_id": session_id,
            "message": "Hello",
        })
        assert resp.status_code == 429
        assert "token budget" in resp.json()["detail"].lower()
