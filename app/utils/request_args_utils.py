from blacksheep import Request

from typing import List

from app.types.arg_types import (
    ArgsDict,
    ArgType,
    ArgTypes,
    ArgTypeUtil,
    ArgValues,
)


REQUEST_ARG_TYPES: List[ArgType] = [
    ArgTypes.List.Str.Genre,
    ArgTypes.List.Str.Artist,
    ArgTypes.List.Str.AlbumArtist,
    ArgTypes.List.Str.Album,
    ArgTypes.List.Str.Title,
    ArgTypes.List.Str.Year,
    ArgTypes.List.Str.CountryCode,
    ArgTypes.List.Str.RegionCode,
    ArgTypes.List.Str.City,
    ArgTypes.List.Str.LanguageCode,
    ArgTypes.Scalar.Int.MinYear,
    ArgTypes.Scalar.Int.MaxYear,
    ArgTypes.Scalar.Enum.Sort,
]


def get_request_args(
    request: Request,
    arg_types: List[ArgType] = REQUEST_ARG_TYPES,
) -> ArgsDict:
    ret: ArgsDict = {}
    for arg_type in arg_types:
        if ArgTypeUtil.is_scalar(arg_type):
            values = request.query.get(str(arg_type))
            if values:
                value = values[0]
                if ArgTypeUtil.is_integer(arg_type):
                    ret[arg_type] = int(value)
                else:
                    # must be enum type, and there's only one currently
                    ret[arg_type] = ArgValues.Scalar.Enum.Sort(value)
        else:
            values = request.query.get(str(arg_type))
            if not values:
                values = request.query.get(f"{arg_type}[]")
            if values:
                ret[arg_type] = values
    return ret
