"""MVP-1 Gate tests — Dedicated path traversal test suite.

Tests various path traversal attack vectors against DocsStore.
"""

from __future__ import annotations

import pytest

from app.services.docs_store import DocsStore


@pytest.fixture()
def store(tmp_path):
    """DocsStore with a minimal API for testing."""
    api_dir = tmp_path / "testapi"
    api_dir.mkdir()
    (api_dir / "product_brief.md").write_text("# Test API")
    (api_dir / "swagger.md").write_text("# Swagger")

    ds = DocsStore(base_dir=str(tmp_path))
    ds.scan()
    return ds


@pytest.mark.security
class TestPathTraversal:
    """Comprehensive path traversal attack vectors."""

    # --- API name attacks ---

    def test_dot_dot_slash(self, store):
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("../etc", "passwd")

    def test_double_dot_dot_slash(self, store):
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("../../etc", "passwd")

    def test_absolute_path(self, store):
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("/etc", "passwd")

    def test_null_byte(self, store):
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("testapi\x00../../etc", "passwd")

    def test_url_encoded_traversal(self, store):
        """Percent-encoded dots and slashes."""
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("%2e%2e/%2e%2e/etc", "passwd")

    def test_backslash_traversal(self, store):
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("..\\..\\etc", "passwd")

    # --- Filename attacks ---

    def test_filename_traversal(self, store):
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("testapi", "../../../etc/passwd")

    def test_filename_absolute(self, store):
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("testapi", "/etc/passwd")

    def test_filename_dot_dot(self, store):
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("testapi", "../../secret.md")

    def test_filename_not_in_allowlist(self, store):
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("testapi", "config.yml")

    def test_filename_md_with_path(self, store):
        """Even if the filename ends in .md, traversal path is rejected."""
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("testapi", "../../other/product_brief.md")

    # --- API name not in index ---

    def test_valid_looking_but_not_indexed(self, store):
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("notindexed", "product_brief.md")

    def test_empty_api_name(self, store):
        with pytest.raises(ValueError, match="Unknown API"):
            store.read_doc("", "product_brief.md")

    def test_empty_filename(self, store):
        with pytest.raises(ValueError, match="not allowed"):
            store.read_doc("testapi", "")

    # --- Allowed combinations work ---

    def test_valid_read_works(self, store):
        content = store.read_doc("testapi", "product_brief.md")
        assert "Test API" in content

    def test_valid_swagger_works(self, store):
        content = store.read_doc("testapi", "swagger.md")
        assert "Swagger" in content
