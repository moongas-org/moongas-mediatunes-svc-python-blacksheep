# pyright: reportUnknownMemberType=false

from pathlib import Path

import pytest
from blacksheep import Application
from blacksheep.server.routing import Router
from blacksheep.testing import TestClient

from app.main.routes import register_routes
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = MediatunesServiceConfig(album_covers_path=str(tmp_path / "covers"))
    config.playback_methods.local.media_path = str(tmp_path / "media")

    def configured_get_config(_app: Application) -> MediatunesServiceConfig:
        return config

    monkeypatch.setattr("app.main.routes.get_config", configured_get_config)
    app = Application(router=Router())
    register_routes(app)
    await app.start()
    yield TestClient(app)
    await app.stop()


@pytest.fixture
def media_file(tmp_path: Path) -> Path:
    path = tmp_path / "media" / "audio.mp3"
    path.parent.mkdir()
    path.write_bytes(bytes(range(256)) * 1024)
    return path


def file_url(path: Path) -> str:
    return "/getfile/" + str(path).lstrip("/")


async def test_full_file(client: TestClient, media_file: Path):
    response = await client.get(file_url(media_file))
    assert response.status == 200
    assert response.get_first_header(b"Accept-Ranges") == b"bytes"
    assert response.get_first_header(b"Content-Length") == b"262144"
    assert response.get_first_header(b"Content-Range") is None
    assert response.get_first_header(b"Content-Type") == b"audio/mpeg"
    assert await response.read() == media_file.read_bytes()


@pytest.mark.parametrize(
    ("range_header", "start", "end"),
    [
        ("bytes=100000-100999", 100000, 100999),
        ("bytes=0-0", 0, 0),
        ("bytes=100000-", 100000, 262143),
        ("bytes=-1000", 261144, 262143),
        ("bytes=262140-999999", 262140, 262143),
        ("bytes=-999999", 0, 262143),
        ("bytes=0-262143", 0, 262143),
        ("Bytes=100000-100999", 100000, 100999),
    ],
)
async def test_byte_range(
    client: TestClient, media_file: Path, range_header: str, start: int, end: int
):
    response = await client.get(file_url(media_file), headers={"Range": range_header})
    assert response.status == 206
    assert response.get_first_header(b"Accept-Ranges") == b"bytes"
    assert response.get_first_header(b"Content-Range") == f"bytes {start}-{end}/262144".encode()
    assert response.get_first_header(b"Content-Length") == str(end - start + 1).encode()
    assert response.get_first_header(b"Content-Type") == b"audio/mpeg"
    assert await response.read() == media_file.read_bytes()[start : end + 1]


@pytest.mark.parametrize("range_header", ["bytes=262144-", "bytes=999999-1000000", "bytes=-0"])
async def test_unsatisfiable_range(client: TestClient, media_file: Path, range_header: str):
    response = await client.get(file_url(media_file), headers={"Range": range_header})
    assert response.status == 416
    assert response.get_first_header(b"Content-Range") == b"bytes */262144"
    assert response.get_first_header(b"Accept-Ranges") == b"bytes"
    assert response.get_first_header(b"Content-Length") == b"0"
    assert not await response.read()


@pytest.mark.parametrize(
    "range_header",
    ["items=0-1", "bytes=bad", "bytes=-", "bytes=20-10", "bytes=0-1,10-11", "bytes=1" + "0" * 5000 + "-"],
)
async def test_ignored_range(client: TestClient, media_file: Path, range_header: str):
    response = await client.get(file_url(media_file), headers={"Range": range_header})
    assert response.status == 200
    assert response.get_first_header(b"Content-Range") is None
    assert await response.read() == media_file.read_bytes()


async def test_if_range_without_matching_validator(client: TestClient, media_file: Path):
    response = await client.get(
        file_url(media_file), headers={"Range": "bytes=0-9", "If-Range": '"old-version"'}
    )
    assert response.status == 200
    assert response.get_first_header(b"Content-Range") is None
    assert await response.read() == media_file.read_bytes()


async def test_head_ignores_range(client: TestClient, media_file: Path):
    response = await client.head(file_url(media_file), headers={"Range": "bytes=0-9"})
    assert response.status == 200
    assert response.get_first_header(b"Accept-Ranges") == b"bytes"
    assert response.get_first_header(b"Content-Length") == b"262144"
    assert response.get_first_header(b"Content-Type") == b"audio/mpeg"
    assert response.get_first_header(b"Content-Range") is None
    assert not await response.read()


@pytest.mark.parametrize("range_header", [None, "bytes=0-0", "bytes=-1"])
async def test_empty_file(client: TestClient, media_file: Path, range_header: str | None):
    media_file.write_bytes(b"")
    headers = {"Range": range_header} if range_header is not None else {}
    response = await client.get(file_url(media_file), headers=headers)
    assert response.status == (200 if range_header is None else 416)
    assert response.get_first_header(b"Content-Length") == b"0"
    assert not await response.read()


async def test_cover_extension_fallback(client: TestClient, tmp_path: Path):
    cover = tmp_path / "covers" / "cover.webp"
    cover.parent.mkdir()
    cover.write_bytes(b"webp content")
    response = await client.get(
        file_url(cover.with_suffix(".jpg")), headers={"Range": "bytes=0-3"}
    )
    assert response.status == 206
    assert response.get_first_header(b"Content-Type") == b"image/webp"
    assert response.get_first_header(b"Content-Range") == b"bytes 0-3/12"
    assert await response.read() == b"webp"


async def test_missing_file(client: TestClient, media_file: Path):
    response = await client.get(file_url(media_file.with_name("missing.mp3")))
    assert response.status == 404


async def test_disallowed_path(client: TestClient, tmp_path: Path):
    path = tmp_path / "outside.mp3"
    path.write_bytes(b"not media")
    response = await client.get(file_url(path), headers={"Range": "bytes=0-3"})
    assert response.status == 404
