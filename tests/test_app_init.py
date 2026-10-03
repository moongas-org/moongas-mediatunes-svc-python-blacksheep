from pathlib import Path
import sqlite3

import pytest
from blacksheep import Application

from app import create_app
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.utils.app_utils import get_mediascan_db_artists, get_mediascan_db_files


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


def test_create_app_valid_database(tmp_path: Path):
    db_file = tmp_path / "valid.db"
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE mediafile (id INTEGER PRIMARY KEY, artistpath TEXT, title TEXT)"
    )
    conn.execute("CREATE TABLE artist (path TEXT PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO artist (path, name) VALUES ('artist1', 'Artist One')")
    conn.execute(
        "INSERT INTO mediafile (id, artistpath, title) VALUES (1, 'artist1', 'Track 1')"
    )
    conn.commit()
    conn.close()

    config = MediatunesServiceConfig(
        mediascan_database_file_path=f"sqlite:///{db_file}"
    )
    app = create_app(config)
    assert isinstance(app, Application)
    files_df = get_mediascan_db_files(app)
    artists_df = get_mediascan_db_artists(app)
    assert len(files_df) == 1
    assert len(artists_df) == 1
