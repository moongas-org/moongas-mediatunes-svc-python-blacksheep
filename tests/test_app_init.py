from pathlib import Path
import sqlite3

import pytest
import pandas as pd
from blacksheep import Application

from app import create_app
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.utils.app_utils import (
    get_mediascan_db_albums,
    get_mediascan_db_artists,
    get_mediascan_db_tracks,
    get_mediascan_db_tracks_album_artist_joined,
)


def test_create_app_missing_database_file(tmp_path: Path):
    non_existent_db = tmp_path / "non_existent.db"
    config = MediatunesServiceConfig(
        mediascan_database_file_path=f"sqlite:///{non_existent_db}"
    )
    with pytest.raises(FileNotFoundError, match="SQLite database file not found"):
        create_app(config)


def test_create_app_empty_database_file(tmp_path: Path):
    empty_db = tmp_path / "empty.db"
    empty_db.touch()
    config = MediatunesServiceConfig(
        mediascan_database_file_path=f"sqlite:///{empty_db}"
    )
    with pytest.raises(ValueError, match="is empty"):
        create_app(config)


def test_create_app_missing_required_tables(tmp_path: Path):
    db_file = tmp_path / "mediascan_test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    config = MediatunesServiceConfig(
        mediascan_database_file_path=f"sqlite:///{db_file}"
    )
    with pytest.raises(ValueError, match="missing required table"):
        create_app(config)


def test_create_app_path_based_schema_requires_rescan(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    db_file = tmp_path / "path_based.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE track (id INTEGER PRIMARY KEY, artistpath TEXT, albumpath TEXT)")
        conn.execute("CREATE TABLE artist (path TEXT PRIMARY KEY)")
    with pytest.raises(ValueError, match="missing ID relationship columns"):
        create_app(MediatunesServiceConfig(mediascan_database_file_path=f"sqlite:///{db_file}"))
    assert "Rescan with a current mediascan" in caplog.text


def test_create_app_valid_database(tmp_path: Path):
    db_file = tmp_path / "valid.db"
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE track (id INTEGER PRIMARY KEY, artistid INTEGER, albumid INTEGER, "
        "title TEXT, artist TEXT, albumartist TEXT, genre TEXT)"
    )
    conn.execute(
        "CREATE TABLE artist (id INTEGER PRIMARY KEY, path TEXT, name TEXT, "
        "countrycode TEXT, regioncode TEXT, city TEXT, languagecode TEXT)"
    )
    conn.execute("INSERT INTO artist (path, name) VALUES ('artist1', 'Artist One')")
    conn.execute(
        "INSERT INTO track (id, artistid, title) VALUES (1, 1, 'Track 1')"
    )
    conn.commit()
    conn.close()

    config = MediatunesServiceConfig(
        mediascan_database_file_path=f"sqlite:///{db_file}"
    )
    app = create_app(config)
    assert isinstance(app, Application)
    tracks_df = get_mediascan_db_tracks(app)
    joined_df = get_mediascan_db_tracks_album_artist_joined(app)
    artists_df = get_mediascan_db_artists(app)
    assert len(tracks_df) == 1
    assert joined_df.loc[0, "title"] == "Track 1"
    assert len(artists_df) == 1
    assert get_mediascan_db_albums(app).empty
    # String columns are loaded as object dtype for fast row access under pandas 3.
    assert not any(isinstance(dtype, pd.StringDtype) for dtype in tracks_df.dtypes)
    assert not any(isinstance(dtype, pd.StringDtype) for dtype in artists_df.dtypes)
