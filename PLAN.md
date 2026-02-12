# FastAPI + Claude Agent SDK — Marketplace API Assistant

## Overview
A FastAPI backend that a frontend system calls to assist users with marketplace API queries. Uses the Claude Agent SDK to orchestrate three specialized agents that can read, interpret, and act on uploaded Swagger/OpenAPI specification files.

---

## Architecture

```
Frontend (any SPA/mobile)
    │
    ▼
┌──────────────────────────────────────────────┐
│  FastAPI Application                         │
│                                              │
│  POST /chat              — main chat entry   │
│  POST /swagger/upload    — upload specs      │
│  GET  /swagger/list      — list loaded specs │
│  GET  /sessions/{id}     — get session hist. │
│  POST /sessions          — create session    │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Orchestrator Agent (main)             │  │
│  │  Routes queries to the right subagent  │  │
│  │                                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ │  │
│  │  │ Product  │ │Integr.   │ │Tech Dev│ │  │
│  │  │ Manager  │ │Manager   │ │Lead    │ │  │
│  │  └──────────┘ └──────────┘ └────────┘ │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─────────────────────┐                     │
│  │  Swagger Store       │ (in-memory + disk) │
│  │  Parsed specs cache  │                    │
│  └─────────────────────┘                     │
└──────────────────────────────────────────────┘
```

---

## Agents

### 1. Product Manager Agent
- **Role**: Understands the APIs in the marketplace — what each endpoint does, business logic, data models, use cases, limitations.
- **System prompt focus**: "You are a Product Manager specializing in API products. Given Swagger/OpenAPI specs, explain what the API does, its capabilities, business value, data models, and typical use cases. Speak in business-friendly language."
- **Tools**: `Read`, `Glob`, `Grep` (read-only access to swagger files)

### 2. Integration Manager Agent
- **Role**: Understands how to apply the API in the user's environment — authentication setup, environment configuration, deployment patterns, integration architecture.
- **System prompt focus**: "You are an Integration Manager. Help users integrate marketplace APIs into their systems. Advise on auth flows, environment setup, networking, rate limits, error handling strategies, and integration patterns."
- **Tools**: `Read`, `Glob`, `Grep` (read-only access to swagger files)

### 3. Technical Dev Lead Agent
- **Role**: Writes actual code — SDKs, client libraries, integration layers — tailored to the user's programming language, framework, and architecture style (e.g. DDD, hexagonal, clean architecture).
- **System prompt focus**: "You are a Technical Dev Lead. Write production-quality code: SDK clients, integration layers, typed models, and service abstractions. Adapt to the user's language, framework, and architecture patterns (DDD, hexagonal, clean arch, etc.)."
- **Tools**: `Read`, `Glob`, `Grep`, `Write`, `Edit`, `Bash`

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
│   │   ├── swagger.py          # Swagger upload/list endpoints
│   │   └── sessions.py         # Session management endpoints
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Main orchestrator + subagent defs
│   │   ├── prompts.py          # All system prompts for agents
│   │   └── tools.py            # Custom MCP tools (swagger lookup)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── swagger_store.py    # Swagger file storage & parsing
│       └── session_store.py    # Chat session storage
├── swagger_files/              # Uploaded swagger specs land here
├── generated_code/             # Agent-generated code output dir
├── requirements.txt
├── .env.example
└── README.md                   # (existing, will be updated)
```

---

## Implementation Steps

### Step 1: Project scaffolding
- Create directory structure (`app/`, `app/routers/`, `app/agents/`, `app/models/`, `app/services/`)
- Create `requirements.txt` with: `fastapi`, `uvicorn[standard]`, `claude-agent-sdk`, `python-multipart`, `pyyaml`, `python-dotenv`, `pydantic`
- Create `.env.example` with `ANTHROPIC_API_KEY=`
- Create `app/config.py` with settings

### Step 2: Pydantic models (`app/models/schemas.py`)
- `ChatRequest`: session_id, message, context (optional user env info: language, framework, arch style)
- `ChatResponse`: session_id, agent_used, message, code_blocks (optional)
- `SwaggerUploadResponse`: id, filename, summary
- `SwaggerListResponse`: list of loaded specs
- `SessionCreate` / `SessionResponse`
- `UserEnvironment`: programming_language, framework, architecture_style, description

### Step 3: Swagger store service (`app/services/swagger_store.py`)
- Store uploaded swagger JSON/YAML files to `swagger_files/`
- Parse and cache key metadata (title, description, endpoints summary)
- Provide methods: `add_spec()`, `list_specs()`, `get_spec()`, `get_spec_summary()`

### Step 4: Session store service (`app/services/session_store.py`)
- In-memory dict of session_id → message history
- Methods: `create_session()`, `get_session()`, `add_message()`, `list_sessions()`

### Step 5: Agent prompts (`app/agents/prompts.py`)
- Define detailed system prompts for each of the 3 agents
- Define the orchestrator's system prompt that explains when to delegate to which subagent

### Step 6: Custom MCP tools (`app/agents/tools.py`)
- `lookup_swagger` tool — lets agents search/read the loaded swagger specs
- `list_available_apis` tool — lists all uploaded API specs with summaries

### Step 7: Orchestrator (`app/agents/orchestrator.py`)
- Function `run_agent_query()` that:
  1. Builds the orchestrator agent with 3 subagents via `AgentDefinition`
  2. Injects swagger context and user environment into the prompt
  3. Calls `query()` from claude_agent_sdk
  4. Streams/collects the response
  5. Returns structured `ChatResponse`

### Step 8: Routers
- `app/routers/swagger.py` — upload and list swagger files
- `app/routers/sessions.py` — create/get sessions
- `app/routers/chat.py` — main chat endpoint, calls orchestrator

### Step 9: FastAPI app (`app/main.py`)
- Create app with CORS middleware (allow all origins for dev)
- Include all routers
- Lifespan: initialize stores, create `swagger_files/` and `generated_code/` dirs

### Step 10: Verify & commit
- Ensure all imports are correct
- Push to branch `claude/fastapi-claude-agents-Nu2Er`
