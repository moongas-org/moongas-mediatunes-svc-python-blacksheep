import pytest
from blacksheep import Request
from blacksheep.exceptions import BadRequest

from app.types.arg_types import ArgTypes
from app.utils.request_args_utils import get_request_args


@pytest.mark.parametrize(
    "value, expected",
    [("true", True), ("TRUE", True), ("1", True), ("false", False), ("FaLsE", False), ("0", False)],
)
def test_explicit_cover_is_boolean(value: str, expected: bool):
    request = Request("GET", f"/albums?explicitCover={value}".encode(), [])
    assert get_request_args(request)[ArgTypes.Boolean.ExplicitCover] is expected


@pytest.mark.parametrize("query", ["", "?genre=Rock"])
def test_explicit_cover_omitted(query: str):
    request = Request("GET", ("/albums" + query).encode(), [])
    assert ArgTypes.Boolean.ExplicitCover not in get_request_args(request)


@pytest.mark.parametrize("query", ["?explicitCover=", "?explicitCover", "?explicitCover=yes"])
def test_invalid_explicit_cover(query: str):
    request = Request("GET", ("/albums" + query).encode(), [])
    with pytest.raises(BadRequest, match="expected true, false, 1, or 0"):
        get_request_args(request)


@pytest.mark.parametrize(
    "value, expected",
    [("true", True), ("TRUE", True), ("1", True), ("false", False), ("FaLsE", False), ("0", False)],
)
@pytest.mark.parametrize("flag", ["hasspotify", "hasmedia", "haslyricstxt", "haslyricslrc"])
def test_track_flag_is_boolean(flag: str, value: str, expected: bool):
    request = Request("GET", f"/tracks?{flag}={value}".encode(), [])
    assert get_request_args(request) == {flag: expected}


@pytest.mark.parametrize("flag", ["hasspotify", "hasmedia", "haslyricstxt", "haslyricslrc"])
@pytest.mark.parametrize("suffix", ["=", "", "=yes"])
def test_invalid_track_flag(flag: str, suffix: str):
    query = f"?{flag}{suffix}"
    request = Request("GET", ("/tracks" + query).encode(), [])
    with pytest.raises(BadRequest, match="expected true, false, 1, or 0"):
        get_request_args(request)


@pytest.mark.parametrize("query", ["", "?genre=Rock"])
def test_track_flags_omitted(query: str):
    args = get_request_args(Request("GET", ("/tracks" + query).encode(), []))
    for flag in (
        ArgTypes.Boolean.HasSpotify,
        ArgTypes.Boolean.HasMedia,
        ArgTypes.Boolean.HasLyricsTxt,
        ArgTypes.Boolean.HasLyricsLrc,
    ):
        assert flag not in args
