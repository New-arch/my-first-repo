"""Pydantic request/response models with security validators."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Default comes from config, but models must be independently importable so
# we use a generous hard-cap here; the router layer can apply the tighter
# config-based limit.
_MAX_MESSAGE_LENGTH = 10_000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ArchitectureStyle(str, Enum):
    """Supported architecture styles for code generation."""

    ddd = "ddd"
    hexagonal = "hexagonal"
    clean_architecture = "clean_architecture"
    layered = "layered"
    microservices = "microservices"
    simple = "simple"


# ---------------------------------------------------------------------------
# Embedded models
# ---------------------------------------------------------------------------


class UserEnvironment(BaseModel):
    """Technical environment context for tailoring agent responses."""

    programming_language: Optional[str] = Field(
        None,
        description="Primary programming language (e.g. Python, TypeScript, Java)",
        max_length=50,
    )
    framework: Optional[str] = Field(
        None,
        description="Framework in use (e.g. FastAPI, Express, Spring Boot)",
        max_length=100,
    )
    architecture_style: Optional[ArchitectureStyle] = Field(
        None,
        description="Architecture pattern for generated code",
    )
    description: Optional[str] = Field(
        None,
        description="Free-text description of the user's environment",
        max_length=500,
    )

    @field_validator("description", mode="after")
    @classmethod
    def _strip_html_tags(cls, v: Optional[str]) -> Optional[str]:
        """Strip XML/HTML tags to prevent prompt injection via env context."""
        if v is None:
            return v
        return _HTML_TAG_RE.sub("", v)


class CodeBlock(BaseModel):
    """A fenced code block extracted from an agent response."""

    language: Optional[str] = Field(None, description="Language tag from the fence")
    code: str = Field(..., description="Code content")


class MessageRecord(BaseModel):
    """A single message in a chat session history."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")
    agent_used: Optional[str] = Field(
        None, description="Which agent produced this message"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When this message was recorded"
    )


# ---------------------------------------------------------------------------
# API info
# ---------------------------------------------------------------------------


class ApiInfo(BaseModel):
    """Metadata for a single marketplace API."""

    name: str = Field(..., description="API folder name")
    available_docs: List[str] = Field(
        ..., description="List of doc filenames present for this API"
    )

    @field_validator("name")
    @classmethod
    def _validate_api_name(cls, v: str) -> str:
        if not _API_NAME_RE.match(v):
            raise ValueError(
                "api_name must be alphanumeric (plus _ and -), 1-64 chars, "
                "and must not start with a special character"
            )
        return v


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class SessionCreate(BaseModel):
    """Request body for creating a new chat session."""

    user_environment: Optional[UserEnvironment] = Field(
        None, description="Optional technical environment context"
    )


class SessionResponse(BaseModel):
    """Full session data returned to the client."""

    id: str = Field(..., description="Session UUID")
    created_at: datetime = Field(..., description="Session creation timestamp")
    user_environment: Optional[UserEnvironment] = None
    messages: List[MessageRecord] = Field(
        default_factory=list, description="Ordered message history"
    )


class EnvironmentUpdate(BaseModel):
    """Request body for PATCH /sessions/{id}/environment."""

    user_environment: UserEnvironment


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    session_id: str = Field(..., description="Target session UUID")
    message: str = Field(
        ...,
        min_length=1,
        max_length=_MAX_MESSAGE_LENGTH,
        description="User message (1-10,000 chars)",
    )
    api_context: Optional[List[str]] = Field(
        None,
        description="Restrict agent to these API names only",
        max_length=10,
    )

    @field_validator("session_id")
    @classmethod
    def _validate_uuid(cls, v: str) -> str:
        try:
            UUID(v, version=4)
        except ValueError:
            raise ValueError("session_id must be a valid UUID v4")
        return v

    @field_validator("api_context")
    @classmethod
    def _validate_api_names(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for name in v:
            if not _API_NAME_RE.match(name):
                raise ValueError(
                    f"Invalid api_context entry '{name}': must be alphanumeric "
                    "(plus _ and -), 1-64 chars"
                )
        return v


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    session_id: str = Field(..., description="Session UUID")
    agent_used: str = Field(..., description="Agent that produced the response")
    message: str = Field(..., description="Agent's text response")
    code_blocks: Optional[List[CodeBlock]] = Field(
        None, description="Extracted code blocks (if any)"
    )
    request_id: Optional[str] = Field(
        None, description="Request traceability ID"
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Structured error response."""

    detail: str = Field(..., description="Human-readable error message")
    request_id: Optional[str] = Field(
        None, description="Request traceability ID"
    )
