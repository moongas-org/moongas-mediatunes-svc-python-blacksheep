# pyright: reportUnknownMemberType=false
# ^ blacksheep.testing.TestClient stub types (e.g. ClientSession.get) contain Unknown,
#   which strict mode flags at every call site; suppressed file-wide for tests.

from pathlib import Path
import sqlite3

import pytest
from blacksheep import Application
from blacksheep.testing import TestClient

from app import create_app
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.types.config.server_config import ServerConfig


@pytest.fixture()
async def app(tmp_path: Path) -> Application:
    db_file = tmp_path / "api_test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE mediafile (
            id INTEGER PRIMARY KEY,
            path TEXT,
            artistpath TEXT,
            title TEXT,
            artist TEXT,
            albumartist TEXT,
            album TEXT,
            genre TEXT,
            year TEXT
        )
        """)
    conn.execute("""
        CREATE TABLE artist (
            path TEXT PRIMARY KEY,
            name TEXT,
            countrycode TEXT,
            regioncode TEXT,
            city TEXT,
            languagecode TEXT
        )
        """)
    conn.execute(
        "INSERT INTO artist (path, name, countrycode, regioncode, city, languagecode) "
        "VALUES ('/data/Music/A/Artist One', 'Artist One', 'US', 'US-AL', 'Huntsville', 'en')"
    )
    conn.execute(
        "INSERT INTO mediafile (id, path, artistpath, title, artist, albumartist, album, genre, year) "
        "VALUES (1, '/data/Music/A/Artist One/Album [2000]/01 - Track 1.mp3', "
        "'/data/Music/A/Artist One', 'Track 1', 'Artist One', 'Artist One', 'Album', 'Rock', '2000')"
    )
    conn.commit()
    conn.close()

    config = MediatunesServiceConfig(
        mediascan_database_file_path=f"sqlite:///{db_file}",
        # serve the API at /api, matching mediatunes-config.yml
        server_config=ServerConfig(url_prefix="/api"),
    )
    application = create_app(config)
    await application.start()
    return application


async def test_api_config(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/config")
    assert resp.status == 200
    data = await resp.json()
    assert "playbackMethodLocalEnabled" in data
    assert "webSearchPlaybackMethods" in data
    assert "presentYear" in data


async def test_api_tracks(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/tracks")
    assert resp.status == 200
    data = await resp.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["title"] == "Track 1"
    assert data["files"][0]["genre"] == "Rock"


async def test_api_tracks_filtered(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/tracks?genre=Jazz")
    assert resp.status == 200
    data = await resp.json()
    assert len(data["files"]) == 0


async def test_api_albums(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/albums")
    assert resp.status == 200
    data = await resp.json()
    assert len(data["albums"]) == 1
    assert data["albums"][0]["album"] == "Album"
    assert data["albums"][0]["year"] == 2000


async def test_api_artists(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/artists")
    assert resp.status == 200
    data = await resp.json()
    assert data["artists"] == [{"name": "Artist One", "count": 1}]


async def test_api_artist(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/artist?artist=Artist One")
    assert resp.status == 200
    data = await resp.json()
    assert data["artist"]["name"] == "Artist One"
    assert data["artist"]["countryCode"] == "US"


async def test_api_artist_not_found(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/artist?artist=Nobody")
    assert resp.status == 404


async def test_api_genres(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/genres")
    assert resp.status == 200
    data = await resp.json()
    assert data["genres"] == [{"genre": "Rock", "count": 1}]


async def test_api_artist_geo(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/artist-geo/countries")
    assert resp.status == 200
    data = await resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Country"
    assert data["items"][0]["value"] == "United States"
    assert data["items"][0]["criteria"] == {"countryCode": "US"}
    assert data["items"][0]["count"] == 1

    resp = await client.get("/api/artist-geo/cities")
    assert resp.status == 200
    data = await resp.json()
    assert data["items"][0]["value"] == "Huntsville (Alabama, United States)"
    assert data["items"][0]["criteria"]["city"] == "Huntsville"

    resp = await client.get("/api/artist-geo/bogus")
    assert resp.status == 404


async def test_api_wordcloud(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/wordcloud/genres")
    assert resp.status == 200
    assert (await resp.json())["words"] == [{"text": "Rock"}]

    resp = await client.get("/api/wordcloud/artists")
    assert resp.status == 200
    assert (await resp.json())["words"] == [{"text": "Artist One"}]


async def test_api_random_track(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/random-track")
    assert resp.status == 200
    data = await resp.json()
    assert data["title"] == "Track 1"
    assert data["artist"] == "Artist One"
    assert "coverPath" in data

    resp = await client.get("/api/random-track?genre=Jazz")
    assert resp.status == 404
