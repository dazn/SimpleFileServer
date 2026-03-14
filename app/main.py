from fastapi import Depends, FastAPI
from app.auth import verify_token
from app.objects import router as objects_router

app = FastAPI()
app.include_router(objects_router)


@app.get("/info", dependencies=[Depends(verify_token)])
async def info() -> dict[str, str]:
    return {"message": "hello world"}
