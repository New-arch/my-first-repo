"""Shared fixtures for the test suite."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Ensure test env vars are set BEFORE importing the app, so that
# app/config.py picks them up via pydantic-settings.
os.environ.setdefault("APP_API_KEY", "test-api-key")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("ENV", "development")

from app.main import app  # noqa: E402 — must come after env setup


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "live: requires ANTHROPIC_API_KEY (deselect with '-m not live')"
    )
    config.addinivalue_line("markers", "security: security-focused tests")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

API_KEY = "test-api-key"
ADMIN_KEY = "test-admin-key"


@pytest.fixture()
def client() -> TestClient:
    """TestClient with no auth headers — for testing 401 scenarios.

    Uses context manager so the lifespan events run (stores are initialised).
    """
    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc


@pytest.fixture()
def auth_client() -> TestClient:
    """TestClient pre-loaded with a valid X-API-Key header."""
    with TestClient(app, headers={"X-API-Key": API_KEY}, raise_server_exceptions=False) as tc:
        yield tc


@pytest.fixture()
def admin_client() -> TestClient:
    """TestClient with both API key and admin key headers."""
    with TestClient(
        app,
        headers={"X-API-Key": API_KEY, "X-Admin-Key": ADMIN_KEY},
        raise_server_exceptions=False,
    ) as tc:
        yield tc
