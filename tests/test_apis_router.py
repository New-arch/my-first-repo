"""MVP-1 Gate tests — /apis endpoint integration tests.

Covers: G1.24–G1.29
"""

from __future__ import annotations

import pytest

from tests.conftest import ADMIN_KEY, API_KEY


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListApis:
    def test_list_apis(self, auth_client):
        """G1.24 — returns both petstore and payments."""
        resp = auth_client.get("/apis")
        assert resp.status_code == 200
        names = [api["name"] for api in resp.json()]
        assert "petstore" in names
        assert "payments" in names

    def test_list_apis_no_auth(self, client):
        """Unauthenticated → 422 (missing header) or 401."""
        resp = client.get("/apis")
        assert resp.status_code in (401, 422)


class TestGetApi:
    def test_get_petstore(self, auth_client):
        """G1.25"""
        resp = auth_client.get("/apis/petstore")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "petstore"
        assert "product_brief.md" in data["available_docs"]
        assert "swagger.md" in data["available_docs"]

    def test_get_nonexistent(self, auth_client):
        """G1.26"""
        resp = auth_client.get("/apis/nonexistent")
        assert resp.status_code == 404

    def test_get_path_traversal(self, auth_client):
        """G1.27 — ../../etc returns 404, not file contents."""
        resp = auth_client.get("/apis/..%2F..%2Fetc")
        assert resp.status_code == 404


class TestRefreshApis:
    def test_refresh_with_admin_key(self, admin_client):
        """G1.28"""
        resp = admin_client.post("/apis/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "refreshed"
        assert data["api_count"] >= 2

    def test_refresh_without_admin_key(self, auth_client):
        """G1.29 — API key alone is not enough for admin endpoints."""
        resp = auth_client.post("/apis/refresh")
        assert resp.status_code in (403, 422)  # 422 if header missing, 403 if wrong

    def test_refresh_no_auth(self, client):
        """Completely unauthenticated."""
        resp = client.post("/apis/refresh")
        assert resp.status_code in (401, 422)
