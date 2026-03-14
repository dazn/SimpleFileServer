from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

import app.storage as storage


async def retrieve_object(path: str, request: Request) -> StreamingResponse:
    target = storage.resolve_safe_path(storage.MEDIA_ROOT, path)

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    file_size = target.stat().st_size
    content_type = storage._guess_content_type(target)
    range_header = request.headers.get("Range")

    if range_header is None:
        return StreamingResponse(
            storage._iter_file(target, 0, file_size - 1),
            status_code=200,
            media_type=content_type,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            },
        )

    if not range_header.startswith("bytes="):
        raise HTTPException(
            status_code=416,
            detail="Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    range_spec = range_header[len("bytes="):]

    if "," in range_spec:
        raise HTTPException(
            status_code=416,
            detail="Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    parts = range_spec.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=416,
            detail="Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    start_str, end_str = parts
    try:
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        raise HTTPException(
            status_code=416,
            detail="Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    if start < 0 or end >= file_size or start > end:
        raise HTTPException(
            status_code=416,
            detail="Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    length = end - start + 1
    return StreamingResponse(
        storage._iter_file(target, start, end),
        status_code=206,
        media_type=content_type,
        headers={
            "Content-Length": str(length),
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
        },
    )
