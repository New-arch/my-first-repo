# Docker Deployment — Dev WSL2

## Prerequisites

- WSL2 with Ubuntu (22.04+)
- Docker Engine installed in WSL2 **or** Docker Desktop for Windows with WSL2 backend

Check Docker is working:

```bash
docker --version
docker compose version
```

If you need Docker in WSL2 (without Docker Desktop):

```bash
# Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in, then verify:
docker run hello-world
```

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd my-first-repo

# 2. Create your .env
cp .env.example .env
# Edit .env — fill in APP_API_KEY, ADMIN_API_KEY, ANTHROPIC_API_KEY

# 3. Build and run
docker compose up --build
```

The API is now live at `http://localhost:8000`.

---

## Running Modes

### Production-like (no live reload)

```bash
docker compose up --build
```

- Builds the image with code baked in
- Mounts `marketplace_apis/` read-only so you can update docs without rebuilding
- Good for testing a "real" deployment

### Dev mode (live reload on code changes)

```bash
docker compose --profile dev up --build app-dev
```

- Mounts `app/` into the container
- Uvicorn `--reload` watches for changes
- Edit code on your host, container auto-restarts

### Detached (background)

```bash
docker compose up -d --build
# or dev mode:
docker compose --profile dev up -d --build app-dev
```

Check logs:

```bash
docker compose logs -f
```

---

## Verify

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"ok"}

# Swagger UI
# Open http://localhost:8000/docs in your Windows browser

# Check container health status
docker compose ps
# Should show "healthy" after ~35 seconds
```

---

## Useful Commands

| What | Command |
|------|---------|
| Start (foreground) | `docker compose up --build` |
| Start dev mode | `docker compose --profile dev up --build app-dev` |
| Start (background) | `docker compose up -d --build` |
| View logs | `docker compose logs -f` |
| Stop | `docker compose down` |
| Rebuild from scratch | `docker compose build --no-cache` |
| Shell into container | `docker compose exec app bash` |
| Run tests in container | `docker compose run --rm app pytest tests/ -v` |

---

## Environment Variables

All env vars are loaded from your `.env` file via `env_file` in docker-compose. You never bake secrets into the image.

To override a single var at runtime:

```bash
docker compose run --rm -e CHAT_RATE_LIMIT_PER_MIN=10 app
```

See `.env.example` for the full list.

---

## Running Tests in Docker

Tests aren't included in the production image (excluded by `.dockerignore`). To run them, use a temporary container that includes the test files:

```bash
# Option 1: mount tests into the existing image
docker compose run --rm -v ./tests:/app/tests app pytest tests/ -v

# Option 2: build a test image (includes tests)
docker build --target base -t marketplace-test .
docker run --rm -v ./tests:/app/tests -v ./.env:/app/.env marketplace-test pytest tests/ -v
```

---

## Image Details

| Property | Value |
|----------|-------|
| Base image | `python:3.11-slim` |
| Image size | ~180 MB |
| Runs as | `appuser` (non-root) |
| Port | 8000 |
| Healthcheck | `GET /health` every 30s |

---

## Troubleshooting

**"Cannot connect to the Docker daemon"**
```bash
# If using Docker Engine (no Desktop):
sudo service docker start
# Or check Docker Desktop is running
```

**Port 8000 already in use**
```bash
# Find what's using it:
lsof -ti:8000
# Kill it, or change the port in docker-compose.yml:
# ports: - "8001:8000"
```

**Container exits immediately**
```bash
docker compose logs app
# Usually a missing .env file or bad env var
```

**Changes not picked up in dev mode**
- Make sure you're using `--profile dev` with `app-dev`
- Check the volume mount is correct: `docker compose config`

**Can't reach from Windows browser**
- `localhost:8000` should work with Docker Desktop
- If using Docker Engine in WSL2 without Desktop, use the WSL2 IP:
  ```bash
  hostname -I | awk '{print $1}'
  # Use that IP instead of localhost
  ```
