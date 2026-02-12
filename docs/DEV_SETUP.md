# Dev Setup Guide — WSL2

## Prerequisites

- WSL2 with Ubuntu (22.04+ recommended)
- Python 3.11+
- An Anthropic API key (for live chat — optional for everything else)

Check your Python version:

```bash
python3 --version
```

If you need to install Python 3.11:

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip
```

---

## 1. Clone the repo

```bash
git clone <repo-url>
cd my-first-repo
```

## 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your prompt. Always activate this before working.

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```bash
# Pick any strings you like for these — they're passwords you define
APP_API_KEY=dev-api-key-change-me
ADMIN_API_KEY=dev-admin-key-change-me

# Get this from https://console.anthropic.com → API Keys
# Leave blank if you only want to test non-chat endpoints
ANTHROPIC_API_KEY=sk-ant-...
```

Everything else in `.env` can stay at the defaults.

## 5. Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `--reload` watches for file changes and auto-restarts
- `--host 0.0.0.0` makes it accessible from Windows (via `localhost:8000`)

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

## 6. Verify it's running

```bash
# From another WSL terminal:
curl http://localhost:8000/health
# → {"status":"ok"}
```

Or open `http://localhost:8000/docs` in your Windows browser for the Swagger UI.

## 7. Run the test suite

```bash
pytest tests/ -v
```

All 132 tests should pass. No API key needed for tests — they use mocked values.

---

## Quick reference

| What | Command |
|------|---------|
| Activate venv | `source .venv/bin/activate` |
| Start server | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| Run all tests | `pytest tests/ -v` |
| Run Gate 0 tests | `pytest tests/test_models.py tests/test_auth.py -v` |
| Run Gate 1 tests | `pytest tests/test_docs_store.py tests/test_session_store.py tests/test_path_traversal.py tests/test_apis_router.py tests/test_sessions_router.py -v` |
| Run Gate 2 tests | `pytest tests/test_tools.py tests/test_chat_router.py tests/test_rate_limit.py tests/test_audit_log.py -v` |
| Stop server | `Ctrl+C` |

## Env vars cheat sheet

| Variable | Required | What it does |
|----------|----------|-------------|
| `APP_API_KEY` | Yes | Auth for all endpoints (sent as `X-API-Key` header) |
| `ADMIN_API_KEY` | Yes | Auth for admin endpoints (sent as `X-Admin-Key` header) |
| `ANTHROPIC_API_KEY` | For /chat | Lets the app call Claude for AI responses |
| `ENV` | No | `development` (default) or `production` |
| `CHAT_RATE_LIMIT_PER_MIN` | No | Rate limit on /chat (default: 60) |
| `SESSION_TTL_SECONDS` | No | Session idle timeout (default: 7200 = 2h) |

## Troubleshooting

**"ModuleNotFoundError"** — activate your venv: `source .venv/bin/activate`

**Port 8000 already in use** — kill the old process: `lsof -ti:8000 | xargs kill -9` or use a different port: `--port 8001`

**Can't reach from Windows browser** — make sure you used `--host 0.0.0.0`, not the default `127.0.0.1`

**Tests fail on import** — make sure you `pip install -r requirements.txt` inside the venv
