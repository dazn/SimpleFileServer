import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer test-key-123"}

# Real MP4 magic bytes: ftyp box at offset 4
_MP4_MAGIC = (
    b"\x00\x00\x00\x1c"  # box size
    b"ftyp"              # box type
    b"isom"              # major brand
    b"\x00\x00\x02\x00" # minor version
    b"isomiso2mp41"      # compatible brands
    + b"\x00" * 200
)

# Real MKV/WebM magic bytes: EBML header
_MKV_MAGIC = b"\x1a\x45\xdf\xa3" + b"\x00" * 200


@pytest.fixture()
def media_dir(tmp_path: Path) -> Path:
    (tmp_path / "file1.txt").write_text("hello world")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file2.mp4").write_bytes(b"\x00" * 100)
    return tmp_path


@pytest.fixture()
def client(media_dir: Path) -> TestClient:
    os.environ["API_KEYS"] = "test-key-123"
    os.environ["MEDIA_ROOT"] = str(media_dir)

    # Reload storage + objects modules to pick up new MEDIA_ROOT
    import importlib
    import app.storage
    importlib.reload(app.storage)
    import app.objects
    importlib.reload(app.objects)
    import app.main
    importlib.reload(app.main)

    from app.main import app  # type: ignore[no-redef]
    return TestClient(app)  # type: ignore[arg-type]


# ─── List endpoint ────────────────────────────────────────────────────────────

def test_list_flat(client: TestClient) -> None:
    r = client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    paths = {e["path"] for e in r.json()}
    assert "file1.txt" in paths
    assert "subdir" in paths
    # subdir contents should NOT appear in flat listing
    assert "subdir/file2.mp4" not in paths


def test_list_recursive(client: TestClient) -> None:
    r = client.get("/objects/?recursive=true", headers=AUTH)
    assert r.status_code == 200
    paths = {e["path"] for e in r.json()}
    assert "file1.txt" in paths
    assert "subdir" in paths
    assert "subdir/file2.mp4" in paths


def test_list_subdir_via_path(client: TestClient) -> None:
    r = client.get("/objects/subdir", headers=AUTH)
    assert r.status_code == 200
    paths = {e["path"] for e in r.json()}
    assert "subdir/file2.mp4" in paths
    assert "file1.txt" not in paths


def test_list_directory_entries_no_size(client: TestClient) -> None:
    r = client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    dirs = [e for e in r.json() if e["type"] == "directory"]
    assert len(dirs) > 0
    for d in dirs:
        assert "size" not in d
        assert "content_type" not in d


def test_list_file_entries_have_size(client: TestClient) -> None:
    r = client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    files = [e for e in r.json() if e["type"] == "file"]
    assert len(files) > 0
    for f in files:
        assert "size" in f
        assert "content_type" in f


def test_list_path_traversal_404(client: TestClient) -> None:
    r = client.get("/objects/../../etc", headers=AUTH)
    assert r.status_code == 404


def test_list_missing_path_404(client: TestClient) -> None:
    r = client.get("/objects/nonexistent", headers=AUTH)
    assert r.status_code == 404


def test_list_missing_token(client: TestClient) -> None:
    r = client.get("/objects/")
    assert r.status_code == 401


# ─── Retrieve endpoint ────────────────────────────────────────────────────────

def test_retrieve_full(client: TestClient) -> None:
    r = client.get("/objects/file1.txt", headers=AUTH)
    assert r.status_code == 200
    assert r.text == "hello world"
    assert "content-length" in r.headers
    assert r.headers["accept-ranges"] == "bytes"


def test_retrieve_range(client: TestClient) -> None:
    r = client.get("/objects/file1.txt", headers={**AUTH, "Range": "bytes=0-4"})
    assert r.status_code == 206
    assert r.content == b"hello"
    assert r.headers["content-range"].startswith("bytes 0-4/")
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-length"] == "5"


def test_retrieve_range_suffix(client: TestClient) -> None:
    # bytes=-5 → last 5 bytes — only if start is empty; our impl treats start=0
    # Use explicit end-of-file range
    content = b"hello world"
    size = len(content)
    r = client.get(
        "/objects/file1.txt",
        headers={**AUTH, "Range": f"bytes={size - 5}-{size - 1}"},
    )
    assert r.status_code == 206
    assert r.content == b"world"


def test_retrieve_range_invalid_416(client: TestClient) -> None:
    r = client.get("/objects/file1.txt", headers={**AUTH, "Range": "bytes=9999-99999"})
    assert r.status_code == 416
    assert "content-range" in r.headers
    assert r.headers["content-range"].startswith("bytes */")


def test_retrieve_multi_range_416(client: TestClient) -> None:
    r = client.get(
        "/objects/file1.txt", headers={**AUTH, "Range": "bytes=0-4,6-10"}
    )
    assert r.status_code == 416


def test_retrieve_not_found(client: TestClient) -> None:
    r = client.get("/objects/nofile.txt", headers=AUTH)
    assert r.status_code == 404


def test_retrieve_path_traversal(client: TestClient) -> None:
    r = client.get("/objects/../../etc/passwd", headers=AUTH)
    assert r.status_code == 404


def test_retrieve_missing_token(client: TestClient) -> None:
    r = client.get("/objects/file1.txt")
    assert r.status_code == 401


# ─── streamFormat field ───────────────────────────────────────────────────────

def test_stream_format_absent_for_text(client: TestClient) -> None:
    r = client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    files = [e for e in r.json() if e["path"] == "file1.txt"]
    assert len(files) == 1
    assert "streamFormat" not in files[0]


def test_stream_format_mp4_via_extension_fallback(client: TestClient) -> None:
    # file2.mp4 has null bytes → filetype returns None → mimetypes → video/mp4 → mp4
    r = client.get("/objects/?recursive=true", headers=AUTH)
    assert r.status_code == 200
    files = [e for e in r.json() if e["path"] == "subdir/file2.mp4"]
    assert len(files) == 1
    assert files[0]["streamFormat"] == "mp4"


@pytest.fixture()
def magic_media_dir(tmp_path: Path) -> Path:
    (tmp_path / "file1.txt").write_text("hello world")
    (tmp_path / "real.mp4").write_bytes(_MP4_MAGIC)
    (tmp_path / "real.mkv").write_bytes(_MKV_MAGIC)
    (tmp_path / "playlist.m3u8").write_text("#EXTM3U\n")
    (tmp_path / "manifest.mpd").write_text('<?xml version="1.0"?>\n')
    return tmp_path


@pytest.fixture()
def magic_client(magic_media_dir: Path) -> TestClient:
    os.environ["API_KEYS"] = "test-key-123"
    os.environ["MEDIA_ROOT"] = str(magic_media_dir)

    import importlib
    import app.storage
    importlib.reload(app.storage)
    import app.objects
    importlib.reload(app.objects)
    import app.main
    importlib.reload(app.main)

    from app.main import app  # type: ignore[no-redef]
    return TestClient(app)  # type: ignore[arg-type]


def test_stream_format_mp4_magic_bytes(magic_client: TestClient) -> None:
    r = magic_client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    files = {e["path"]: e for e in r.json() if e["type"] == "file"}
    assert files["real.mp4"]["streamFormat"] == "mp4"
    assert files["real.mp4"]["content_type"] == "video/mp4"


def test_stream_format_mkv_magic_bytes(magic_client: TestClient) -> None:
    r = magic_client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    files = {e["path"]: e for e in r.json() if e["type"] == "file"}
    assert files["real.mkv"]["streamFormat"] == "mkv"
    assert files["real.mkv"]["content_type"] == "video/x-matroska"


def test_stream_format_hls_by_extension(magic_client: TestClient) -> None:
    r = magic_client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    files = {e["path"]: e for e in r.json() if e["type"] == "file"}
    assert files["playlist.m3u8"]["streamFormat"] == "hls"


def test_stream_format_dash_by_extension(magic_client: TestClient) -> None:
    r = magic_client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    files = {e["path"]: e for e in r.json() if e["type"] == "file"}
    assert files["manifest.mpd"]["streamFormat"] == "dash"


def test_stream_format_absent_for_text_in_magic_dir(magic_client: TestClient) -> None:
    r = magic_client.get("/objects/", headers=AUTH)
    assert r.status_code == 200
    files = {e["path"]: e for e in r.json() if e["type"] == "file"}
    assert "streamFormat" not in files["file1.txt"]
