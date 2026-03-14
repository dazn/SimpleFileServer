import mimetypes
import os
from pathlib import Path
from typing import Any

import filetype  # type: ignore[import-untyped]
from fastapi import HTTPException

_media_root_raw = os.environ.get("MEDIA_ROOT", "")
if not _media_root_raw:
    raise RuntimeError("MEDIA_ROOT environment variable is not set")

MEDIA_ROOT = Path(_media_root_raw).resolve()

if not MEDIA_ROOT.is_dir():
    raise RuntimeError(f"MEDIA_ROOT is not a valid directory: {MEDIA_ROOT}")


def resolve_safe_path(base: Path, relative: str) -> Path:
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base):
        raise HTTPException(status_code=404, detail="Not found")
    return resolved


_MIME_TO_STREAM_FORMAT: dict[str, str] = {
    "video/mp4": "mp4",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
    "video/x-matroska": "mkv",
    "audio/x-matroska": "mka",
    "application/vnd.apple.mpegurl": "hls",
    "application/dash+xml": "dash",
}

_EXT_TO_STREAM_FORMAT: dict[str, str] = {
    ".mks": "mks",
    ".m3u8": "hls",
    ".mpd": "dash",
}


def _guess_content_type(path: Path) -> str:
    kind = filetype.guess(path)
    if kind is not None:
        return kind.mime  # type: ignore[no-any-return]
    ct, _ = mimetypes.guess_type(path.name)
    return ct or "application/octet-stream"


def _guess_stream_format(path: Path, content_type: str) -> str | None:
    if content_type in _MIME_TO_STREAM_FORMAT:
        return _MIME_TO_STREAM_FORMAT[content_type]
    return _EXT_TO_STREAM_FORMAT.get(path.suffix.lower())


def _make_entry(path: Path) -> dict[str, Any]:
    rel = path.relative_to(MEDIA_ROOT)
    if path.is_dir():
        return {"path": str(rel), "type": "directory"}
    ct = _guess_content_type(path)
    entry: dict[str, Any] = {
        "path": str(rel),
        "type": "file",
        "size": path.stat().st_size,
        "content_type": ct,
    }
    fmt = _guess_stream_format(path, ct)
    if fmt is not None:
        entry["streamFormat"] = fmt
    return entry


_CHUNK = 1 << 16  # 64 KiB


def _iter_file(path: Path, start: int, end: int) -> Any:
    with path.open("rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(_CHUNK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
