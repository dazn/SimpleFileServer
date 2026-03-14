from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os

_bearer = HTTPBearer()


def _get_api_keys() -> set[str]:
    raw = os.environ.get("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def verify_token(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> None:
    if credentials.credentials not in _get_api_keys():
        raise HTTPException(status_code=401, detail="Invalid API key")
