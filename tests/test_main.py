import os
import pytest
from fastapi.testclient import TestClient

os.environ["API_KEYS"] = "test-key-123"
os.environ.setdefault("MEDIA_ROOT", "/tmp")

from app.main import app

client = TestClient(app)


def test_info_status() -> None:
    response = client.get("/info", headers={"Authorization": "Bearer test-key-123"})
    assert response.status_code == 200


def test_info_body() -> None:
    response = client.get("/info", headers={"Authorization": "Bearer test-key-123"})
    assert response.json() == {"message": "hello world"}


def test_info_missing_token() -> None:
    response = client.get("/info")
    assert response.status_code == 401


def test_info_invalid_token() -> None:
    response = client.get("/info", headers={"Authorization": "Bearer invalid-key"})
    assert response.status_code == 401
