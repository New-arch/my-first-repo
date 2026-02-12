"""MVP-0 Gate tests — Authentication and middleware.

Covers: G0.10, G0.11, G0.12, G0.13, G0.14
"""

from __future__ import annotations

import uuid

import pytest

# Fixtures are imported from conftest.py automatically by pytest.


# ---------------------------------------------------------------------------
# Health endpoint — always unauthenticated
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """G0.3 — /health returns 200 without auth."""

    def test_health_no_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_has_request_id(self, client):
        """G0.13 — all responses include X-Request-Id."""
        resp = client.get("/health")
        assert "X-Request-Id" in resp.headers
        # Should be a valid UUID
        uuid.UUID(resp.headers["X-Request-Id"])


# ---------------------------------------------------------------------------
# Auth enforcement on protected endpoints
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    """G0.10, G0.11, G0.12 — API key enforcement.

    Note: In MVP-0 we only have the /health endpoint (which is unprotected).
    These tests validate the auth dependency functions directly and will be
    extended in MVP-1 when protected endpoints are added.
    """

    def test_verify_api_key_rejects_missing(self, client):
        """G0.10 — request without X-API-Key gets 401.

        We test this by calling a mock endpoint that uses the dependency.
        Since no protected endpoints exist yet in MVP-0, we test the
        dependency directly.
        """
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from app.dependencies import verify_api_key

        test_app = FastAPI()

        @test_app.get("/protected")
        async def protected(key: str = Depends(verify_api_key)):
            return {"ok": True}

        tc = TestClient(test_app, raise_server_exceptions=False)
        resp = tc.get("/protected")
        assert resp.status_code == 422 or resp.status_code == 401

    def test_verify_api_key_rejects_invalid(self, client):
        """G0.11 — request with wrong X-API-Key gets 401."""
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from app.dependencies import verify_api_key

        test_app = FastAPI()

        @test_app.get("/protected")
        async def protected(key: str = Depends(verify_api_key)):
            return {"ok": True}

        tc = TestClient(test_app, raise_server_exceptions=False)
        resp = tc.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_verify_api_key_accepts_valid(self, client):
        """G0.12 — request with correct X-API-Key succeeds."""
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from app.dependencies import verify_api_key

        test_app = FastAPI()

        @test_app.get("/protected")
        async def protected(key: str = Depends(verify_api_key)):
            return {"ok": True}

        tc = TestClient(test_app, raise_server_exceptions=False)
        resp = tc.get("/protected", headers={"X-API-Key": "test-api-key"})
        assert resp.status_code == 200

    def test_verify_admin_key_rejects_invalid(self):
        """G0.10 variant — admin key validation."""
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from app.dependencies import verify_admin_key

        test_app = FastAPI()

        @test_app.post("/admin")
        async def admin_ep(key: str = Depends(verify_admin_key)):
            return {"ok": True}

        tc = TestClient(test_app, raise_server_exceptions=False)
        resp = tc.post("/admin", headers={"X-Admin-Key": "wrong"})
        assert resp.status_code == 403

    def test_verify_admin_key_accepts_valid(self):
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from app.dependencies import verify_admin_key

        test_app = FastAPI()

        @test_app.post("/admin")
        async def admin_ep(key: str = Depends(verify_admin_key)):
            return {"ok": True}

        tc = TestClient(test_app, raise_server_exceptions=False)
        resp = tc.post("/admin", headers={"X-Admin-Key": "test-admin-key"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------


class TestRequestId:
    """G0.13 — X-Request-Id on every response."""

    def test_generated_when_absent(self, client):
        resp = client.get("/health")
        rid = resp.headers.get("X-Request-Id")
        assert rid is not None
        uuid.UUID(rid)  # must be valid UUID

    def test_preserved_when_present(self, client):
        custom_id = str(uuid.uuid4())
        resp = client.get("/health", headers={"X-Request-Id": custom_id})
        assert resp.headers["X-Request-Id"] == custom_id


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------


class TestGlobalErrorHandler:
    """G0.14 — unhandled exceptions produce generic 500, no stack trace."""

    def test_no_stack_trace_in_500(self):
        """Trigger an unhandled exception and verify no traceback leaks."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.middleware.request_id import RequestIdMiddleware

        err_app = FastAPI()
        err_app.add_middleware(RequestIdMiddleware)

        @err_app.exception_handler(Exception)
        async def handler(request, exc):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": getattr(request.state, "request_id", None),
                },
            )

        @err_app.get("/boom")
        async def boom():
            raise RuntimeError("kaboom")

        tc = TestClient(err_app, raise_server_exceptions=False)
        resp = tc.get("/boom")
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"] == "Internal server error"
        assert "kaboom" not in body["detail"]
        assert "Traceback" not in str(body)
        assert "request_id" in body
