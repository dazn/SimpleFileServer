from typing import Any

from fastapi import HTTPException

import app.storage as storage


async def list_objects(path: str = "", recursive: bool = False) -> list[dict[str, Any]]:
    safe_path = path.lstrip("/")
    target = storage.resolve_safe_path(storage.MEDIA_ROOT, safe_path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")

    entries: list[dict[str, Any]] = []
    if recursive:
        for item in sorted(target.rglob("*")):
            entries.append(storage._make_entry(item))
    else:
        for item in sorted(target.iterdir()):
            entries.append(storage._make_entry(item))

    return entries
