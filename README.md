# File Server

A FastAPI-based read-only media file server with bearer token authentication and HTTP range request support.

## Requirements

| Variable | Description |
|---|---|
| `API_KEYS` | Comma-separated list of valid bearer tokens |
| `MEDIA_ROOT` | Host path to the media directory (mapped to `/media` in the container) |

## Running

### Generate a self-signed certificate (one-time)

```bash
bash scripts/generate_cert.sh
```

This creates `certs/cert.pem` and `certs/key.pem`. The `certs/` directory is git-ignored.

### Start the server

```bash
API_KEYS=yourtoken MEDIA_ROOT=/srv/media docker compose up
```

The server listens on port **6567** over **HTTPS**. Since the certificate is self-signed, clients must skip verification (e.g. `curl -k` or `--insecure`).

## Authentication

All endpoints require a bearer token:

```
Authorization: Bearer <token>
```

Tokens are validated against the `API_KEYS` environment variable. Returns `401` on invalid or missing tokens.

## Endpoints

### `GET /info`

Health check.

**Response**
```json
{"message": "hello world"}
```

---

### `GET /objects/{path}`

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

`ffprobe_response` is absent if the file could not be probed (e.g. not a recognised media container). The structure is the verbatim JSON output of `ffprobe -v quiet -print_format json -show_format -show_streams`. See [ffprobe documentation](https://ffmpeg.org/ffprobe.html) for the full schema.

**File headers**

| Header | Description |
|---|---|
| `Range` | Optional. Standard HTTP byte range (e.g. `bytes=0-1023`). Only single ranges are supported. |

**Responses**

| Status | Description |
|---|---|
| `200` | Directory listing (JSON) or full file content with `Accept-Ranges: bytes` and `Content-Length` |
| `206` | Partial file content with `Content-Range` header |
| `404` | Path not found |
| `416` | Range not satisfiable |
