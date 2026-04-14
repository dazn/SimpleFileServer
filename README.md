# File Server

A FastAPI-based read-only media file server with bearer/cookie authentication, HTTP range request support, an ffprobe sidecar cache, and a bundled static web client.

## Requirements

| Variable | Description |
|---|---|
| `API_KEYS` | Comma-separated list of valid API keys |
| `MEDIA_ROOT` | Host path to the media directory (mapped to `/media` in the container) |

`ffmpeg` (which provides `ffprobe`) is required on the host or in the container image. The bundled `Dockerfile` installs it automatically.

## Running

### Clone with submodules

The web client lives in a git submodule and must be initialised before the server can serve `/ui`:

```bash
git submodule update --init --recursive
```

### Generate a self-signed certificate (one-time)

```bash
bash scripts/generate_cert.sh
```

This creates `certs/cert.pem` and `certs/key.pem`. The `certs/` directory is git-ignored.

### Start the server (Docker)

```bash
API_KEYS=yourtoken MEDIA_ROOT=/srv/media docker compose up
```

The server listens on port **6567** over **HTTPS**. Since the certificate is self-signed, clients must skip verification (e.g. `curl -k` or `--insecure`).

### Start the server (local development)

```bash
uv sync
API_KEYS=test-key MEDIA_ROOT=./files uv run uvicorn app.main:app --reload \
  --ssl-certfile certs/cert.pem --ssl-keyfile certs/key.pem
```

### Pre-warm the ffprobe sidecar cache

On startup, the server walks `MEDIA_ROOT` and runs `ffprobe` for any media file missing a sidecar `.json`. For large libraries this can be slow on first boot. Pre-warm the cache ahead of time to avoid blocking startup:

```bash
MEDIA_ROOT=/srv/media uv run python scripts/probe_all.py
```

Already-probed files are skipped.

### Type check and tests

```bash
uv run python -m mypy app/ tests/
uv run python -m pytest
```

## Authentication

All API endpoints require a valid API key supplied one of two ways:

- **Bearer token** (preferred for programmatic clients): `Authorization: Bearer <key>`
- **Cookie** (used by the web client for in-browser media playback, since `<video>` elements cannot send custom headers): `media_api_key=<key>`

Keys are validated against the `API_KEYS` environment variable. Missing or invalid keys return `401`.

## Endpoints

### `GET /info`

Health check. Requires authentication.

**Response**
```json
{"message": "hello world"}
```

---

### `GET /objects/` and `GET /objects/{path}`

Unified endpoint — behaviour depends on whether the path is a directory or a file.

- **Directory** → returns a JSON listing of its contents
- **File** → streams the file content with range request support

**Path traversal is rejected** — requests that resolve outside `MEDIA_ROOT` return `404`.

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `recursive` | bool | `false` | (Directory only) Whether to recurse into subdirectories |

**Directory response** — array of entries:

```json
[
  {"path": "movies", "type": "directory"},
  {
    "path": "movies/film.mkv",
    "type": "file",
    "size": 1234567,
    "content_type": "video/x-matroska",
    "streamFormat": "mkv",
    "ffprobe_response": {
      "streams": [...],
      "format": {...}
    }
  }
]
```

`streamFormat` is only present for recognized streamable formats (`mp4`, `mp3`, `mkv`, `mka`, `mks`, `hls`, `dash`).

`ffprobe_response` is the verbatim JSON output of `ffprobe -v quiet -print_format json -show_format -show_streams`, loaded from a sidecar `<filename>.json` alongside the media file. It is absent if the file could not be probed (e.g. not a recognised media container). See [ffprobe documentation](https://ffmpeg.org/ffprobe.html) for the full schema.

Sidecar `.json` files are filtered from all directory listings and are invisible to API consumers.

**File request headers**

| Header | Description |
|---|---|
| `Range` | Optional. Standard HTTP byte range (e.g. `bytes=0-1023`). Only single ranges are supported. |

**Responses**

| Status | Description |
|---|---|
| `200` | Directory listing (JSON) or full file content with `Accept-Ranges: bytes` and `Content-Length` |
| `206` | Partial file content with `Content-Range` header |
| `401` | Missing or invalid API key |
| `404` | Path not found |
| `416` | Range not satisfiable |

---

### `GET /ui` (web client)

A static JavaScript client served from the `web_client/` submodule. It prompts for an API key on first load, stores it as the `media_api_key` cookie, and uses it for subsequent requests (including `<video>`/`<audio>` playback).

This route is unauthenticated at the HTTP level — the client itself enforces auth by attaching the key to API calls. It is only mounted if the `web_client/` directory is present.
