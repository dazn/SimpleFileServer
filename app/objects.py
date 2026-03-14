from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.auth import verify_token
from app.handlers.list_objects import list_objects
from app.handlers.retrieve_object import retrieve_object
import app.storage as storage

router = APIRouter(prefix="/objects", dependencies=[Depends(verify_token)])


@router.get("/")
async def objects_root_endpoint(recursive: bool = False) -> list[dict[str, Any]]:
    return await list_objects(path="", recursive=recursive)


@router.get("/{path:path}", response_model=None)
async def objects_endpoint(
    path: str, request: Request, recursive: bool = False
) -> list[dict[str, Any]] | StreamingResponse:
    safe = storage.resolve_safe_path(storage.MEDIA_ROOT, path.lstrip("/"))
    if not safe.exists():
        raise HTTPException(status_code=404)
    if safe.is_dir():
        return await list_objects(path=path, recursive=recursive)
    return await retrieve_object(path=path, request=request)
