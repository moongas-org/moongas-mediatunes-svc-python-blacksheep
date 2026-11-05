from pathlib import Path

import pandas as pd
import pytest
from blacksheep import Application
from blacksheep.server.routing import Router

from app.types.album_info import AlbumInfo
from app.types.arg_types import ArgTypes, ArgValues
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.utils.mediascan_db import albums as albums_module


def _patch_config(
    monkeypatch: pytest.MonkeyPatch,
    app: Application,
    config: MediatunesServiceConfig,
) -> None:
    def get_test_config(application: Application) -> MediatunesServiceConfig:
        assert application is app
        return config

    monkeypatch.setattr(albums_module, "get_config", get_test_config)


def test_get_albums_keeps_artist_aligned_with_duplicate_indexes(
    monkeypatch: pytest.MonkeyPatch,
):
    app = Application(router=Router())
    albums = pd.DataFrame(
        [
            {
                "album_id": 1,
                "album_path": "/music/Artist One/Album",
                "album_name": "Album One",
                "album_year": 2001,
                "album_explicitcover": True,
                "artist_name": "Artist One",
            },
            {
                "album_id": 2,
                "album_path": "/music/Artist Two/Album",
                "album_name": "Album Two",
                "album_year": 2002,
                "album_explicitcover": False,
                "artist_name": "Artist Two",
            },
        ],
        index=[0, 0],
    )
    config = MediatunesServiceConfig(
        max_results_album_covers=0,
        album_covers_path="/music/",
    )
    config.playback_methods.local.media_path = "/music/"
    _patch_config(monkeypatch, app, config)

    result = albums_module.get_albums(
        app, albums, {ArgTypes.Scalar.Enum.Sort: ArgValues.Scalar.Enum.Sort.Artist}
    )

    assert result == [
        AlbumInfo(
            "Artist One",
            "Album One",
            2001,
            Path("/music/Artist One/Album/cover.jpg"),
            True,
        ),
        AlbumInfo(
            "Artist Two",
            "Album Two",
            2002,
            Path("/music/Artist Two/Album/cover.jpg"),
            False,
        ),
    ]


def test_get_albums_returns_empty_for_empty_dataframe(
    monkeypatch: pytest.MonkeyPatch,
):
    app = Application(router=Router())
    config = MediatunesServiceConfig(max_results_album_covers=0)
    _patch_config(monkeypatch, app, config)

    assert albums_module.get_albums(app, pd.DataFrame(), {}) == []
