from fastapi import Cookie, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import os
from typing import Optional

_bearer = HTTPBearer(auto_error=False)
AUTH_COOKIE_NAME = "media_api_key"


def _get_api_keys() -> set[str]:
    raw = os.environ.get("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
    media_api_key: Optional[str] = Cookie(default=None),
) -> None:
    token = credentials.credentials if credentials else media_api_key
    if not token or token not in _get_api_keys():
        raise HTTPException(status_code=401, detail="Invalid API key")
