# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Initialize the web_client submodule (required for /ui to serve)
git submodule update --init --recursive

# Install dependencies (including dev)
uv sync

# Generate self-signed certificate (one-time)
bash scripts/generate_cert.sh

# Run locally (HTTPS)
API_KEYS=test-key MEDIA_ROOT=./files uv run uvicorn app.main:app --reload --ssl-certfile certs/cert.pem --ssl-keyfile certs/key.pem

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
- `app/handlers/list_objects.py` — directory listing with optional `?recursive=true`; filters `.json` sidecar files from results; attaches `ffprobe_response` to file entries when a sidecar exists
- `app/handlers/retrieve_object.py` — file streaming with HTTP Range request support (returns 206 for partial, 416 for invalid ranges)
- `app/storage.py` — path safety (`resolve_safe_path` prevents traversal), MIME detection, chunked file iteration (64 KiB chunks), ffprobe sidecar helpers (`read_ffprobe_sidecar`, `_probe_and_cache`)

All API routes require authentication. The `/objects/{path}` route handles both directories (returns JSON listing) and files (streams binary).

The `web_client/` directory is a git submodule containing a static JS client mounted publicly at `/ui` (no bearer auth — the client prompts for the API key via its own modal).

## ffprobe Sidecar Cache

Directory listings include a `ffprobe_response` field on file entries. The data comes from sidecar JSON files stored alongside media (e.g. `movie.mkv` → `movie.mkv.json`).

- **Startup sweep** (`app/main.py` lifespan): on startup, walks `MEDIA_ROOT` and runs `ffprobe` for any file missing a sidecar. Already-cached files are skipped.
- **Pre-warm script**: `MEDIA_ROOT=./files uv run python scripts/probe_all.py` — run before deploying to generate sidecars without blocking server startup.
- `.json` files are always filtered from all directory listings so sidecars are invisible to API consumers.
- `ffprobe_response` is absent from an entry when ffprobe fails or the file is not a recognised media container.

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
