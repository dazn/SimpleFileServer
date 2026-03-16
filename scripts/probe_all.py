#!/usr/bin/env python3
"""Pre-generate ffprobe sidecar .json files for all media files in MEDIA_ROOT."""
import asyncio
from pathlib import Path

import app.storage as storage


async def main() -> None:
    files = sorted(p for p in storage.MEDIA_ROOT.rglob("*") if p.is_file() and not p.name.endswith(".json"))
    print(f"Probing {len(files)} files in {storage.MEDIA_ROOT}")
    for path in files:
        sidecar = path.parent / (path.name + ".json")
        if sidecar.exists():
            print(f"skip  {path.relative_to(storage.MEDIA_ROOT)}")
            continue
        result = await storage._probe_and_cache(path)
        status = "done" if result is not None else "error"
        print(f"{status}  {path.relative_to(storage.MEDIA_ROOT)}")


asyncio.run(main())
