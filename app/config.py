"""Application settings loaded from environment variables."""

from __future__ import annotations

import json
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — all values come from env vars or .env file."""

    # --- Required secrets ---
    anthropic_api_key: str = ""
    app_api_key: str = ""
    admin_api_key: str = ""

    # --- Environment ---
    env: str = "development"  # "development" | "production"

    # --- CORS ---
    cors_allowed_origins: List[str] = ["*"]

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v]
        return v

    # --- Input limits ---
    max_message_length: int = 10_000
    max_api_context_items: int = 10

    # --- Session limits ---
    session_ttl_seconds: int = 7200  # 2 hours
    max_sessions: int = 1000
    max_messages_per_session: int = 200

    # --- Agent / cost governance ---
    max_tokens_per_call: int = 4096
    session_token_budget: int = 50_000

    # --- Rate limiting ---
    chat_rate_limit_per_min: int = 60

    # --- Filesystem ---
    marketplace_apis_dir: str = "marketplace_apis"
    max_doc_file_size_bytes: int = 1_048_576  # 1 MB

    # --- Doc filename allowlist ---
    allowed_doc_filenames: List[str] = [
        "product_brief.md",
        "swagger.md",
        "implementation.md",
        "error_codes.md",
        "changelog.md",
        "examples.md",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton — import this wherever config is needed
settings = Settings()
