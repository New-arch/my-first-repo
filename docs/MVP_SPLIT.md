# MVP Split & Testing Gates

## Marketplace API Assistant — FastAPI + Claude Agent SDK

---

## Philosophy

Each MVP phase is a **shippable increment** that can be tested independently. No phase starts until the previous phase's testing gate passes. Each gate has automated tests (`pytest`) and manual curl checks.

---

## Phase Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  MVP-0: Foundation           ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  Scaffolding, config, models, example docs                      │
│  GATE 0: Server starts, /docs loads, models validate            │
├─────────────────────────────────────────────────────────────────┤
│  MVP-1: Data Layer           ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  Docs store, session store, /apis + /sessions endpoints         │
│  GATE 1: CRUD works, docs indexed, unit tests pass              │
├─────────────────────────────────────────────────────────────────┤
│  MVP-2: Single Agent Chat    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  MCP tools, one agent (PM), /chat endpoint (no routing)         │
│  GATE 2: Chat returns agent response, tools read docs           │
├─────────────────────────────────────────────────────────────────┤
│  MVP-3: All Agents + Orchestrator  ░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  3 sub-agents, orchestrator routing, agent_used metadata        │
│  GATE 3: Routing correct, multi-agent responses, UAT passes     │
├─────────────────────────────────────────────────────────────────┤
│  MVP-4: Polish & Hardening   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  Error handling, multi-turn, code_blocks, environment injection │
│  GATE 4: Full UAT suite passes, edge cases handled              │
└─────────────────────────────────────────────────────────────────┘
```

---

## MVP-0: Foundation

**Goal**: Server boots, Swagger UI loads, Pydantic models validate, example API docs exist.

### Deliverables

| # | File | What |
|---|------|------|
| 0.1 | `requirements.txt` | All dependencies |
| 0.2 | `.env.example` | Environment variable template |
| 0.3 | `app/config.py` | Settings via pydantic-settings |
| 0.4 | `app/models/schemas.py` | All Pydantic models (UserEnvironment, Session*, Chat*, Api*, MessageRecord) |
| 0.5 | `app/main.py` | Minimal FastAPI app with CORS, health endpoint |
| 0.6 | `marketplace_apis/petstore/` | 4 sample markdown docs (product_brief, swagger, implementation, error_codes) |
| 0.7 | `tests/test_models.py` | Unit tests for Pydantic model validation |

### Testing Gate 0

| ID | Test | Type | Pass Criteria |
|----|------|------|--------------|
| G0.1 | `pip install -r requirements.txt` | CLI | Installs without errors |
| G0.2 | `uvicorn app.main:app` | CLI | Server starts on port 8000 |
| G0.3 | `curl http://localhost:8000/health` | curl | Returns `{"status": "ok"}` |
| G0.4 | Browser → `http://localhost:8000/docs` | Manual | Swagger UI loads |
| G0.5 | `pytest tests/test_models.py` | pytest | All model validation tests pass |
| G0.6 | Pydantic models reject invalid input | pytest | `architecture_style="invalid"` raises ValidationError |
| G0.7 | `marketplace_apis/petstore/` has 4 files | CLI | `ls` shows product_brief.md, swagger.md, implementation.md, error_codes.md |

**Exit criteria**: All G0.x pass. No agent logic yet — just a bootable app with validated models.

---

## MVP-1: Data Layer

**Goal**: Docs store scans filesystem, session store manages sessions, CRUD endpoints work.

### Deliverables

| # | File | What |
|---|------|------|
| 1.1 | `app/services/docs_store.py` | DocsStore class — scan, index, read, search, refresh |
| 1.2 | `app/services/session_store.py` | SessionStore class — create, get, delete, add_message, update_environment |
| 1.3 | `app/routers/apis.py` | `GET /apis`, `GET /apis/{name}`, `POST /apis/refresh` |
| 1.4 | `app/routers/sessions.py` | `POST /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}`, `PATCH /sessions/{id}/environment` |
| 1.5 | `app/main.py` (update) | Include routers, lifespan initialises DocsStore |
| 1.6 | `marketplace_apis/payments/` | Second example API (for multi-API testing) |
| 1.7 | `tests/test_docs_store.py` | Unit tests for docs store |
| 1.8 | `tests/test_session_store.py` | Unit tests for session store |
| 1.9 | `tests/test_apis_router.py` | Integration tests for /apis endpoints |
| 1.10 | `tests/test_sessions_router.py` | Integration tests for /sessions endpoints |

### Testing Gate 1

| ID | Test | Type | Pass Criteria |
|----|------|------|--------------|
| **Docs Store** | | | |
| G1.1 | DocsStore scans `marketplace_apis/` | pytest | `list_apis()` returns `["payments", "petstore"]` |
| G1.2 | DocsStore reads a doc | pytest | `read_doc("petstore", "product_brief.md")` returns markdown content |
| G1.3 | DocsStore returns error for missing API | pytest | `get_api_info("nonexistent")` returns None |
| G1.4 | DocsStore search finds keyword | pytest | `search_docs("authentication")` returns matches with API name + file + line |
| G1.5 | DocsStore refresh picks up new folder | pytest | Add folder → `refresh()` → appears in `list_apis()` |
| **Session Store** | | | |
| G1.6 | Create session without env | pytest | Returns session with id, created_at, empty messages |
| G1.7 | Create session with env | pytest | `user_environment` is stored |
| G1.8 | Get existing session | pytest | Returns full session data |
| G1.9 | Get missing session | pytest | Returns None |
| G1.10 | Delete session | pytest | Session gone, subsequent get returns None |
| G1.11 | Add message to session | pytest | Message appended with timestamp |
| G1.12 | Update environment | pytest | Environment replaced, old values gone |
| **API Endpoints** | | | |
| G1.13 | `GET /apis` | curl/pytest | Returns both petstore and payments |
| G1.14 | `GET /apis/petstore` | curl/pytest | Returns petstore with doc file list |
| G1.15 | `GET /apis/nonexistent` | curl/pytest | Returns 404 |
| G1.16 | `POST /apis/refresh` | curl/pytest | Returns updated count |
| G1.17 | `POST /sessions` → `GET /sessions/{id}` | curl/pytest | Round-trip works |
| G1.18 | `DELETE /sessions/{id}` → `GET /sessions/{id}` | curl/pytest | 404 after delete |
| G1.19 | `PATCH /sessions/{id}/environment` | curl/pytest | Environment updated |

**Exit criteria**: All G1.x pass. Full data layer operational. No AI/agent logic yet.

---

## MVP-2: Single Agent Chat

**Goal**: One working agent (Product Manager) answers questions using MCP tools. `/chat` endpoint functional.

### Deliverables

| # | File | What |
|---|------|------|
| 2.1 | `app/agents/tools.py` | MCP tool functions: `list_available_apis`, `read_api_doc`, `search_api_docs` |
| 2.2 | `app/agents/prompts.py` | Product Manager system prompt (other agents as stubs) |
| 2.3 | `app/agents/orchestrator.py` | Simplified orchestrator — routes everything to PM agent (no routing logic yet) |
| 2.4 | `app/routers/chat.py` | `POST /chat` endpoint — validates request, calls orchestrator, returns response |
| 2.5 | `app/main.py` (update) | Include chat router |
| 2.6 | `tests/test_tools.py` | Unit tests for MCP tool functions (no API key needed) |
| 2.7 | `tests/test_chat_router.py` | Integration test for /chat endpoint (mocked agent) |

### Testing Gate 2

| ID | Test | Type | Pass Criteria |
|----|------|------|--------------|
| **MCP Tools** | | | |
| G2.1 | `list_available_apis()` | pytest | Returns indexed API list matching DocsStore |
| G2.2 | `read_api_doc("petstore", "swagger.md")` | pytest | Returns markdown content |
| G2.3 | `read_api_doc("nonexistent", "swagger.md")` | pytest | Returns clear error message |
| G2.4 | `search_api_docs("endpoint")` | pytest | Returns matches across APIs |
| **Chat Endpoint (mocked agent)** | | | |
| G2.5 | `POST /chat` with valid session + message | pytest | Returns 200 with ChatResponse shape |
| G2.6 | `POST /chat` with invalid session_id | pytest | Returns 404 |
| G2.7 | `POST /chat` with empty message | pytest | Returns 422 |
| G2.8 | Response has `session_id`, `agent_used`, `message` fields | pytest | All fields present and typed correctly |
| G2.9 | Message history updated after chat | pytest | `GET /sessions/{id}` shows user + assistant messages |
| **Live Agent Test (requires ANTHROPIC_API_KEY)** | | | |
| G2.10 | Send "What does the Petstore API do?" | curl | PM agent returns business description using doc content |
| G2.11 | Send "What endpoints are available?" | curl | PM agent lists endpoints from swagger.md |
| G2.12 | Agent response references actual doc content | manual | Not hallucinated — matches petstore docs |

**Exit criteria**: All G2.1–G2.9 pass without API key. G2.10–G2.12 pass with API key. Single-agent chat works end-to-end.

---

## MVP-3: All Agents + Orchestrator

**Goal**: All 3 sub-agents operational. Orchestrator routes by intent. `agent_used` metadata correct.

### Deliverables

| # | File | What |
|---|------|------|
| 3.1 | `app/agents/prompts.py` (update) | Full prompts for Integration Manager + Technical Dev Lead |
| 3.2 | `app/agents/orchestrator.py` (update) | Full orchestrator with intent detection and routing to 3 sub-agents |
| 3.3 | `tests/test_orchestrator_routing.py` | Tests that verify routing logic (mocked agents) |

### Testing Gate 3

| ID | Test | Type | Pass Criteria |
|----|------|------|--------------|
| **Routing (mocked)** | | | |
| G3.1 | "What is this API for?" → | pytest | Routed to `product_manager` |
| G3.2 | "How do I authenticate?" → | pytest | Routed to `integration_manager` |
| G3.3 | "Write me a Python SDK client" → | pytest | Routed to `technical_dev_lead` |
| G3.4 | `agent_used` field matches routed agent | pytest | Correct for each test |
| **Live Agent Tests (requires ANTHROPIC_API_KEY)** | | | |
| G3.5 | Business question | curl | `agent_used: "product_manager"`, business-friendly response |
| G3.6 | Integration question | curl | `agent_used: "integration_manager"`, setup/auth advice |
| G3.7 | Code generation request with `user_environment` set | curl | `agent_used: "technical_dev_lead"`, code in correct language |
| G3.8 | Code response includes `code_blocks` | curl | At least one code block extracted |
| G3.9 | Multi-API comparison (api_context: ["petstore", "payments"]) | curl | Response references both APIs |

**Exit criteria**: All G3.1–G3.4 pass without API key. G3.5–G3.9 pass with API key. All three agents respond correctly.

---

## MVP-4: Polish & Hardening

**Goal**: Multi-turn context, environment injection, code_blocks extraction, error hardening, full UAT.

### Deliverables

| # | File | What |
|---|------|------|
| 4.1 | `app/agents/orchestrator.py` (update) | Inject full message history + user environment into agent context |
| 4.2 | `app/routers/chat.py` (update) | Extract code blocks from agent response into `code_blocks` array |
| 4.3 | `app/routers/chat.py` (update) | Structured error handling for agent SDK failures (no 500s) |
| 4.4 | `app/main.py` (update) | Startup check for ANTHROPIC_API_KEY, return 503 on missing config |
| 4.5 | `tests/test_chat_multiturn.py` | Multi-turn conversation tests |
| 4.6 | `tests/test_error_handling.py` | Error edge case tests |
| 4.7 | `tests/test_code_blocks.py` | Code block extraction tests |

### Testing Gate 4

| ID | Test | Type | Pass Criteria |
|----|------|------|--------------|
| **Multi-turn** | | | |
| G4.1 | Send question → follow-up referencing prior answer | curl | Follow-up is context-aware |
| G4.2 | Ask PM question → then ask TDL to code based on PM's answer | curl | TDL builds on prior context |
| G4.3 | `GET /sessions/{id}` after 3 exchanges | curl | 6 messages (3 user + 3 assistant) in order |
| **Environment Injection** | | | |
| G4.4 | Set env to Python+DDD → code request | curl | Python code with DDD patterns |
| G4.5 | `PATCH` env to TypeScript+hexagonal → same request | curl | TypeScript code with ports/adapters |
| **Code Block Extraction** | | | |
| G4.6 | Response with fenced code blocks | pytest | `code_blocks` array has entries with `language` and `code` |
| G4.7 | Response with no code | pytest | `code_blocks` is empty array or null |
| **Error Handling** | | | |
| G4.8 | Chat with non-existent session | pytest | 404, not 500 |
| G4.9 | Chat with non-existent API in api_context | pytest | 400 with available APIs listed |
| G4.10 | No ANTHROPIC_API_KEY set → POST /chat | pytest | 503 with config error message |
| G4.11 | Empty message body | pytest | 422 validation error |
| **Full UAT** | | | |
| G4.12 | Run full UAT suite from REQUIREMENTS.md | manual | All UAT-1 through UAT-9 pass |

**Exit criteria**: All G4.x pass. Full UAT suite from `docs/REQUIREMENTS.md` passes. Production-ready.

---

## Test Infrastructure

### Directory Structure

```
tests/
├── conftest.py                  # Shared fixtures (test client, temp docs dir, stores)
├── test_models.py               # MVP-0: Pydantic model validation
├── test_docs_store.py           # MVP-1: DocsStore unit tests
├── test_session_store.py        # MVP-1: SessionStore unit tests
├── test_apis_router.py          # MVP-1: /apis endpoint integration tests
├── test_sessions_router.py      # MVP-1: /sessions endpoint integration tests
├── test_tools.py                # MVP-2: MCP tool function tests
├── test_chat_router.py          # MVP-2: /chat endpoint (mocked agent)
├── test_orchestrator_routing.py # MVP-3: Routing logic tests
├── test_chat_multiturn.py       # MVP-4: Multi-turn context tests
├── test_error_handling.py       # MVP-4: Error edge cases
└── test_code_blocks.py          # MVP-4: Code block extraction
```

### Running Tests

```bash
# All tests (no API key needed)
pytest tests/ -v

# Single MVP phase
pytest tests/test_models.py -v                    # Gate 0
pytest tests/test_docs_store.py tests/test_session_store.py tests/test_apis_router.py tests/test_sessions_router.py -v  # Gate 1
pytest tests/test_tools.py tests/test_chat_router.py -v  # Gate 2
pytest tests/test_orchestrator_routing.py -v       # Gate 3
pytest tests/test_chat_multiturn.py tests/test_error_handling.py tests/test_code_blocks.py -v  # Gate 4

# Live agent tests (requires ANTHROPIC_API_KEY)
pytest tests/ -v -m "live"
```

### Test Markers

```python
# conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "live: requires ANTHROPIC_API_KEY (deselect with '-m not live')")
```

---

## Dependency Chain

```
MVP-0 ──► MVP-1 ──► MVP-2 ──► MVP-3 ──► MVP-4
models    stores     tools     all agents  polish
config    routers    1 agent   orchestr.   multi-turn
main.py   CRUD       /chat     routing     errors
docs                                       code_blocks
```

No phase can begin until the prior gate passes. Each gate is a **hard stop** — fix failures before proceeding.
