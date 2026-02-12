"""Tests for MCP tool functions (MVP-2).

Covers functional tool behavior and path-validation security (G2.1–G2.7).
"""

from __future__ import annotations

import logging
import os
import tempfile

import pytest

from app.agents.tools import list_available_apis, read_api_doc, search_api_docs
from app.services.docs_store import DocsStore


@pytest.fixture()
def docs_store(tmp_path):
    """Create a DocsStore backed by a temporary directory with test data."""
    # Create petstore API docs
    petstore = tmp_path / "petstore"
    petstore.mkdir()
    (petstore / "product_brief.md").write_text("# Petstore API\nManage pets in a store.")
    (petstore / "swagger.md").write_text(
        "# Swagger\n## Endpoints\n- GET /pets\n- POST /pets\n"
        "## Authentication\nUse API key header."
    )

    # Create payments API docs
    payments = tmp_path / "payments"
    payments.mkdir()
    (payments / "product_brief.md").write_text("# Payments API\nProcess payments.")
    (payments / "swagger.md").write_text("# Swagger\n## Endpoints\n- POST /charge")

    store = DocsStore(base_dir=str(tmp_path))
    store.scan()
    return store


# ---------------------------------------------------------------------------
# Functional tests (G2.1 – G2.4)
# ---------------------------------------------------------------------------


class TestToolsFunctional:
    """G2.1–G2.4: MCP tools work correctly."""

    def test_list_available_apis(self, docs_store):
        """G2.1: list_available_apis returns indexed API list matching DocsStore."""
        result = list_available_apis(docs_store)
        names = [api["name"] for api in result]
        assert sorted(names) == ["payments", "petstore"]
        for api in result:
            assert "available_docs" in api

    def test_read_api_doc(self, docs_store):
        """G2.2: read_api_doc returns markdown content."""
        content = read_api_doc(docs_store, "petstore", "swagger.md")
        assert "# Swagger" in content
        assert "GET /pets" in content

    def test_read_api_doc_missing_api(self, docs_store):
        """G2.3: read_api_doc returns clear error for missing API."""
        result = read_api_doc(docs_store, "nonexistent", "swagger.md")
        assert "Error" in result
        assert "nonexistent" in result

    def test_search_api_docs(self, docs_store):
        """G2.4: search_api_docs returns matches across APIs."""
        results = search_api_docs(docs_store, "endpoint")
        # "Endpoints" appears in both petstore and payments swagger
        assert len(results) > 0
        api_names = {r["api_name"] for r in results}
        assert "petstore" in api_names or "payments" in api_names
        for r in results:
            assert "api_name" in r
            assert "filename" in r
            assert "line_number" in r
            assert "line" in r


# ---------------------------------------------------------------------------
# Security tests (G2.5 – G2.7)
# ---------------------------------------------------------------------------


class TestToolsSecurity:
    """G2.5–G2.7: Tool path validation and logging."""

    def test_path_traversal_api_name(self, docs_store):
        """G2.5: read_api_doc rejects ../../etc as api_name."""
        result = read_api_doc(docs_store, "../../etc", "passwd")
        assert "Error" in result

    def test_path_traversal_filename(self, docs_store):
        """G2.6: read_api_doc rejects ../../secret as filename."""
        result = read_api_doc(docs_store, "petstore", "../../secret")
        assert "Error" in result

    def test_tool_invocations_are_logged(self, docs_store, caplog):
        """G2.7: Tool invocations are logged with tool_name and params."""
        with caplog.at_level(logging.INFO):
            read_api_doc(docs_store, "petstore", "swagger.md")

        # Check that the tool invocation was logged
        assert any("tool_invocation" in r.message for r in caplog.records)
        tool_records = [r for r in caplog.records if r.message == "tool_invocation"]
        assert len(tool_records) >= 1
        record = tool_records[0]
        assert record.tool_name == "read_api_doc"
        assert record.tool_params == {"api_name": "petstore", "filename": "swagger.md"}

    def test_list_apis_logged(self, docs_store, caplog):
        """Tool invocations for list_available_apis are logged."""
        with caplog.at_level(logging.INFO):
            list_available_apis(docs_store)

        tool_records = [r for r in caplog.records if r.message == "tool_invocation"]
        assert len(tool_records) >= 1
        assert tool_records[0].tool_name == "list_available_apis"

    def test_search_logged(self, docs_store, caplog):
        """Tool invocations for search_api_docs are logged."""
        with caplog.at_level(logging.INFO):
            search_api_docs(docs_store, "test")

        tool_records = [r for r in caplog.records if r.message == "tool_invocation"]
        assert len(tool_records) >= 1
        assert tool_records[0].tool_name == "search_api_docs"
        assert tool_records[0].tool_params == {"query": "test"}
