"""MVP-1 Gate tests — SessionStore functional and security tests.

Covers: G1.12–G1.18 (functional), G1.19–G1.23 (security)
"""

from __future__ import annotations

import re
import time

import pytest

from app.models.schemas import MessageRecord, UserEnvironment
from app.services.session_store import SessionStore

UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@pytest.fixture()
def store():
    """Fresh session store with generous limits."""
    return SessionStore(ttl_seconds=3600, max_sessions=100, max_messages_per_session=50)


@pytest.fixture()
def tiny_store():
    """Session store with tight limits for testing caps."""
    return SessionStore(ttl_seconds=1, max_sessions=3, max_messages_per_session=5)


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


class TestSessionStoreFunctional:
    def test_create_session_no_env(self, store):
        """G1.12"""
        session = store.create_session()
        assert UUID4_RE.match(session.id)
        assert session.created_at is not None
        assert session.messages == []
        assert session.user_environment is None

    def test_create_session_with_env(self, store):
        """G1.13"""
        env = UserEnvironment(programming_language="Python", architecture_style="ddd")
        session = store.create_session(user_environment=env)
        assert session.user_environment.programming_language == "Python"

    def test_get_existing_session(self, store):
        """G1.14"""
        session = store.create_session()
        fetched = store.get_session(session.id)
        assert fetched is not None
        assert fetched.id == session.id

    def test_get_missing_session(self, store):
        """G1.15"""
        assert store.get_session("nonexistent-id") is None

    def test_delete_session(self, store):
        """G1.16"""
        session = store.create_session()
        assert store.delete_session(session.id) is True
        assert store.get_session(session.id) is None

    def test_delete_nonexistent_session(self, store):
        """G1.16 — negative case."""
        assert store.delete_session("nonexistent") is False

    def test_add_message(self, store):
        """G1.17"""
        session = store.create_session()
        msg = MessageRecord(role="user", content="Hello")
        store.add_message(session.id, msg)

        fetched = store.get_session(session.id)
        assert len(fetched.messages) == 1
        assert fetched.messages[0].content == "Hello"
        assert fetched.messages[0].timestamp is not None

    def test_add_multiple_messages(self, store):
        """Messages are appended in order."""
        session = store.create_session()
        store.add_message(session.id, MessageRecord(role="user", content="Q1"))
        store.add_message(session.id, MessageRecord(role="assistant", content="A1", agent_used="pm"))
        store.add_message(session.id, MessageRecord(role="user", content="Q2"))

        fetched = store.get_session(session.id)
        assert len(fetched.messages) == 3
        assert [m.role for m in fetched.messages] == ["user", "assistant", "user"]

    def test_add_message_to_missing_session(self, store):
        """add_message to nonexistent session raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            store.add_message("missing", MessageRecord(role="user", content="hi"))

    def test_update_environment(self, store):
        """G1.18"""
        session = store.create_session(
            user_environment=UserEnvironment(programming_language="Python")
        )
        new_env = UserEnvironment(programming_language="Go", architecture_style="hexagonal")
        result = store.update_environment(session.id, new_env)

        assert result is not None
        assert result.user_environment.programming_language == "Go"
        assert result.user_environment.architecture_style.value == "hexagonal"

    def test_update_environment_missing_session(self, store):
        """update_environment on nonexistent session returns None."""
        env = UserEnvironment(programming_language="Rust")
        assert store.update_environment("missing", env) is None


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------


class TestSessionStoreSecurity:
    def test_session_id_is_uuid4(self, store):
        """G1.19"""
        session = store.create_session()
        assert UUID4_RE.match(session.id), f"ID is not UUID4: {session.id}"

    def test_session_expires_after_ttl(self, tiny_store):
        """G1.20"""
        session = tiny_store.create_session()
        assert tiny_store.get_session(session.id) is not None

        time.sleep(1.5)  # TTL is 1 second
        assert tiny_store.get_session(session.id) is None

    def test_max_sessions_cap(self, tiny_store):
        """G1.21"""
        for _ in range(3):
            tiny_store.create_session()

        with pytest.raises(RuntimeError, match="Maximum sessions"):
            tiny_store.create_session()

    def test_max_messages_per_session(self, tiny_store):
        """G1.22"""
        session = tiny_store.create_session()
        for i in range(5):
            tiny_store.add_message(session.id, MessageRecord(role="user", content=f"msg {i}"))

        with pytest.raises(RuntimeError, match="message limit"):
            tiny_store.add_message(session.id, MessageRecord(role="user", content="overflow"))

    def test_cleanup_removes_expired(self, tiny_store):
        """G1.23"""
        s1 = tiny_store.create_session()
        s2 = tiny_store.create_session()
        assert tiny_store.session_count == 2

        time.sleep(1.5)  # TTL is 1 second
        removed = tiny_store.cleanup_expired()
        assert removed == 2
        assert tiny_store.session_count == 0

    def test_token_tracking(self, store):
        """Track cumulative tokens per session."""
        session = store.create_session()
        store.track_tokens(session.id, 100)
        store.track_tokens(session.id, 250)

        fetched = store.get_session(session.id)
        assert fetched.tokens_used == 350
