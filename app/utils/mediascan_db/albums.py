import random
from pathlib import Path
from typing import Any, List, cast

import pandas as pd
from blacksheep import Application

from app.types.album_info import AlbumInfo
from app.types.arg_types import (
    ArgsDict,
    ArgTypes,
    ArgValueListStr,
    ArgValueScalarInt,
    ArgValues,
    args_dict_to_str,
)
from app.utils.app_utils import get_config
from app.utils.mediascan_db.tracks import filter_tracks, get_album_cover_path
from app.utils.string_utils import any_substr_in_str_ignore_case


def _album_column(albums: pd.DataFrame, column: str) -> str:
    if column == "artist":
        candidates = ("artist_name", "artist")
    elif column in ("countrycode", "regioncode", "city", "languagecode"):
        candidates = (f"artist_{column}", column)
    else:
        candidates = (f"album_{column}", column)
    return next((candidate for candidate in candidates if candidate in albums), column)


def _album_metadata_columns(albums: pd.DataFrame) -> pd.DataFrame:
    columns = ("id", "path", "name", "year", "explicitcover")
    result = pd.DataFrame(index=albums.index)
    for column in columns:
        source = _album_column(albums, column)
        if source in albums:
            result[column] = albums[source]
    return result


def filter_albums(app: Application, albums: pd.DataFrame, args: ArgsDict) -> pd.DataFrame:
    """Filter album rows using album metadata and their associated artist."""
    app.logger.info("filter_albums args=%s", args_dict_to_str(args))
    filtered = albums
    if filtered.empty:
        return filtered
    for arg_type, column in (
        (ArgTypes.List.Str.Album, "name"),
        (ArgTypes.List.Str.Genre, "genre"),
        (ArgTypes.List.Str.Year, "year"),
        (ArgTypes.List.Str.Artist, "artist"),
        (ArgTypes.List.Str.CountryCode, "countrycode"),
        (ArgTypes.List.Str.RegionCode, "regioncode"),
        (ArgTypes.List.Str.City, "city"),
        (ArgTypes.List.Str.LanguageCode, "languagecode"),
    ):
        if filtered.empty:
            return filtered
        if arg_type in args:
            values = cast(ArgValueListStr, args[arg_type])
            if values:
                actual_column = _album_column(filtered, column)
                filtered = filtered[
                    filtered[actual_column].map(lambda value: any_substr_in_str_ignore_case(str(value), values))
                ]
    if ArgTypes.Scalar.Int.MinYear in args:
        minimum = cast(ArgValueScalarInt, args[ArgTypes.Scalar.Int.MinYear])
        year_column = _album_column(filtered, "year")
        filtered = filtered[filtered[year_column] >= minimum]
    if ArgTypes.Scalar.Int.MaxYear in args:
        maximum = cast(ArgValueScalarInt, args[ArgTypes.Scalar.Int.MaxYear])
        year_column = _album_column(filtered, "year")
        filtered = filtered[filtered[year_column] <= maximum]
    if ArgTypes.Boolean.ExplicitCover in args:
        explicit_cover = cast(bool, args[ArgTypes.Boolean.ExplicitCover])
        cover_column = _album_column(filtered, "explicitcover")
        filtered = filtered[filtered[cover_column] == explicit_cover]
    return filtered


def get_album(app: Application, tracks: pd.DataFrame, albums: pd.DataFrame, args: ArgsDict) -> tuple[Any, ...] | None:
    """Return metadata for the first album with tracks matching the filters."""
    if albums.empty:
        return None
    tracks_filtered = filter_tracks(app, tracks, args)
    if tracks_filtered.empty:
        return None
    album_id_column = _album_column(albums, "id")
    albums_filtered = albums[albums[album_id_column].isin(tracks_filtered["albumid"].unique())]
    if ArgTypes.Boolean.ExplicitCover in args:
        explicit_cover = cast(bool, args[ArgTypes.Boolean.ExplicitCover])
        cover_column = _album_column(albums_filtered, "explicitcover")
        albums_filtered = albums_filtered[albums_filtered[cover_column] == explicit_cover]
    metadata = _album_metadata_columns(albums_filtered.head(1))
    return next(metadata.itertuples(name="album", index=False), None)


def get_albums(app: Application, albums: pd.DataFrame, args: ArgsDict) -> List[AlbumInfo]:
    """Return one AlbumInfo per album path, using album-table metadata."""
    config = get_config(app)
    albums_filtered = filter_albums(app, albums, args)
    if albums_filtered.empty:
        return []
    path_column = _album_column(albums_filtered, "path")
    albums_filtered = albums_filtered.drop_duplicates(subset=[path_column])
    metadata = _album_metadata_columns(albums_filtered)
    result: List[AlbumInfo] = []
    artist_column = _album_column(albums_filtered, "artist")
    metadata.insert(0, "artist", albums_filtered[artist_column].to_numpy())
    for artist_value, _, path, name, year, explicit_cover in metadata.itertuples(index=False, name=None):
        artist = "" if pd.isna(artist_value) else str(artist_value)
        result.append(
            AlbumInfo(
                artist,
                str(name),
                int(str(year)),
                get_album_cover_path(config, Path(str(path))),
                bool(explicit_cover),
            )
        )

    sort = ArgValues.Scalar.Enum.Sort.Random
    if ArgTypes.Scalar.Enum.Sort in args:
        sort = args[ArgTypes.Scalar.Enum.Sort]

    if sort == ArgValues.Scalar.Enum.Sort.Artist:
        result = sorted(result, key=lambda album: album.artist)
    elif sort == ArgValues.Scalar.Enum.Sort.Album:
        result = sorted(result, key=lambda album: album.album)
    elif sort == ArgValues.Scalar.Enum.Sort.Year:
        result = sorted(result, key=lambda album: album.year, reverse=True)
    elif sort == ArgValues.Scalar.Enum.Sort.Random:
        random.shuffle(result)

    if config.max_results_album_covers > 0 and len(result) > config.max_results_album_covers:
        result = result[: config.max_results_album_covers]
    return result
