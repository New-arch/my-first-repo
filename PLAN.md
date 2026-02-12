# FastAPI + Claude Agent SDK — Marketplace API Assistant

## Overview

A FastAPI backend that enables frontend applications to query an AI-powered assistant about marketplace APIs. The system reads API documentation stored as markdown files in per-API subfolders (`marketplace_apis/{api_name}/`) and uses the Claude Agent SDK to orchestrate three specialised agents — Product Manager, Integration Manager, and Technical Dev Lead — to answer user queries.

---

## Architecture

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
│  │  Orchestrator Agent                                │  │
│  │  Analyses intent → delegates to sub-agent(s)       │  │
│  │  max_tokens=4096, timeout=60s per call             │  │
│  │                                                    │  │
│  │  System prompts include:                           │  │
│  │  • Injection resistance instructions               │  │
│  │  • Scope restriction (API docs only)               │  │
│  │  • Secret-in-code prevention                       │  │
│  │  • <user_message> boundary markers                 │  │
│  │                                                    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │  │
│  │  │  Product      │ │ Integration  │ │ Technical  │ │  │
│  │  │  Manager      │ │ Manager      │ │ Dev Lead   │ │  │
│  │  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ │  │
│  │         └────────────────┼───────────────┘        │  │
│  │                          │                        │  │
│  │                    MCP Tools                      │  │
│  │         list_available_apis                       │  │
│  │         read_api_doc  (path-validated)            │  │
│  │         search_api_docs                           │  │
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
            │
            ▼  (read-only, validated paths only)
  marketplace_apis/
  ├── petstore/
  │   ├── product_brief.md
  │   ├── swagger.md
  │   ├── implementation.md
  │   └── error_codes.md
  ├── payments/
  │   ├── product_brief.md
  │   ├── swagger.md
  │   ├── implementation.md
  │   └── error_codes.md
  └── ...
```

---

## Agents

### 1. Product Manager Agent

- **Role**: Understands marketplace APIs from a product/business perspective — what each endpoint does, data models, use cases, limitations, rate limits.
- **System prompt focus**: "You are a Product Manager specialising in API products. Given API documentation, explain what the API does, its capabilities, business value, data models, and typical use cases. Speak in business-friendly language unless told otherwise."
- **Tools**: `list_available_apis`, `read_api_doc`, `search_api_docs` (read-only)

### 2. Integration Manager Agent

- **Role**: Advises on how to integrate marketplace APIs — authentication flows, environment configuration, error handling strategies, integration patterns.
- **System prompt focus**: "You are an Integration Manager. Help users integrate marketplace APIs into their systems. Advise on auth flows, environment setup, networking, error handling strategies, retry/backoff patterns, and integration architecture. Tailor advice to the user's environment."
- **Tools**: `list_available_apis`, `read_api_doc`, `search_api_docs` (read-only)

### 3. Technical Dev Lead Agent

- **Role**: Writes production-quality code — SDK clients, integration layers, typed models — tailored to the user's language, framework, and architecture style (DDD, hexagonal, clean architecture, etc.).
- **System prompt focus**: "You are a Technical Dev Lead. Write production-quality code: SDK clients, integration layers, typed models, error handling, and service abstractions. Adapt to the user's language, framework, and architecture patterns. Include proper error handling mapped to the API's error codes."
- **Tools**: `list_available_apis`, `read_api_doc`, `search_api_docs` (read-only)

### 4. Orchestrator Agent

- **Role**: Top-level agent that analyses user intent and routes to the appropriate sub-agent(s).
- **Routing logic**:
  - Business/product questions → Product Manager
  - Integration/setup/config questions → Integration Manager
  - Code generation/SDK requests → Technical Dev Lead
  - Mixed queries → Multiple agents, synthesised response
- **Response metadata**: Includes `agent_used` indicating which agent(s) contributed

---

## Documentation Folder Structure

Each API lives in its own subfolder under `marketplace_apis/`:

```
marketplace_apis/{api_name}/
├── product_brief.md        # What the API does, business value, use cases
├── swagger.md              # OpenAPI/Swagger spec in markdown
├── implementation.md       # Integration guide, auth flows, env setup
├── error_codes.md          # Error codes, meanings, resolution steps
├── changelog.md            # (optional) Version history
└── examples.md             # (optional) Request/response examples
```

The Docs Store Service scans this directory on startup and exposes it via MCP tools and the `/apis` endpoints.

---

## Project Structure

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
│   │   ├── orchestrator.py     # Main orchestrator + sub-agent defs
│   │   ├── prompts.py          # System prompts (with injection resistance)
│   │   └── tools.py            # Custom MCP tools (path-validated doc lookup)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models (with field validators)
│   └── services/
│       ├── __init__.py
│       ├── docs_store.py       # API doc discovery (path-safe, size-limited)
│       └── session_store.py    # Session storage (TTL, caps, cleanup)
├── marketplace_apis/           # API docs live here (subfolders per API)
│   └── petstore/               # Example API
│       ├── product_brief.md
│       ├── swagger.md
│       ├── implementation.md
│       └── error_codes.md
├── tests/                      # Test suite (see MVP_SPLIT.md)
├── docs/
│   ├── REQUIREMENTS.md         # Feature requirements & UAT definitions
│   ├── MVP_SPLIT.md            # MVP phases & testing gates
│   └── SECURITY_GOVERNANCE.md  # Security review & governance controls
├── requirements.txt            # Pinned dependency versions
├── .env.example
├── .gitignore                  # Includes .env
├── PLAN.md                     # This file
└── README.md
```

---

## Implementation Steps

### Step 1: Project scaffolding
- Create directory structure (`app/`, `app/routers/`, `app/agents/`, `app/models/`, `app/services/`, `app/middleware/`)
- Create `requirements.txt` with pinned versions: `fastapi`, `uvicorn[standard]`, `anthropic`, `pydantic`, `pydantic-settings`, `python-dotenv`
- Create `.env.example` with all config vars (see Config below)
- Create `.gitignore` with `.env`, `__pycache__/`, `.pytest_cache/`
- Create `app/config.py` with settings including security defaults

#### Config variables (`.env.example`)
```
# Required
ANTHROPIC_API_KEY=
APP_API_KEY=                           # API key for endpoint auth
ADMIN_API_KEY=                         # Separate key for admin endpoints

# Security defaults
ENV=development                        # development | production
CORS_ALLOWED_ORIGINS=["*"]             # JSON array; restrict in production
MAX_MESSAGE_LENGTH=10000               # Max chars per chat message
SESSION_TTL_SECONDS=7200               # 2 hours
MAX_SESSIONS=1000
MAX_MESSAGES_PER_SESSION=200
MAX_TOKENS_PER_CALL=4096
SESSION_TOKEN_BUDGET=50000             # Max tokens per session lifetime
CHAT_RATE_LIMIT_PER_MIN=60
MAX_DOC_FILE_SIZE_BYTES=1048576        # 1 MB
MARKETPLACE_APIS_DIR=marketplace_apis
```

### Step 2: Pydantic models (`app/models/schemas.py`)
- `UserEnvironment`: programming_language, framework, architecture_style (enum-validated), description (max 500 chars, tags stripped)
- `SessionCreate`: optional user_environment
- `SessionResponse`: id, created_at, user_environment, messages
- `ChatRequest`: session_id (UUID format), message (max 10k chars validator), api_context (optional, max 10 items)
- `ChatResponse`: session_id, agent_used, message, code_blocks (optional), request_id
- `ApiInfo`: name (regex-validated), available_docs list
- `MessageRecord`: role, content, agent_used, timestamp
- `ErrorResponse`: detail, request_id

### Step 3: Auth & middleware
- `app/dependencies.py` — `verify_api_key()` checks `X-API-Key` against `APP_API_KEY`; `verify_admin_key()` checks against `ADMIN_API_KEY`
- `app/middleware/request_id.py` — generates UUID `X-Request-Id` on every request
- `app/middleware/rate_limit.py` — sliding-window rate limiter for `/chat` endpoint
- `app/middleware/logging.py` — structured JSON audit logger (metadata only, no message content)

### Step 4: Docs store service (`app/services/docs_store.py`)
- Scan `marketplace_apis/` directory for subfolders (one level deep only)
- Index which doc files each API has (`.md` extension only, known filenames only)
- **Security**: path canonicalisation (`os.path.realpath`), no symlinks, max file size check, api_name regex validation
- Provide methods: `list_apis()`, `get_api_info()`, `read_doc()`, `search_docs()`, `refresh()`

### Step 5: Session store service (`app/services/session_store.py`)
- In-memory dict of session_id → session data
- **Security**: UUID4 IDs, TTL-based expiry, max sessions cap, max messages per session, per-session token tracking
- Background cleanup of expired sessions
- Methods: `create_session()`, `get_session()`, `delete_session()`, `add_message()`, `update_environment()`, `track_tokens()`, `cleanup_expired()`

### Step 6: Agent prompts (`app/agents/prompts.py`)
- Detailed system prompts for Product Manager, Integration Manager, Technical Dev Lead
- **Security**: All prompts include injection resistance instructions (FR-11.1–FR-11.7)
- Orchestrator prompt with routing instructions
- Prompt template that wraps user input with `<user_message>` boundary markers
- Template that injects sanitised user environment context
- TDL prompt includes "never include real secrets in generated code"

### Step 7: Custom MCP tools (`app/agents/tools.py`)
- `list_available_apis` — returns all indexed APIs with their doc file inventory
- `read_api_doc` — reads a specific doc file; **validates api_name against index and filename against allowlist**
- `search_api_docs` — searches across all API docs for a keyword/phrase
- All tools log invocations for audit trail

### Step 8: Orchestrator (`app/agents/orchestrator.py`)
- Build orchestrator agent with 3 sub-agents via Claude Agent SDK
- Inject doc context, sanitised user environment, and message history
- **Security**: `max_tokens` per call, 60-second timeout, token usage tracking per session
- Route to appropriate sub-agent based on intent
- Return structured `ChatResponse` with `agent_used` metadata

### Step 9: Routers
- `app/routers/apis.py` — list APIs, get API detail, refresh (admin-only auth)
- `app/routers/sessions.py` — create, get, delete sessions, patch environment
- `app/routers/chat.py` — main chat endpoint with input validation, calls orchestrator, extracts code_blocks, scans for accidental secrets
- All routers use `verify_api_key` dependency

### Step 10: FastAPI app (`app/main.py`)
- Create app with middleware stack (request_id → auth → rate_limit → audit_log → CORS)
- **Security**: env-based CORS config, global exception handler (no stack traces), startup config validation
- Include all routers
- Lifespan: initialise stores, validate required env vars, start session cleanup task

### Step 11: Example API docs
- Create `marketplace_apis/petstore/` with sample product_brief, swagger, implementation, and error_codes markdown files

### Step 12: Verify & push
- Ensure all imports resolve
- Run test suite
- Push to branch `claude/fastapi-claude-agents-Nu2Er`
