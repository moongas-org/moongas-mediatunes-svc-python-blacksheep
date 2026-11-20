import pytest

from app.types.arg_types import ArgType, ArgTypeBoolean, ArgTypes, ArgTypeUtil


def test_explicit_cover_boolean_arg_type():
    assert isinstance(ArgTypeBoolean.ExplicitCover, ArgType)
    assert ArgTypeBoolean("explicitCover") is ArgTypeBoolean.ExplicitCover
    assert str(ArgTypeBoolean.ExplicitCover) == "explicitCover"
    assert ArgTypes.Boolean.ExplicitCover is ArgTypeBoolean.ExplicitCover
    assert ArgTypeUtil.is_scalar(ArgTypes.Boolean.ExplicitCover)
    assert ArgTypeUtil.is_boolean(ArgTypes.Boolean.ExplicitCover)
    assert not ArgTypeUtil.is_integer(ArgTypes.Boolean.ExplicitCover)
    assert not ArgTypeUtil.is_boolean(ArgTypes.Scalar.Int.MinYear)


@pytest.mark.parametrize(
    "name, arg_type",
    [
        ("hascover", ArgTypes.Boolean.HasCover),
        ("hasspotify", ArgTypes.Boolean.HasSpotify),
        ("hasmedia", ArgTypes.Boolean.HasMedia),
        ("haslyricstxt", ArgTypes.Boolean.HasLyricsTxt),
        ("haslyricslrc", ArgTypes.Boolean.HasLyricsLrc),
    ],
)
def test_track_boolean_arg_type(name: str, arg_type: ArgTypeBoolean):
    assert ArgTypeBoolean(name) is arg_type
    assert str(arg_type) == name
    assert ArgTypeUtil.is_scalar(arg_type)
    assert ArgTypeUtil.is_boolean(arg_type)
    assert not ArgTypeUtil.is_integer(arg_type)
