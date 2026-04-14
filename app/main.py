import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

import app.storage as storage
from app.auth import verify_token
from app.objects import router as objects_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    files = [
        p for p in storage.MEDIA_ROOT.rglob("*")
        if p.is_file() and not p.name.endswith(".json")
    ]
    for path in sorted(files):
        sidecar = path.parent / (path.name + ".json")
        if not sidecar.exists():
            try:
                result = await storage._probe_and_cache(path)
            except Exception:
                logger.exception("ffprobe error for %s", path)
                continue
            if result is not None:
                logger.info("created sidecar %s", sidecar)
            else:
                logger.warning("ffprobe returned no data for %s", path)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(objects_router)

_web_client_dir = Path(__file__).parent.parent / "web_client"
if _web_client_dir.is_dir():
    app.mount(
        "/ui",
        StaticFiles(directory=_web_client_dir, html=True),
        name="ui",
    )


@app.get("/info", dependencies=[Depends(verify_token)])
async def info() -> dict[str, str]:
    return {"message": "hello world"}
