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
