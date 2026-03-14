# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (including dev)
uv sync

# Run locally
API_KEYS=test-key MEDIA_ROOT=./files uv run uvicorn app.main:app --reload

# Run all tests
uv run python -m pytest

# Run a single test file
uv run python -m pytest tests/test_objects.py

# Type check
uv run python -m mypy app/ tests/
```

## Architecture

This is a read-only FastAPI media file server. Authentication uses bearer tokens from a comma-separated `API_KEYS` env var. The `MEDIA_ROOT` env var points to the directory being served.

**Request flow:** `objects.py` (router + route definitions) → `handlers/` (business logic) → `storage.py` (file I/O utilities)

- `app/auth.py` — `HTTPBearer` dependency that validates tokens; used as a FastAPI dependency on all routes
- `app/objects.py` — `APIRouter` with prefix `/objects`; routes delegate to handlers
- `app/handlers/list_objects.py` — directory listing with optional `?recursive=true`
- `app/handlers/retrieve_object.py` — file streaming with HTTP Range request support (returns 206 for partial, 416 for invalid ranges)
- `app/storage.py` — path safety (`resolve_safe_path` prevents traversal), MIME detection, chunked file iteration (64 KiB chunks)

All routes require authentication. The `/objects/{path}` route handles both directories (returns JSON listing) and files (streams binary).

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEYS` | Comma-separated bearer tokens |
| `MEDIA_ROOT` | Absolute path to the media directory being served |

## Docker

```bash
docker compose up  # requires API_KEYS and MEDIA_ROOT env vars set
```

The container serves on port `6567` and mounts `MEDIA_ROOT` as `/media` read-only.
