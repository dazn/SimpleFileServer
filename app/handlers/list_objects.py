from typing import Any

from fastapi import HTTPException

import app.storage as storage


async def list_objects(path: str = "", recursive: bool = False) -> list[dict[str, Any]]:
    safe_path = path.lstrip("/")
    target = storage.resolve_safe_path(storage.MEDIA_ROOT, safe_path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")

    items = sorted(target.rglob("*") if recursive else target.iterdir())
    entries: list[dict[str, Any]] = []
    for item in items:
        if item.name.endswith(".json"):
            continue
        entry = storage._make_entry(item)
        if item.is_file():
            probe = storage.read_ffprobe_sidecar(item)
            if probe is not None:
                entry["ffprobe_response"] = probe
        entries.append(entry)
    return entries
