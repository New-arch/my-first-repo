"""MCP tool functions for agent access to API documentation.

Each tool wraps the DocsStore with input validation and invocation logging.
Tools are plain functions that receive the DocsStore instance — the orchestrator
is responsible for injecting it.

Security controls:
- Path validation delegated to DocsStore (SEC-1)
- Every invocation is logged with tool_name + parameters (SEC-9 / FR-12.2)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.docs_store import DocsStore

logger = logging.getLogger(__name__)


def _log_tool_call(tool_name: str, params: Dict[str, Any]) -> None:
    """Emit a structured audit log entry for a tool invocation (FR-12.2)."""
    logger.info(
        "tool_invocation",
        extra={"tool_name": tool_name, "tool_params": params},
    )


def list_available_apis(docs_store: DocsStore) -> List[Dict[str, Any]]:
    """Return all indexed APIs with their doc file inventory (FR-9.1).

    Returns a list of dicts: [{"name": "petstore", "available_docs": [...]}]
    """
    _log_tool_call("list_available_apis", {})

    result = []
    for api_name in docs_store.list_apis():
        info = docs_store.get_api_info(api_name)
        if info is not None:
            result.append(info)
    return result


def read_api_doc(docs_store: DocsStore, api_name: str, filename: str) -> str:
    """Read a specific doc file for a given API (FR-9.2).

    Returns the markdown content or an error message string.
    Path validation is handled by DocsStore (SEC-1).
    """
    _log_tool_call("read_api_doc", {"api_name": api_name, "filename": filename})

    try:
        return docs_store.read_doc(api_name, filename)
    except ValueError as e:
        return f"Error: {e}"


def search_api_docs(docs_store: DocsStore, query: str) -> List[Dict[str, Any]]:
    """Search across all API docs for a keyword/phrase (FR-9.3).

    Returns a list of dicts with api_name, filename, line_number, and line.
    """
    _log_tool_call("search_api_docs", {"query": query})

    results = docs_store.search_docs(query)
    return [
        {
            "api_name": r.api_name,
            "filename": r.filename,
            "line_number": r.line_number,
            "line": r.line,
        }
        for r in results
    ]
