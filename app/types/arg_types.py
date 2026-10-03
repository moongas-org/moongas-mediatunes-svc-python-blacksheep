from typing import Dict, List, Union
from enum import StrEnum


class ArgType(StrEnum):
    pass


class ArgTypeScalarInt(ArgType):
    MinYear = "minYear"
    MaxYear = "maxYear"


class ArgTypeScalarEnum(ArgType):
    Sort = "sort"


class ArgTypeScalar:
    Int = ArgTypeScalarInt
    Enum = ArgTypeScalarEnum


class ArgTypeListStr(ArgType):
    Genre = "genre"
    Artist = "artist"
    AlbumArtist = "albumartist"
    Album = "album"
    Title = "title"
    Year = "year"
    CountryCode = "countryCode"
    RegionCode = "regionCode"
    City = "city"
    LanguageCode = "languageCode"


class ArgTypeList:
    Str = ArgTypeListStr


class ArgTypes:
    List = ArgTypeList
    Scalar = ArgTypeScalar


class ArgTypeUtil:
    @classmethod
    def is_scalar(cls, arg_type: ArgType) -> bool:
        return arg_type in (
            ArgTypes.Scalar.Int.MinYear,
            ArgTypes.Scalar.Int.MaxYear,
            ArgTypes.Scalar.Enum.Sort,
        )

    @classmethod
    def is_integer(cls, arg_type: ArgType) -> bool:
        return arg_type in (
            ArgTypes.Scalar.Int.MinYear,
            ArgTypes.Scalar.Int.MaxYear,
        )


ArgValueScalarInt = int
ArgValueListStr = List[str]


class ArgValueScalarEnumSort(StrEnum):
    Name = "name"
    Count = "count"
    Year = "year"
    Artist = "artist"
    Album = "album"
    Random = "random"


class ArgValuesScalarEnum:
    Sort = ArgValueScalarEnumSort


class ArgValuesScalar:
    Enum = ArgValuesScalarEnum


class ArgValues:
    Scalar = ArgValuesScalar


ArgValue = Union[ArgValueScalarInt, ArgValueListStr, ArgValueScalarEnumSort]
ArgsDict = Dict[ArgType, ArgValue]


def args_dict_to_str(args: ArgsDict) -> str:
    msg = "["
    for k, v in args.items():
        msg += f"{k}={v},"
    msg += "]"
    return msg
