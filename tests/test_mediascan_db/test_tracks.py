import pytest
from blacksheep import Request
from types import SimpleNamespace

from app.types.arg_types import ArgsDict, ArgTypes
from app.utils.mediascan_db.tracks import (
    TrackDataWithArtistData,
    expand_artist_args,
    row_to_track_data_with_artist_data,
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


def test_row_to_track_data_with_artist_data():
    track = row_to_track_data_with_artist_data(
        SimpleNamespace(
            id=1,
            path="/music/Artist/Album/track.yml",
            album_path="/music/Artist/Album",
            artist_path="/music/Artist",
            title="Track",
            artist="Artist",
            albumartist="Artist",
            album="Album",
            genre="Rock",
            year=2001,
            countrycode="US",
            regioncode="CA",
            city="Los Angeles",
            languagecode="en",
        )
    )

    assert isinstance(track, TrackDataWithArtistData)
    assert track.id == 1
    assert track.path == "/music/Artist/Album/track.yml"
    assert track.format == "mp3"
    assert track.album_path == "/music/Artist/Album"
    assert track.artist_path == "/music/Artist"
    assert track.countryCode == "US"
    assert track.regionCode == "CA"
    assert track.languageCode == "en"
