"""Tests for structured JSON audit logging (MVP-2).

Covers G2.17–G2.18: audit log format and content.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.middleware.logging import JSONFormatter, setup_audit_logging
from tests.conftest import API_KEY


def _create_session(auth_client):
    """Helper: create a session and return its ID."""
    resp = auth_client.post("/sessions", json={})
    assert resp.status_code == 201
    return resp.json()["id"]


def _mock_agent_result():
    from app.agents.orchestrator import OrchestratorResult
    return OrchestratorResult(
        message="The Petstore API lets you manage pets.",
        agent_used="product_manager",
        tokens_used=150,
        latency_ms=200.0,
    )


class TestJSONFormatter:
    """Test the JSON log formatter directly."""

    def test_basic_format(self):
        """Log records are valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "test message"
        assert data["level"] == "INFO"
        assert "timestamp" in data
        assert data["logger"] == "test"

    def test_extra_fields_included(self):
        """Extra fields (session_id, agent_used, etc.) appear in JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="chat_request",
            args=None,
            exc_info=None,
        )
        record.session_id = "abc-123"
        record.agent_used = "product_manager"
        record.tokens_used = 150
        record.latency_ms = 200.5
        record.request_id = "req-456"

        output = formatter.format(record)
        data = json.loads(output)
        assert data["session_id"] == "abc-123"
        assert data["agent_used"] == "product_manager"
        assert data["tokens_used"] == 150
        assert data["latency_ms"] == 200.5
        assert data["request_id"] == "req-456"

    def test_tool_fields_included(self):
        """Tool invocation fields appear in JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="tool_invocation",
            args=None,
            exc_info=None,
        )
        record.tool_name = "read_api_doc"
        record.tool_params = {"api_name": "petstore", "filename": "swagger.md"}

        output = formatter.format(record)
        data = json.loads(output)
        assert data["tool_name"] == "read_api_doc"
        assert data["tool_params"]["api_name"] == "petstore"

    def test_missing_extra_fields_omitted(self):
        """Fields not set on the record are not in the JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="simple log",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "session_id" not in data
        assert "agent_used" not in data
        assert "tool_name" not in data


class TestAuditLogIntegration:
    """G2.17–G2.18: Audit log integration tests with mocked agent."""

    @patch("app.routers.chat.run_agent", new_callable=AsyncMock)
    def test_chat_produces_audit_log(self, mock_run, auth_client, caplog):
        """G2.17: /chat request produces audit log with expected fields."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        with caplog.at_level(logging.INFO):
            resp = auth_client.post("/chat", json={
                "session_id": session_id,
                "message": "What does the Petstore API do?",
            })
        assert resp.status_code == 200

        # Find the chat_request audit log entry
        chat_records = [r for r in caplog.records if r.message == "chat_request"]
        assert len(chat_records) >= 1

        record = chat_records[0]
        assert record.session_id == session_id
        assert record.agent_used == "product_manager"
        assert record.tokens_used == 150
        assert record.latency_ms > 0
        assert record.request_id is not None

    @patch("app.routers.chat.run_agent", new_callable=AsyncMock)
    def test_audit_log_does_not_contain_message(self, mock_run, auth_client, caplog):
        """G2.18: Audit log does NOT contain message content."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        user_message = "Tell me something very specific about petstore XYZ123"

        with caplog.at_level(logging.INFO):
            auth_client.post("/chat", json={
                "session_id": session_id,
                "message": user_message,
            })

        # Check that the user message text is NOT in any log record
        chat_records = [r for r in caplog.records if r.message == "chat_request"]
        for record in chat_records:
            # The formatter would produce JSON — check the formatted output
            formatter = JSONFormatter()
            log_json = formatter.format(record)
            assert user_message not in log_json
            assert "XYZ123" not in log_json
