# FastAPI + Claude Agent SDK — Marketplace API Assistant

## Overview

A FastAPI backend that enables frontend applications to query an AI-powered assistant about marketplace APIs. The system reads API documentation stored as markdown files in per-API subfolders (`marketplace_apis/{api_name}/`) and uses the Claude Agent SDK to orchestrate three specialised agents — Product Manager, Integration Manager, and Technical Dev Lead — to answer user queries.

---

## Architecture

```
Frontend (any SPA / mobile / CLI)
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Application                                     │
│                                                          │
│  GET  /apis                        — list all APIs       │
│  GET  /apis/{api_name}             — single API detail   │
│  POST /apis/refresh                — hot-reload docs     │
│                                                          │
│  POST /sessions                    — create session      │
│  GET  /sessions/{id}               — get session + hist  │
│  DELETE /sessions/{id}             — remove session      │
│  PATCH /sessions/{id}/environment  — update user env     │
│                                                          │
│  POST /chat                        — main chat entry     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Orchestrator Agent                                │  │
│  │  Analyses intent → delegates to sub-agent(s)       │  │
│  │                                                    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │  │
│  │  │  Product      │ │ Integration  │ │ Technical  │ │  │
│  │  │  Manager      │ │ Manager      │ │ Dev Lead   │ │  │
│  │  │              │ │              │ │            │ │  │
│  │  │ Business &   │ │ Auth, config │ │ Code gen,  │ │  │
│  │  │ use cases    │ │ & patterns   │ │ SDK build  │ │  │
│  │  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ │  │
│  │         │                │               │        │  │
│  │         └────────────────┼───────────────┘        │  │
│  │                          │                        │  │
│  │                    MCP Tools                      │  │
│  │         list_available_apis                       │  │
│  │         read_api_doc                              │  │
│  │         search_api_docs                           │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │  Docs Store Service                                │  │
│  │  Scans marketplace_apis/ on startup                │  │
│  │  Indexes folders, reads markdown on demand         │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Session Store Service (in-memory, v1)             │  │
│  │  Sessions, message history, user environment       │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
            │
            ▼
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
│   ├── main.py                 # FastAPI app, CORS, lifespan
│   ├── config.py               # Settings (env vars, defaults)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py             # POST /chat endpoint
│   │   ├── apis.py             # GET /apis, GET /apis/{name}, POST /apis/refresh
│   │   └── sessions.py         # Session CRUD + environment patch
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Main orchestrator + sub-agent defs
│   │   ├── prompts.py          # All system prompts for agents
│   │   └── tools.py            # Custom MCP tools (doc lookup)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── docs_store.py       # API doc discovery & reading
│       └── session_store.py    # Chat session storage
├── marketplace_apis/           # API docs live here (subfolders per API)
│   └── petstore/               # Example API
│       ├── product_brief.md
│       ├── swagger.md
│       ├── implementation.md
│       └── error_codes.md
├── docs/
│   └── REQUIREMENTS.md         # Feature requirements & UAT definitions
├── requirements.txt
├── .env.example
├── PLAN.md                     # This file
└── README.md
```

---

## Implementation Steps

### Step 1: Project scaffolding
- Create directory structure (`app/`, `app/routers/`, `app/agents/`, `app/models/`, `app/services/`)
- Create `requirements.txt` with: `fastapi`, `uvicorn[standard]`, `anthropic`, `pydantic`, `pydantic-settings`, `python-dotenv`
- Create `.env.example` with `ANTHROPIC_API_KEY=`
- Create `app/config.py` with settings

### Step 2: Pydantic models (`app/models/schemas.py`)
- `UserEnvironment`: programming_language, framework, architecture_style, description
- `SessionCreate`: optional user_environment
- `SessionResponse`: id, created_at, user_environment, messages
- `ChatRequest`: session_id, message, api_context (optional list of API names)
- `ChatResponse`: session_id, agent_used, message, code_blocks (optional)
- `ApiInfo`: name, available_docs list
- `ApiListResponse`: list of ApiInfo
- `MessageRecord`: role, content, agent_used, timestamp

### Step 3: Docs store service (`app/services/docs_store.py`)
- Scan `marketplace_apis/` directory for subfolders
- Index which doc files each API has
- Provide methods: `list_apis()`, `get_api_info()`, `read_doc()`, `search_docs()`, `refresh()`

### Step 4: Session store service (`app/services/session_store.py`)
- In-memory dict of session_id → session data
- Methods: `create_session()`, `get_session()`, `delete_session()`, `add_message()`, `update_environment()`

### Step 5: Agent prompts (`app/agents/prompts.py`)
- Detailed system prompts for Product Manager, Integration Manager, Technical Dev Lead
- Orchestrator prompt with routing instructions
- Prompt template that injects user environment context

### Step 6: Custom MCP tools (`app/agents/tools.py`)
- `list_available_apis` — returns all indexed APIs with their doc file inventory
- `read_api_doc` — reads a specific doc file for a given API
- `search_api_docs` — searches across all API docs for a keyword/phrase

### Step 7: Orchestrator (`app/agents/orchestrator.py`)
- Build orchestrator agent with 3 sub-agents via Claude Agent SDK
- Inject doc context, user environment, and message history
- Route to appropriate sub-agent based on intent
- Return structured `ChatResponse` with `agent_used` metadata

### Step 8: Routers
- `app/routers/apis.py` — list APIs, get API detail, refresh
- `app/routers/sessions.py` — create, get, delete sessions, patch environment
- `app/routers/chat.py` — main chat endpoint, calls orchestrator

### Step 9: FastAPI app (`app/main.py`)
- Create app with CORS middleware (allow all origins for dev)
- Include all routers
- Lifespan: initialise docs store, create required dirs

### Step 10: Example API docs
- Create `marketplace_apis/petstore/` with sample product_brief, swagger, implementation, and error_codes markdown files

### Step 11: Verify & push
- Ensure all imports resolve
- Push to branch `claude/fastapi-claude-agents-Nu2Er`
