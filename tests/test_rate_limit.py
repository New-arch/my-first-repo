"""Tests for rate limiting middleware (MVP-2).

Covers G2.14–G2.16: rate limit enforcement on /chat only.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import API_KEY


def _create_session(auth_client):
    """Helper: create a session and return its ID."""
    resp = auth_client.post("/sessions", json={})
    assert resp.status_code == 201
    return resp.json()["id"]


def _mock_agent_result():
    from app.agents.orchestrator import OrchestratorResult
    return OrchestratorResult(
        message="Response",
        agent_used="product_manager",
        tokens_used=50,
        latency_ms=100.0,
    )


class TestRateLimiting:
    """G2.14–G2.16: Rate limiting on /chat."""

    @patch("app.routers.chat.run_agent", new_callable=AsyncMock)
    def test_requests_under_limit_succeed(self, mock_run, auth_client):
        """G2.14: Requests under the rate limit all succeed."""
        mock_run.return_value = _mock_agent_result()
        session_id = _create_session(auth_client)

        # Send a few requests — well under the default limit of 60/min
        for _ in range(3):
            resp = auth_client.post("/chat", json={
                "session_id": session_id,
                "message": "Hello",
            })
            assert resp.status_code == 200

    def test_rate_limit_exceeded(self):
        """G2.15: Exceeding rate limit on /chat returns 429."""
        # Create a test app with a very low rate limit for testing
        from app.main import app
        from app.middleware.rate_limit import RateLimitMiddleware

        # Find and replace the rate limit middleware with a tight one
        # We'll create a fresh client with a custom app that has low limits
        from fastapi import FastAPI
        from starlette.testclient import TestClient as StarletteTestClient

        # Use a standalone approach: test the middleware directly
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse as StarletteJSONResponse
        from starlette.routing import Route

        async def chat_endpoint(request):
            return StarletteJSONResponse({"message": "ok"})

        async def other_endpoint(request):
            return StarletteJSONResponse({"message": "ok"})

        test_app = Starlette(
            routes=[
                Route("/chat", chat_endpoint, methods=["POST"]),
                Route("/apis", other_endpoint, methods=["GET"]),
            ],
        )
        test_app.add_middleware(RateLimitMiddleware, max_requests=3, window_seconds=60)

        client = StarletteTestClient(test_app)

        # First 3 requests should succeed
        for _ in range(3):
            resp = client.post("/chat")
            assert resp.status_code == 200

        # 4th request should be rate-limited
        resp = client.post("/chat")
        assert resp.status_code == 429
        assert "Too many requests" in resp.json()["detail"]

    def test_non_chat_endpoints_not_limited(self):
        """G2.16: Non-chat endpoints are not rate-limited."""
        from app.middleware.rate_limit import RateLimitMiddleware
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse as StarletteJSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient as StarletteTestClient

        async def chat_endpoint(request):
            return StarletteJSONResponse({"message": "ok"})

        async def apis_endpoint(request):
            return StarletteJSONResponse({"message": "ok"})

        test_app = Starlette(
            routes=[
                Route("/chat", chat_endpoint, methods=["POST"]),
                Route("/apis", apis_endpoint, methods=["GET"]),
            ],
        )
        test_app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)

        client = StarletteTestClient(test_app)

        # Exhaust rate limit on /chat
        for _ in range(2):
            client.post("/chat")

        # /chat should now be limited
        resp = client.post("/chat")
        assert resp.status_code == 429

        # But /apis should still work fine
        for _ in range(10):
            resp = client.get("/apis")
            assert resp.status_code == 200
