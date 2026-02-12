"""MVP-1 Gate tests — DocsStore functional and security tests.

Covers: G1.1–G1.5 (functional), G1.6–G1.11 (security)
"""

from __future__ import annotations

import os
import tempfile

import pytest

from app.services.docs_store import DocsStore


@pytest.fixture()
def tmp_docs(tmp_path):
    """Create a temp marketplace_apis directory with two APIs."""
    petstore = tmp_path / "petstore"
    petstore.mkdir()
    (petstore / "product_brief.md").write_text("# Petstore\n\nA pet store API.")
    (petstore / "swagger.md").write_text("# Swagger\n\nGET /pet/findByStatus")
    (petstore / "implementation.md").write_text("# Implementation\n\nAuthentication required.")
    (petstore / "error_codes.md").write_text("# Errors\n\n404: Pet not found")

    payments = tmp_path / "payments"
    payments.mkdir()
    (payments / "product_brief.md").write_text("# Payments\n\nPayment processing API.")
    (payments / "swagger.md").write_text("# Swagger\n\nPOST /payment-intents")
    (payments / "implementation.md").write_text("# Implementation\n\nBearer authentication.")
    (payments / "error_codes.md").write_text("# Errors\n\ninsufficient_funds")

    return tmp_path


@pytest.fixture()
def store(tmp_docs):
    """DocsStore backed by temp directory."""
    ds = DocsStore(base_dir=str(tmp_docs))
    ds.scan()
    return ds


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


class TestDocsStoreFunctional:
    def test_list_apis(self, store):
        """G1.1"""
        assert store.list_apis() == ["payments", "petstore"]

    def test_read_doc(self, store):
        """G1.2"""
        content = store.read_doc("petstore", "product_brief.md")
        assert "Petstore" in content
        assert "pet store API" in content

    def test_get_api_info_missing(self, store):
        """G1.3"""
        assert store.get_api_info("nonexistent") is None

    def test_get_api_info_exists(self, store):
        """G1.3 — positive case."""
        info = store.get_api_info("petstore")
        assert info is not None
        assert info["name"] == "petstore"
        assert "product_brief.md" in info["available_docs"]

    def test_search_docs(self, store):
        """G1.4"""
        results = store.search_docs("authentication")
        assert len(results) >= 1
        api_names = {r.api_name for r in results}
        assert "petstore" in api_names or "payments" in api_names

    def test_refresh_picks_up_new_folder(self, store, tmp_docs):
        """G1.5"""
        assert "newapi" not in store.list_apis()

        newapi = tmp_docs / "newapi"
        newapi.mkdir()
        (newapi / "product_brief.md").write_text("# New API")

        store.refresh()
        assert "newapi" in store.list_apis()

    def test_read_doc_missing_file(self, store):
        """read_doc for a valid API but missing doc file raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            store.read_doc("petstore", "changelog.md")


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------


class TestDocsStoreSecurity:
    def test_path_traversal_api_name(self, store):
        """G1.6 — read_doc with ../../etc rejects because not in index."""
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("../../etc", "passwd")

    def test_path_traversal_filename(self, store):
        """G1.7 — read_doc with ../../etc/passwd in filename rejects."""
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("petstore", "../../etc/passwd")

    def test_non_md_file_rejected(self, store, tmp_docs):
        """G1.8 — only .md files in allowlist."""
        # Plant a non-allowed file
        (tmp_docs / "petstore" / "secret.txt").write_text("secret data")
        store.refresh()
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("petstore", "secret.txt")

    def test_symlink_escape(self, tmp_docs):
        """G1.9 — symlink pointing outside base dir is not followed."""
        # Create a symlink from marketplace_apis/evil -> /tmp
        evil_link = tmp_docs / "evil"
        try:
            evil_link.symlink_to("/tmp")
        except OSError:
            pytest.skip("Cannot create symlinks")

        ds = DocsStore(base_dir=str(tmp_docs))
        ds.scan()
        assert "evil" not in ds.list_apis()

    def test_oversized_file_rejected(self, tmp_docs):
        """G1.10 — doc file > max size is refused."""
        from app.config import settings

        (tmp_docs / "petstore" / "swagger.md").write_text("x" * (settings.max_doc_file_size_bytes + 1))

        ds = DocsStore(base_dir=str(tmp_docs))
        ds.scan()
        with pytest.raises(ValueError, match="too large"):
            ds.read_doc("petstore", "swagger.md")

    def test_nested_subdirectory_not_indexed(self, tmp_docs):
        """G1.11 — only one level deep."""
        nested = tmp_docs / "pet" / "store"
        nested.mkdir(parents=True)
        (nested / "product_brief.md").write_text("# Nested")

        ds = DocsStore(base_dir=str(tmp_docs))
        ds.scan()
        # "pet" is indexed (it's a direct child) but "store" inside it is not a top-level API
        assert "store" not in ds.list_apis()

    def test_hidden_dirs_skipped(self, tmp_docs):
        """Directories starting with . or _ are skipped."""
        (tmp_docs / ".hidden").mkdir()
        (tmp_docs / "_private").mkdir()

        ds = DocsStore(base_dir=str(tmp_docs))
        ds.scan()
        assert ".hidden" not in ds.list_apis()
        assert "_private" not in ds.list_apis()

    def test_invalid_api_name_chars_skipped(self, tmp_docs):
        """Directories with invalid chars are skipped during scan."""
        (tmp_docs / "bad name").mkdir()
        ds = DocsStore(base_dir=str(tmp_docs))
        ds.scan()
        assert "bad name" not in ds.list_apis()
