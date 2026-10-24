import pytest
from blacksheep import Request

from app.types.arg_types import ArgsDict, ArgTypes
from app.utils.media_files_utils import expand_artist_args
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
