"""MVP-1 Gate tests — /sessions endpoint integration tests.

Covers: G1.30–G1.32
"""

from __future__ import annotations

import pytest

from tests.conftest import API_KEY


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSessionCRUD:
    def test_create_and_get_session(self, auth_client):
        """G1.30 — POST /sessions → GET /sessions/{id} round-trip."""
        # Create
        resp = auth_client.post("/sessions", json={})
        assert resp.status_code == 201
        data = resp.json()
        session_id = data["id"]
        assert "created_at" in data
        assert data["messages"] == []

        # Get
        resp = auth_client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id

    def test_create_with_environment(self, auth_client):
        """Create session with user environment."""
        resp = auth_client.post(
            "/sessions",
            json={
                "user_environment": {
                    "programming_language": "Python",
                    "framework": "FastAPI",
                    "architecture_style": "ddd",
                    "description": "Our main backend",
                }
            },
        )
        assert resp.status_code == 201
        env = resp.json()["user_environment"]
        assert env["programming_language"] == "Python"
        assert env["architecture_style"] == "ddd"

    def test_get_nonexistent_session(self, auth_client):
        """GET for a non-existent session ID returns 404."""
        resp = auth_client.get("/sessions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_delete_and_verify(self, auth_client):
        """G1.31 — DELETE /sessions/{id} → GET returns 404."""
        resp = auth_client.post("/sessions", json={})
        session_id = resp.json()["id"]

        # Delete
        resp = auth_client.delete(f"/sessions/{session_id}")
        assert resp.status_code == 204

        # Verify gone
        resp = auth_client.get(f"/sessions/{session_id}")
        assert resp.status_code == 404

    def test_delete_nonexistent(self, auth_client):
        resp = auth_client.delete("/sessions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_update_environment(self, auth_client):
        """G1.32 — PATCH /sessions/{id}/environment."""
        resp = auth_client.post("/sessions", json={})
        session_id = resp.json()["id"]

        resp = auth_client.patch(
            f"/sessions/{session_id}/environment",
            json={
                "user_environment": {
                    "programming_language": "TypeScript",
                    "architecture_style": "hexagonal",
                }
            },
        )
        assert resp.status_code == 200
        env = resp.json()["user_environment"]
        assert env["programming_language"] == "TypeScript"
        assert env["architecture_style"] == "hexagonal"

    def test_update_environment_nonexistent(self, auth_client):
        resp = auth_client.patch(
            "/sessions/00000000-0000-0000-0000-000000000000/environment",
            json={"user_environment": {"programming_language": "Go"}},
        )
        assert resp.status_code == 404

    def test_no_auth(self, client):
        """All session endpoints require auth."""
        resp = client.post("/sessions", json={})
        assert resp.status_code in (401, 422)

    def test_environment_html_stripped(self, auth_client):
        """HTML tags in description are stripped by Pydantic."""
        resp = auth_client.post(
            "/sessions",
            json={
                "user_environment": {
                    "description": "<script>alert('xss')</script>Normal text",
                }
            },
        )
        assert resp.status_code == 201
        desc = resp.json()["user_environment"]["description"]
        assert "<script>" not in desc
        assert "Normal text" in desc
