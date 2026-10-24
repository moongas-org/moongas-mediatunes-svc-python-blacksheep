# pyright: reportUnknownMemberType=false
# ^ blacksheep.testing.TestClient stub types (e.g. ClientSession.get) contain Unknown,
#   which strict mode flags at every call site; suppressed file-wide for tests.

from functools import partial
from pathlib import Path
import sqlite3

import pytest
from blacksheep import Application
from blacksheep.server.routing import Router
from blacksheep.testing import TestClient

from app import create_app
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.types.config.server_config import ServerConfig
from app.utils.app_utils import get_config, get_mediascan_db_files_artists_joined
from app.utils.media_files_utils import MediaFile


@pytest.fixture(autouse=True)
def isolated_router(monkeypatch: pytest.MonkeyPatch) -> None:
    # The default shared router can retain handlers bound to a previous test app.
    monkeypatch.setattr("app.Application", partial(Application, router=Router()))


@pytest.fixture()
def db_file(tmp_path: Path) -> Path:
    db_file = tmp_path / "api_test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE mediafile (
            id INTEGER PRIMARY KEY,
            path TEXT,
            albumpath TEXT,
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
        CREATE TABLE album (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            name TEXT,
            year INTEGER,
            explicitcover BOOLEAN
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
        "INSERT INTO mediafile (id, path, albumpath, artistpath, title, artist, albumartist, album, genre, year) "
        "VALUES (1, '/data/Music/A/Artist One/Album [2000]/01 - Track 1.mp3', "
        "'/data/Music/A/Artist One/Album [2000]', "
        "'/data/Music/A/Artist One', 'Track 1', 'Artist One', 'Artist One', 'Album', 'Rock', '2000')"
    )
    conn.execute(
        "INSERT INTO album (path, name, year, explicitcover) "
        "VALUES ('/data/Music/A/Artist One/Album [2000]', 'Album Metadata Name', 2001, 1)"
    )
    conn.commit()
    conn.close()
    return db_file


@pytest.fixture()
async def app(db_file: Path) -> Application:
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
    assert data["album"]["name"] == "Album Metadata Name"


async def test_api_tracks_filtered(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/tracks?genre=Jazz")
    assert resp.status == 200
    data = await resp.json()
    assert len(data["files"]) == 0
    assert data["album"] is None


SINGLE_ALBUM_JSON: dict[str, object] = {
    "id": 1,
    "path": "/data/Music/A/Artist One/Album [2000]",
    "name": "Album Metadata Name",
    "year": 2001,
    "explicitCover": True,
}
OTHER_ALBUM_JSON: dict[str, object] = {
    "id": 2,
    "path": "/data/Music/A/Artist One/Other [2000]",
    "name": "Album Metadata Name",
    "year": 2001,
    "explicitCover": False,
}


@pytest.mark.parametrize(
    "query, expected_album",
    [
        ("", None),
        ("genre=Jazz", None),
        ("album=Album", SINGLE_ALBUM_JSON),
        ("title=Track%201", SINGLE_ALBUM_JSON),
        ("title=Other", OTHER_ALBUM_JSON),
        ("artist=Missing", None),
    ],
)
async def test_api_tracks_single_album(
    multi_album_app: Application, query: str, expected_album: dict[str, object] | None
):
    response = await TestClient(multi_album_app).get("/api/tracks?" + query)
    assert response.status == 200
    assert (await response.json())["album"] == expected_album


async def test_api_tracks_single_album_without_metadata(db_file: Path):
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE album SET path = '/other/album'")
    application = create_app(
        MediatunesServiceConfig(
            mediascan_database_file_path=f"sqlite:///{db_file}",
            server_config=ServerConfig(url_prefix="/api"),
        )
    )
    await application.start()
    response = await TestClient(application).get("/api/tracks")
    assert response.status == 200
    data = await response.json()
    assert len(data["files"]) == 1
    assert data["album"] is None


async def test_api_tracks_single_album_ignores_max_results(multi_album_app: Application):
    get_config(multi_album_app).max_results = 1
    response = await TestClient(multi_album_app).get("/api/tracks?genre=Jazz")
    assert response.status == 200
    data = await response.json()
    assert len(data["files"]) == 1
    assert data["album"] is None


@pytest.mark.parametrize("limit", [1, 2, 3, 4, 0, -1])
@pytest.mark.parametrize(
    "query, matching_count",
    [
        ("", 3),
        ("sort=year", 3),
        ("artist=Artist%20One", 2),
        ("album=Album", 2),
        ("genre=Jazz", 2),
        ("artist=Missing", 0),
    ],
)
async def test_api_tracks_max_results(
    multi_album_app: Application, limit: int, query: str, matching_count: int
):
    get_config(multi_album_app).max_results = limit
    response = await TestClient(multi_album_app).get("/api/tracks?" + query)
    assert response.status == 200
    files = (await response.json())["files"]
    expected_count = min(limit, matching_count) if limit > 0 else matching_count
    assert len(files) == expected_count


async def test_api_tracks_max_results_after_sorting(multi_album_app: Application):
    files = get_mediascan_db_files_artists_joined(multi_album_app)
    files["year"] = files["title"].map(
        {"Track 1": "1990", "Other Track": "2010", "Second Track": "2000"}
    )
    get_config(multi_album_app).max_results = 1
    response = await TestClient(multi_album_app).get("/api/tracks?sort=year")
    assert response.status == 200
    tracks = (await response.json())["files"]
    assert [track["title"] for track in tracks] == ["Other Track"]


async def test_api_albums(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/albums")
    assert resp.status == 200
    data = await resp.json()
    assert len(data["albums"]) == 1
    assert data["albums"][0]["album"] == "Album Metadata Name"
    assert data["albums"][0]["year"] == 2001
    assert data["albums"][0]["artist"] == "Artist One"
    assert data["albums"][0]["coverPath"].endswith("/Artist One/Album [2000]/cover.jpg")
    assert data["albums"][0]["explicitCover"] is True


@pytest.mark.parametrize(
    "query, count",
    [
        ("explicitCover=true", 1),
        ("explicitCover=TRUE", 1),
        ("explicitCover=1", 1),
        ("explicitCover=false", 0),
        ("explicitCover=FALSE", 0),
        ("explicitCover=0", 0),
        ("album[]=album%20metadata%20name&year[]=2001", 1),
        ("album=Album", 1),
        ("album=metadata", 1),
        ("album=Missing", 0),
        ("year=2000", 0),
        ("minYear=2001&maxYear=2001", 1),
        ("minYear=2002", 0),
        ("maxYear=2000", 0),
        ("artist=Artist%20One&albumartist=Artist%20One&genre=Rock&title=Track%201", 1),
        ("countryCode=US&regionCode=US-AL&city=Huntsville&languageCode=en", 1),
        ("genre=Jazz", 0),
        ("artist=Nobody", 0),
        ("artist=one&artist=nobody", 1),
        ("countryCode=CA", 0),
        ("artist=Nobody&genre=Rock&minYear=2000", 0),
        ("explicitCover=true&genre=Rock&year=2001", 1),
        ("explicitCover=false&genre=Rock", 0),
    ],
)
async def test_api_albums_filtered(app: Application, query: str, count: int):
    resp = await TestClient(app).get("/api/albums?" + query)
    assert resp.status == 200
    assert len((await resp.json())["albums"]) == count


@pytest.mark.parametrize("value", ["yes", "2", "", "not-a-bool"])
async def test_api_albums_invalid_explicit_cover(app: Application, value: str):
    resp = await TestClient(app).get("/api/albums?explicitCover=" + value)
    assert resp.status == 400


async def test_api_albums_bare_explicit_cover(app: Application):
    resp = await TestClient(app).get("/api/albums?explicitCover")
    assert resp.status == 400


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?artist=Artist%20One&album=Album&year=2000",
        "?albumartist[]=Artist%20One&album[]=album&minYear=1999&maxYear=2000",
        "?countryCode=US&genre=Rock",
    ],
)
async def test_api_album(app: Application, query: str):
    resp = await TestClient(app).get("/api/album" + query)
    assert resp.status == 200
    assert await resp.json() == {
        "album": {
            "id": 1,
            "path": "/data/Music/A/Artist One/Album [2000]",
            "name": "Album Metadata Name",
            "year": 2001,
            "explicitCover": True,
        }
    }


@pytest.mark.parametrize(
    "query",
    ["?album=Missing", "?artist=Nobody", "?year=2001", "?genre=Jazz", "?minYear=2002"],
)
async def test_api_album_not_found(app: Application, query: str):
    resp = await TestClient(app).get("/api/album" + query)
    assert resp.status == 404


async def test_api_album_matches_path_not_name(db_file: Path):
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT INTO artist (path, name, countrycode, regioncode, city, languagecode) "
            "VALUES ('/data/Music/B/Artist Two', 'Artist Two', 'US', 'US-AL', 'Huntsville', 'en')"
        )
        conn.execute(
            "INSERT INTO mediafile (path, albumpath, artistpath, title, artist, albumartist, album, genre, year) "
            "VALUES ('/data/Music/B/Artist Two/Album [2000]/01.mp3', "
            "'/data/Music/B/Artist Two/Album [2000]', '/data/Music/B/Artist Two', "
            "'Other Track', 'Artist Two', 'Artist Two', 'Album', 'Rock', '2000')"
        )
        conn.execute(
            "INSERT INTO album (path, name, year, explicitcover) "
            "VALUES ('/data/Music/B/Artist Two/Album [2000]', 'Album Metadata Name', 2000, 0)"
        )
    application = create_app(
        MediatunesServiceConfig(
            mediascan_database_file_path=f"sqlite:///{db_file}",
            server_config=ServerConfig(url_prefix="/api"),
        )
    )
    await application.start()
    resp = await TestClient(application).get("/api/album?artist=Artist%20Two&album=Album")
    assert resp.status == 200
    assert await resp.json() == {
        "album": {
            "id": 2,
            "path": "/data/Music/B/Artist Two/Album [2000]",
            "name": "Album Metadata Name",
            "year": 2000,
            "explicitCover": False,
        }
    }


@pytest.mark.parametrize("metadata", ["empty", "legacy", "unmatched"])
async def test_api_album_without_metadata(db_file: Path, metadata: str):
    with sqlite3.connect(db_file) as conn:
        if metadata == "legacy":
            conn.execute("DROP TABLE album")
        elif metadata == "empty":
            conn.execute("DELETE FROM album")
        else:
            conn.execute("UPDATE album SET path = '/other/album'")
    application = create_app(
        MediatunesServiceConfig(
            mediascan_database_file_path=f"sqlite:///{db_file}",
            server_config=ServerConfig(url_prefix="/api"),
        )
    )
    await application.start()
    client = TestClient(application)
    assert (await client.get("/api/album?album=Album")).status == 404
    albums_response = await client.get("/api/albums")
    assert albums_response.status == 200
    albums = (await albums_response.json())["albums"]
    assert len(albums) == (1 if metadata == "unmatched" else 0)
    assert (await client.get("/api/artist?artist=Artist%20One")).status == 200


@pytest.fixture()
async def multi_album_app(db_file: Path) -> Application:
    with sqlite3.connect(db_file) as conn:
        # Duplicate names/years must not collapse distinct album paths.
        conn.execute(
            "INSERT INTO album (path, name, year, explicitcover) "
            "VALUES ('/data/Music/A/Artist One/Other [2000]', 'Album Metadata Name', 2001, 0)"
        )
        conn.execute(
            "INSERT INTO mediafile (path, albumpath, artistpath, title, artist, albumartist, album, genre, year) "
            "VALUES ('/data/Music/A/Artist One/Other [2000]/01.mp3', "
            "'/data/Music/A/Artist One/Other [2000]', '/data/Music/A/Artist One', "
            "'Other Track', 'Artist One', '', 'Other', 'Jazz', '2000')"
        )
        conn.execute(
            "INSERT INTO mediafile (path, albumpath, artistpath, title, artist, albumartist, album, genre, year) "
            "VALUES ('/data/Music/A/Artist One/Album [2000]/02.mp3', "
            "'/data/Music/A/Artist One/Album [2000]', '/data/Music/A/Artist One', "
            "'Second Track', 'Guest Artist', 'Artist One', 'Album', 'Jazz', '2000')"
        )
        conn.execute(
            "INSERT INTO album (path, name, year, explicitcover) "
            "VALUES ('/data/Music/A/Artist One/Standalone [1990]', 'Standalone', 1990, 0)"
        )
    application = create_app(
        MediatunesServiceConfig(
            mediascan_database_file_path=f"sqlite:///{db_file}",
            server_config=ServerConfig(url_prefix="/api"),
        )
    )
    await application.start()
    return application


async def test_api_albums_distinct_paths_and_no_tracks(multi_album_app: Application):
    client = TestClient(multi_album_app)
    resp = await client.get("/api/albums?sort=year")
    assert resp.status == 200
    albums = (await resp.json())["albums"]
    assert [album["year"] for album in albums] == [2001, 2001, 1990]
    assert len({album["coverPath"] for album in albums}) == 3
    assert [album["explicitCover"] for album in albums] == [True, False, False]
    assert albums[0]["artist"] == albums[1]["artist"] == "Artist One"
    assert albums[2]["artist"] == ""
    resp = await client.get("/api/albums?explicitCover=false")
    assert resp.status == 200
    assert len((await resp.json())["albums"]) == 2
    resp = await client.get("/api/albums?artist=Guest%20Artist&genre=Rock")
    assert resp.status == 200
    assert (await resp.json())["albums"] == []


@pytest.mark.parametrize("sort", ["artist", "album", "year", "random"])
async def test_api_albums_limit_and_sort(multi_album_app: Application, sort: str):
    config = get_config(multi_album_app)
    config.max_results_album_covers = 1
    resp = await TestClient(multi_album_app).get("/api/albums?sort=" + sort)
    assert resp.status == 200
    assert len((await resp.json())["albums"]) == 1


@pytest.mark.parametrize("sort, field", [("artist", "artist"), ("album", "album"), ("year", "year")])
async def test_api_albums_sort_order(multi_album_app: Application, sort: str, field: str):
    resp = await TestClient(multi_album_app).get("/api/albums?sort=" + sort)
    assert resp.status == 200
    values = [album[field] for album in (await resp.json())["albums"]]
    assert values == sorted(values, reverse=sort == "year")


async def test_api_albums_cover_root(app: Application):
    config = get_config(app)
    config.playback_methods.local.media_path = "/data/Music/"
    config.album_covers_path = "/covers/"
    resp = await TestClient(app).get("/api/albums")
    assert resp.status == 200
    assert (await resp.json())["albums"][0]["coverPath"] == "/covers/A/Artist One/Album [2000]/cover.jpg"


@pytest.mark.parametrize("value, status", [("true", 200), ("false", 404), ("0", 404), ("1", 200)])
async def test_api_album_explicit_cover(app: Application, value: str, status: int):
    resp = await TestClient(app).get("/api/album?explicitCover=" + value)
    assert resp.status == status


async def test_api_artists(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/artists")
    assert resp.status == 200
    data = await resp.json()
    assert data["artists"] == [{"name": "Artist One", "count": 1}]


async def test_api_artist(app: Application):
    client = TestClient(app)
    resp = await client.get("/api/artist?artist=Artist%20One")
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
    assert data["albumartist"] == "Artist One"
    assert "coverPath" in data

    resp = await client.get("/api/random-track?genre=Jazz")
    assert resp.status == 404


@pytest.mark.parametrize(
    ("query", "expected_titles"),
    [
        ("explicitCover=true", {"Track 1", "Second Track"}),
        ("explicitCover=false", {"Other Track"}),
        ("explicitCover=TRUE&genre=Jazz", {"Second Track"}),
        ("explicitCover=0&genre=Jazz", {"Other Track"}),
        ("explicitCover=false&genre=Rock", set[str]()),
        ("explicitCover=true&artist=Missing", set[str]()),
    ],
)
async def test_api_track_selection_explicit_cover(
    multi_album_app: Application,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    expected_titles: set[str],
):
    def choose_first(files: list[MediaFile]) -> MediaFile:
        return files[0]

    monkeypatch.setattr("app.api.routes.random.choice", choose_first)
    client = TestClient(multi_album_app)
    response = await client.get("/api/tracks?" + query)
    assert response.status == 200
    assert {file["title"] for file in (await response.json())["files"]} == expected_titles

    response = await client.get("/api/random-track?" + query)
    assert response.status == (200 if expected_titles else 404)
    if expected_titles:
        assert (await response.json())["title"] in expected_titles


@pytest.mark.parametrize("explicit_cover", ["true", "false"])
@pytest.mark.parametrize("metadata", ["empty", "legacy", "unmatched"])
async def test_api_random_track_explicit_cover_without_metadata(
    db_file: Path, explicit_cover: str, metadata: str
):
    with sqlite3.connect(db_file) as conn:
        if metadata == "legacy":
            conn.execute("DROP TABLE album")
        elif metadata == "empty":
            conn.execute("DELETE FROM album")
        else:
            conn.execute("UPDATE album SET path = '/other/album'")
    application = create_app(
        MediatunesServiceConfig(
            mediascan_database_file_path=f"sqlite:///{db_file}",
            server_config=ServerConfig(url_prefix="/api"),
        )
    )
    await application.start()
    client = TestClient(application)
    assert (await client.get("/api/random-track?explicitCover=" + explicit_cover)).status == 404
    assert (await client.get("/api/random-track")).status == 200
