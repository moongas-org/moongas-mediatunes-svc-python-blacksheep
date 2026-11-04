import pandas as pd
import pytest
from blacksheep import Application, Request
from mediascan.utils.db.mediascan_db_loader import get_df_track_album_artist_joined
from sqlalchemy import create_engine, text

from app.types.arg_types import ArgsDict, ArgTypes
from app.utils.mediascan_db.tracks import (
    df_to_track_data_with_album_and_artist_data_list,
    expand_artist_args,
    filter_tracks,
)
from app.utils.request_args_utils import get_request_args

TRIBE = "A Tribe Called Quest, Busta Rhymes, Redman"
TRIBE_EXPANDED = [TRIBE, "A Tribe Called Quest", "Busta Rhymes", "Redman"]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("artist=A+Tribe+Called+Quest,+Busta+Rhymes,+Redman", TRIBE_EXPANDED),
        (
            "artist=A+Tribe+Called+Quest,Busta+Rhymes,Redman",
            ["A Tribe Called Quest,Busta Rhymes,Redman", *TRIBE_EXPANDED[1:]],
        ),
        ("artist=Coldplay", ["Coldplay"]),
        ("artist=Coldplay&artist=U2,+Muse", ["Coldplay", "U2, Muse", "U2", "Muse"]),
        ("artist=,Coldplay,,+", [",Coldplay,, ", "Coldplay"]),
        ("artist=Coldplay,+coldplay&artist=Coldplay", ["Coldplay, coldplay", "Coldplay", "coldplay"]),
    ],
)
def test_expand_artist_args(query: str, expected: list[str]):
    args = get_request_args(Request("GET", f"/artist?{query}&genre=Rock".encode(), []))
    expanded = expand_artist_args(args)
    assert expanded[ArgTypes.List.Str.Artist] == expected
    assert expanded[ArgTypes.List.Str.Genre] == ["Rock"]


def test_expand_artist_args_does_not_modify_input():
    args: ArgsDict = {ArgTypes.List.Str.Artist: [TRIBE]}
    expanded = expand_artist_args(args)
    assert args == {ArgTypes.List.Str.Artist: [TRIBE]}
    assert expanded[ArgTypes.List.Str.Artist] == TRIBE_EXPANDED


def test_expand_artist_args_without_artist():
    args: ArgsDict = {ArgTypes.List.Str.Genre: ["Rock"]}
    assert expand_artist_args(args) == {ArgTypes.List.Str.Genre: ["Rock"]}


@pytest.mark.parametrize(
    "query, expected_ids",
    [
        ("", [1, 2, 3]),
        ("hasspotify=true", [1, 3]),
        ("hasspotify=false", [2]),
        ("hasspotify=1&genre=Jazz", [3]),
        ("hasspotify=0&genre=Rock", []),
    ],
)
@pytest.mark.parametrize("spotify_values", [[1, 0, 1], [True, False, True]])
def test_filter_tracks_hasspotify(
    query: str, expected_ids: list[int], spotify_values: list[int] | list[bool]
):
    tracks = pd.DataFrame(
        {"id": [1, 2, 3], "hasspotify": spotify_values, "genre": ["Rock", "Jazz", "Jazz"]},
        index=[4, 8, 12],
    )
    args = get_request_args(Request("GET", f"/tracks?{query}".encode(), []))
    filtered = filter_tracks(Application(), tracks, args)
    assert filtered["id"].tolist() == expected_ids
    assert tracks["id"].tolist() == [1, 2, 3]


@pytest.mark.parametrize("year, expected_year", [("2000", 2000), ("", None)])
def test_track_dataframe_conversion_accepts_text_year(year: str, expected_year: int | None):
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE track (id INTEGER PRIMARY KEY, path TEXT, albumid INTEGER, "
                "artistid INTEGER, title TEXT, artist TEXT, albumartist TEXT, album TEXT, "
                "genre TEXT, year TEXT, hasspotify BOOLEAN)"
            ))
            conn.execute(text(
                "CREATE TABLE album (id INTEGER PRIMARY KEY, path TEXT, name TEXT, "
                "year INTEGER, explicitcover BOOLEAN, genre TEXT, artistid INTEGER)"
            ))
            conn.execute(text(
                "CREATE TABLE artist (id INTEGER PRIMARY KEY, path TEXT, name TEXT, "
                "countrycode TEXT, regioncode TEXT, city TEXT, languagecode TEXT)"
            ))
            conn.execute(text(
                "INSERT INTO artist VALUES "
                "(1, '/music/Artist', 'Artist', 'US', 'CA', 'Los Angeles', 'en')"
            ))
            conn.execute(text(
                "INSERT INTO album VALUES "
                "(1, '/music/Artist/Album', 'Album', 2000, 0, 'Rock', 1)"
            ))
            conn.execute(
                text(
                    "INSERT INTO track VALUES "
                    "(1, '/music/Artist/Album/track.mp3', 1, 1, 'Track', 'Artist', "
                    "'Artist', 'Album', 'Rock', :year, TRUE)"
                ),
                {"year": year},
            )

        tracks = get_df_track_album_artist_joined(engine)
        [track] = df_to_track_data_with_album_and_artist_data_list(tracks)
    finally:
        engine.dispose()

    assert track.year == expected_year
    assert track.id == 1
    assert track.artistid == 1
    assert track.albumid == 1
    assert track.path == "/music/Artist/Album/track.mp3"
    assert track.hasspotify is True
    assert track.album_path == "/music/Artist/Album"
    assert track.artist_path == "/music/Artist"
    assert track.genre == "Rock"
