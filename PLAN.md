# FastAPI + Claude Agent SDK — Marketplace API Assistant

## Overview

A FastAPI backend that enables frontend applications to query an AI-powered assistant about marketplace APIs. The system reads API documentation stored as markdown files in per-API subfolders (`marketplace_apis/{api_name}/`) and uses the Claude Agent SDK to orchestrate three specialised agents — Product Manager, Integration Manager, and Technical Dev Lead — to answer user queries.

---

## Migration Plan: Raw Anthropic SDK → Claude Agent SDK

### Problem

The requirements specify "Claude Agent SDK" (`claude-agent-sdk` package) but the current
implementation uses a hand-rolled agent loop on the raw `anthropic==0.42.0` Messages API:
manual tool definitions, manual tool dispatch, manual tool-use loop. None of this leverages
the actual `claude-agent-sdk` package (`pip install claude-agent-sdk`).

### Files Changed

| # | File | Action |
|---|------|--------|
| 1 | `requirements.txt` | Add `claude-agent-sdk>=0.1.35`, remove bare `anthropic` (SDK bundles it) |
| 2 | `Dockerfile` | Add Node.js layer (SDK's bundled CLI needs Node runtime) |
| 3 | `app/agents/tools.py` | Add `@tool()` decorator wrappers + `create_docs_mcp_server()` factory |
| 4 | `app/agents/prompts.py` | Add Integration Manager, Technical Dev Lead, and Orchestrator prompts |
| 5 | `app/agents/orchestrator.py` | Full rewrite: `query()` + `AgentDefinition` + `ResultMessage` tracking |
| 6 | `app/routers/chat.py` | `await run_agent(...)` (it becomes async) |
| 7 | `tests/test_chat_router.py` | Switch `@patch` to `AsyncMock` for async `run_agent` |
| 8 | `tests/test_rate_limit.py` | Same `AsyncMock` update |
| 9 | `tests/test_audit_log.py` | Same `AsyncMock` update |

### Files Unchanged

- `app/config.py`, `app/dependencies.py` — API key loading untouched
- `app/services/docs_store.py`, `app/services/session_store.py` — no changes
- `app/models/schemas.py` — no changes
- `app/routers/apis.py`, `app/routers/sessions.py` — no changes
- `.env.example`, `.dockerignore`, `docker-compose.yml` — no changes
- `tests/test_tools.py` — plain tool functions still tested directly
- `OrchestratorResult` dataclass — same fields, same import path

---

### Step 1: `requirements.txt`

Replace `anthropic==0.42.0` with `claude-agent-sdk>=0.1.35`. The SDK depends on
`anthropic` internally so we don't list both.

```diff
- anthropic==0.42.0
+ claude-agent-sdk>=0.1.35
```

### Step 2: `Dockerfile` — Add Node.js

The SDK bundles the Claude Code CLI which requires a Node.js runtime. Add a Node.js
install step before `pip install`:

```dockerfile
# Node.js 20 (required by claude-agent-sdk's bundled CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
```

Insert between `ENV ...` and `COPY requirements.txt .`. Everything else in the
Dockerfile stays the same.

### Step 3: `app/agents/tools.py` — MCP server factory

Keep existing plain functions (`list_available_apis`, `read_api_doc`, `search_api_docs`)
unchanged — they're tested independently. Add a new factory that wraps them as SDK tools:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

def create_docs_mcp_server(docs_store: DocsStore):
    """Build an in-process MCP server exposing doc tools (FR-9)."""

    @tool("list_available_apis",
          "Return all indexed marketplace APIs with their doc file inventory.",
          {})
    async def list_apis_tool(args):
        _log_tool_call("list_available_apis", {})
        result = list_available_apis(docs_store)
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

    @tool("read_api_doc",
          "Read a specific documentation file for a given API.",
          {"api_name": str, "filename": str})
    async def read_doc_tool(args):
        _log_tool_call("read_api_doc", args)
        content = read_api_doc(docs_store, args["api_name"], args["filename"])
        return {"content": [{"type": "text", "text": content}]}

    @tool("search_api_docs",
          "Search across all API docs for a keyword or phrase.",
          {"query": str})
    async def search_docs_tool(args):
        _log_tool_call("search_api_docs", args)
        results = search_api_docs(docs_store, args["query"])
        return {"content": [{"type": "text", "text": json.dumps(results, default=str)}]}

    return create_sdk_mcp_server(
        name="marketplace-docs",
        version="1.0.0",
        tools=[list_apis_tool, read_doc_tool, search_docs_tool],
    )
```

The `@tool` closures capture `docs_store`, so the MCP server is created at runtime
(during app startup or per-request) with the correct store reference.

### Step 4: `app/agents/prompts.py` — Add missing prompts

The Product Manager prompt already exists. Add three new prompts, each including
the existing `_INJECTION_RESISTANCE` block:

- **`INTEGRATION_MANAGER_PROMPT`** (FR-6): auth flows, env config, error handling,
  retry/backoff, tailored to user environment
- **`TECHNICAL_DEV_LEAD_PROMPT`** (FR-7): production code, typed models, architecture-
  adapted, includes "never include real secrets in generated code" (FR-11.7)
- **`ORCHESTRATOR_PROMPT`** (FR-8): intent analysis, routing rules for which sub-agent
  handles which query type, synthesis of multi-agent responses

Also add a `build_full_prompt()` helper that combines conversation history, user
environment, available APIs, and the current message into a single string for `query()`.

### Step 5: `app/agents/orchestrator.py` — Full SDK rewrite

Replace the entire manual agent loop with the Claude Agent SDK:

```python
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition,
    AssistantMessage, ResultMessage, TextBlock,
)

MCP_TOOLS = [
    "mcp__marketplace-docs__list_available_apis",
    "mcp__marketplace-docs__read_api_doc",
    "mcp__marketplace-docs__search_api_docs",
]

async def run_agent(*, message, session_id, docs_store, session_store,
                    history=None, user_environment=None, api_context=None):
    """Run the orchestrator via Claude Agent SDK."""
    start_time = time.time()

    docs_server = create_docs_mcp_server(docs_store)
    prompt = build_full_prompt(message, history, user_environment, api_context, docs_store)

    options = ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        model="claude-sonnet-4-5-20250929",
        mcp_servers={"marketplace-docs": docs_server},
        allowed_tools=MCP_TOOLS + ["Task"],
        permission_mode="bypassPermissions",
        max_turns=10,
        env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
        agents={
            "product_manager": AgentDefinition(
                description="Answers business/product questions about marketplace APIs",
                prompt=PRODUCT_MANAGER_PROMPT,
                tools=MCP_TOOLS,
            ),
            "integration_manager": AgentDefinition(
                description="Advises on API integration, auth, config, error handling",
                prompt=INTEGRATION_MANAGER_PROMPT,
                tools=MCP_TOOLS,
            ),
            "technical_dev_lead": AgentDefinition(
                description="Writes production-quality code tailored to user's stack",
                prompt=TECHNICAL_DEV_LEAD_PROMPT,
                tools=MCP_TOOLS,
            ),
        },
    )

    # Collect result from async iterator
    final_text = ""
    agent_used = "orchestrator"
    tokens_used = 0

    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    final_text = block.text
                if hasattr(block, "name") and block.name == "Task":
                    agent_used = block.input.get("subagent_type", "orchestrator")
        elif isinstance(msg, ResultMessage):
            usage = msg.usage or {}
            tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    session_store.track_tokens(session_id, tokens_used)
    latency_ms = (time.time() - start_time) * 1000

    return OrchestratorResult(
        message=final_text,
        agent_used=agent_used,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
```

Key changes vs current code:
- `run_agent` becomes **async** (was sync)
- No manual tool dispatch — SDK handles tool-use loop via MCP
- Three sub-agents via `AgentDefinition` (was: single PM agent)
- Token tracking via `ResultMessage` (was: manual accumulation)
- `permission_mode="bypassPermissions"` — automated backend, no interactive prompts

### Step 6: `app/routers/chat.py` — await the async orchestrator

Single line change:

```python
# Before (sync):
result: OrchestratorResult = run_agent(...)

# After (async):
result: OrchestratorResult = await run_agent(...)
```

Everything else in chat.py stays the same — `OrchestratorResult` is unchanged.

### Step 7–9: Test updates (3 files)

All test files that mock `run_agent` need `AsyncMock` since it's now async:

```python
# Before:
from unittest.mock import patch
@patch("app.routers.chat.run_agent")

# After:
from unittest.mock import patch, AsyncMock
@patch("app.routers.chat.run_agent", new_callable=AsyncMock)
```

The `return_value = _mock_agent_result()` pattern stays the same — `AsyncMock`
automatically wraps it in a coroutine. Applies to:
- `tests/test_chat_router.py`
- `tests/test_rate_limit.py`
- `tests/test_audit_log.py`

`tests/test_tools.py` is **unchanged** — the plain tool functions are still tested directly.

---

## Architecture Diagram (after migration)

```
POST /chat
    │
    ▼
chat.py ──await──► orchestrator.run_agent()
                        │
                        ├─ create_docs_mcp_server(docs_store)
                        │    └─ @tool list_available_apis
                        │    └─ @tool read_api_doc
                        │    └─ @tool search_api_docs
                        │
                        ├─ ClaudeAgentOptions(
                        │      system_prompt = ORCHESTRATOR_PROMPT,
                        │      agents = {PM, IM, TDL},
                        │      mcp_servers = {docs_server},
                        │  )
                        │
                        └─ async for msg in query(prompt, options):
                               ├─ AssistantMessage → extract text + agent_used
                               └─ ResultMessage    → extract token usage
```

---

## Notes

- The SDK spawns a Claude Code CLI subprocess per `query()` call. This adds overhead
  vs direct API calls but is acceptable for MVP. Can be revisited for production scale.
- The SDK requires `ANTHROPIC_API_KEY` in the subprocess env. We pass it explicitly
  via `ClaudeAgentOptions.env`.
- Node.js in the Docker image adds ~60-80 MB. Acceptable tradeoff for SDK compliance.
- Conversation history is formatted into the prompt string (the SDK's `query()` takes
  a string, not structured messages). `build_full_prompt()` handles this.

---

## Original Architecture & Project Structure

(Preserved below for reference — the migration does not change the overall architecture,
only how the orchestrator layer is implemented.)

### Architecture

```
Frontend (any SPA / mobile / CLI)
    │
    │  X-API-Key header (required)
    ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Application                                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Middleware Stack                                  │  │
│  │  1. Request ID  (X-Request-Id generation)          │  │
│  │  2. Auth        (X-API-Key / ADMIN_API_KEY verify) │  │
│  │  3. Rate Limit  (token-bucket on /chat)            │  │
│  │  4. Audit Log   (structured JSON, metadata only)   │  │
│  │  5. CORS        (env-based allowed origins)        │  │
│  │  6. Error Guard (no stack traces in responses)     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  GET  /apis                        — list all APIs       │
│  GET  /apis/{api_name}             — single API detail   │
│  POST /apis/refresh                — hot-reload (admin)  │
│                                                          │
│  POST /sessions                    — create session      │
│  GET  /sessions/{id}               — get session + hist  │
│  DELETE /sessions/{id}             — remove session      │
│  PATCH /sessions/{id}/environment  — update user env     │
│                                                          │
│  POST /chat                        — main chat entry     │
│         │  input validation: max 10k chars, session cap  │
│         │  env.description sanitised (tags stripped)      │
│         ▼                                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Orchestrator Agent (Claude Agent SDK)             │  │
│  │  query() + AgentDefinition for 3 sub-agents       │  │
│  │                                                    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │  │
│  │  │  Product      │ │ Integration  │ │ Technical  │ │  │
│  │  │  Manager      │ │ Manager      │ │ Dev Lead   │ │  │
│  │  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ │  │
│  │         └────────────────┼───────────────┘        │  │
│  │                    MCP Tools                      │  │
│  │         @tool list_available_apis                 │  │
│  │         @tool read_api_doc                        │  │
│  │         @tool search_api_docs                     │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │  Docs Store Service                                │  │
│  │  • Scans marketplace_apis/ on startup              │  │
│  │  • Path canonicalisation (realpath inside base)    │  │
│  │  • Filename allowlist (.md only, known names)      │  │
│  │  • No symlink following                            │  │
│  │  • Max file size limit (1 MB)                      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Session Store Service (in-memory, v1)             │  │
│  │  • UUID4 session IDs (cryptographically random)    │  │
│  │  • TTL-based expiry (default 2h)                   │  │
│  │  • Max sessions cap (default 1,000)                │  │
│  │  • Max messages per session (default 200)          │  │
│  │  • Per-session token budget tracking               │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Project Structure

```
my-first-repo/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, CORS, lifespan, global error handler
│   ├── config.py               # Settings (env vars, security defaults)
│   ├── dependencies.py         # Auth dependencies (verify_api_key, verify_admin_key)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py       # X-Request-Id generation
│   │   ├── rate_limit.py       # Token-bucket rate limiter for /chat
│   │   └── logging.py          # Structured JSON audit logging
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py             # POST /chat (input validation, code_blocks scan)
│   │   ├── apis.py             # GET /apis, GET /apis/{name}, POST /apis/refresh
│   │   └── sessions.py         # Session CRUD + environment patch
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # SDK-based orchestrator with AgentDefinition
│   │   ├── prompts.py          # System prompts for all 4 agents
│   │   └── tools.py            # MCP tools via @tool + create_sdk_mcp_server
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models (with field validators)
│   └── services/
│       ├── __init__.py
│       ├── docs_store.py       # API doc discovery (path-safe, size-limited)
│       └── session_store.py    # Session storage (TTL, caps, cleanup)
├── marketplace_apis/           # API docs live here (subfolders per API)
├── tests/                      # Test suite
├── docs/                       # Requirements, MVP split, security governance
├── requirements.txt            # claude-agent-sdk + FastAPI deps
├── Dockerfile                  # Python + Node.js for SDK CLI
├── docker-compose.yml
├── .env.example
├── .gitignore
├── PLAN.md                     # This file
└── README.md
```
