"""Session store — in-memory chat session management with security limits.

Security controls (SEC-4):
- Cryptographically random UUID4 session IDs
- TTL-based auto-expiry
- Global max sessions cap
- Per-session max message cap
- Background cleanup of expired sessions
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.config import settings
from app.models.schemas import MessageRecord, UserEnvironment

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Internal session representation."""

    id: str
    created_at: datetime
    last_active: datetime
    user_environment: Optional[UserEnvironment] = None
    messages: List[MessageRecord] = field(default_factory=list)
    tokens_used: int = 0


class SessionStore:
    """In-memory session store with TTL, caps, and cleanup."""

    def __init__(
        self,
        ttl_seconds: int | None = None,
        max_sessions: int | None = None,
        max_messages_per_session: int | None = None,
    ) -> None:
        self._sessions: Dict[str, SessionData] = {}
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.session_ttl_seconds
        self._max_sessions = max_sessions if max_sessions is not None else settings.max_sessions
        self._max_messages = (
            max_messages_per_session
            if max_messages_per_session is not None
            else settings.max_messages_per_session
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(
        self, user_environment: Optional[UserEnvironment] = None
    ) -> SessionData:
        """Create a new session. Raises RuntimeError if cap exceeded."""
        # Cleanup expired before checking cap
        self.cleanup_expired()

        if len(self._sessions) >= self._max_sessions:
            raise RuntimeError(
                f"Maximum sessions ({self._max_sessions}) reached. "
                "Try again later or delete unused sessions."
            )

        now = datetime.utcnow()
        session = SessionData(
            id=str(uuid.uuid4()),
            created_at=now,
            last_active=now,
            user_environment=user_environment,
        )
        self._sessions[session.id] = session
        logger.info("Session created: %s", session.id)
        return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID. Returns None if not found or expired."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        # Check TTL
        if self._is_expired(session):
            del self._sessions[session_id]
            logger.info("Session expired on access: %s", session_id)
            return None

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Session deleted: %s", session_id)
            return True
        return False

    def add_message(self, session_id: str, message: MessageRecord) -> MessageRecord:
        """Add a message to a session. Raises ValueError/RuntimeError on issues."""
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        if len(session.messages) >= self._max_messages:
            raise RuntimeError(
                f"Session message limit ({self._max_messages}) reached. "
                "Start a new session to continue."
            )

        session.messages.append(message)
        session.last_active = datetime.utcnow()
        return message

    def update_environment(
        self, session_id: str, user_environment: UserEnvironment
    ) -> Optional[SessionData]:
        """Replace the session's user environment. Returns None if not found."""
        session = self.get_session(session_id)
        if session is None:
            return None

        session.user_environment = user_environment
        session.last_active = datetime.utcnow()
        return session

    def track_tokens(self, session_id: str, tokens: int) -> None:
        """Add to cumulative token count for a session."""
        session = self._sessions.get(session_id)
        if session is not None:
            session.tokens_used += tokens

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count removed."""
        expired = [
            sid for sid, s in self._sessions.items() if self._is_expired(s)
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
        return len(expired)

    @property
    def session_count(self) -> int:
        """Current number of active sessions."""
        return len(self._sessions)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_expired(self, session: SessionData) -> bool:
        cutoff = datetime.utcnow() - timedelta(seconds=self._ttl_seconds)
        return session.last_active < cutoff
