"""Docs store — discovers, indexes, and reads API documentation.

Security controls (SEC-1, SEC-6):
- Path canonicalisation via os.path.realpath
- API name validated against indexed registry
- Filename restricted to allowlist
- No symlink following (resolved path must be inside base dir)
- Max file size enforced
- Only one level of subdirectories scanned
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_API_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


@dataclass
class SearchResult:
    """A single search hit across API docs."""

    api_name: str
    filename: str
    line_number: int
    line: str


@dataclass
class DocsStore:
    """Filesystem-backed API documentation store with path safety."""

    base_dir: str = ""
    _index: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.base_dir:
            self.base_dir = settings.marketplace_apis_dir
        # Resolve to absolute path once at init
        self.base_dir = os.path.realpath(self.base_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> None:
        """Scan the base directory and index all API subfolders."""
        self._index.clear()

        if not os.path.isdir(self.base_dir):
            logger.warning("Docs directory does not exist: %s", self.base_dir)
            return

        for entry in sorted(os.listdir(self.base_dir)):
            entry_path = os.path.join(self.base_dir, entry)

            # Only one level deep — skip files, hidden dirs, non-dirs
            if not os.path.isdir(entry_path):
                continue
            if entry.startswith(".") or entry.startswith("_"):
                continue
            if not _API_NAME_RE.match(entry):
                continue

            # Verify resolved path is still inside base_dir (no symlink escape)
            real_path = os.path.realpath(entry_path)
            if not real_path.startswith(self.base_dir + os.sep) and real_path != self.base_dir:
                logger.warning("Skipping symlink escape: %s -> %s", entry, real_path)
                continue

            # Index allowed doc files
            docs = []
            for fname in sorted(os.listdir(entry_path)):
                if fname in settings.allowed_doc_filenames:
                    fpath = os.path.join(entry_path, fname)
                    if os.path.isfile(fpath):
                        docs.append(fname)
            self._index[entry] = docs

        logger.info("Indexed %d APIs: %s", len(self._index), list(self._index.keys()))

    def refresh(self) -> int:
        """Re-scan the docs directory. Returns the new API count."""
        self.scan()
        return len(self._index)

    def list_apis(self) -> List[str]:
        """Return sorted list of indexed API names."""
        return sorted(self._index.keys())

    def get_api_info(self, api_name: str) -> Optional[Dict[str, object]]:
        """Return metadata for a single API, or None if not found."""
        if api_name not in self._index:
            return None
        return {
            "name": api_name,
            "available_docs": self._index[api_name],
        }

    def read_doc(self, api_name: str, filename: str) -> str:
        """Read a doc file content. Raises ValueError on invalid input."""
        # Validate api_name is in the index
        if api_name not in self._index:
            raise ValueError(f"Unknown API: '{api_name}'. Available: {self.list_apis()}")

        # Validate filename is in the allowlist
        if filename not in settings.allowed_doc_filenames:
            raise ValueError(
                f"Filename '{filename}' is not allowed. "
                f"Allowed: {settings.allowed_doc_filenames}"
            )

        # Validate the file exists for this API
        if filename not in self._index[api_name]:
            raise ValueError(
                f"File '{filename}' not found for API '{api_name}'. "
                f"Available: {self._index[api_name]}"
            )

        # Build path and verify it resolves inside base_dir
        file_path = os.path.join(self.base_dir, api_name, filename)
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(self.base_dir + os.sep):
            raise ValueError("Path traversal detected")

        # Check file size
        file_size = os.path.getsize(real_path)
        if file_size > settings.max_doc_file_size_bytes:
            raise ValueError(
                f"File too large ({file_size} bytes). "
                f"Max allowed: {settings.max_doc_file_size_bytes} bytes"
            )

        with open(real_path, "r", encoding="utf-8") as f:
            return f.read()

    def search_docs(self, query: str) -> List[SearchResult]:
        """Search all indexed docs for a keyword/phrase. Case-insensitive."""
        results: List[SearchResult] = []
        query_lower = query.lower()

        for api_name in sorted(self._index.keys()):
            for filename in self._index[api_name]:
                try:
                    content = self.read_doc(api_name, filename)
                except ValueError:
                    continue

                for i, line in enumerate(content.splitlines(), start=1):
                    if query_lower in line.lower():
                        results.append(
                            SearchResult(
                                api_name=api_name,
                                filename=filename,
                                line_number=i,
                                line=line.strip(),
                            )
                        )
        return results
