import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Tuple, cast

import pandas as pd
from blacksheep import Application

from app.types.arg_types import (
    ArgsDict,
    ArgType,
    ArgTypes,
    ArgValueListStr,
    ArgValueScalarInt,
    ArgValues,
    args_dict_to_str,
)
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.utils.app_utils import get_config, get_mediascan_db_albums


@dataclass
class TrackDataWithArtistData:
    """Track data enriched with artist geo fields for API responses."""

    id: int
    path: str
    album_path: str
    artist_path: str
    size: int
    format: str
    title: str
    artist: str
    albumartist: str
    album: str
    genre: str
    year: int
    duration: int
    countryCode: str = ""
    regionCode: str = ""
    city: str = ""
    languageCode: str = ""


def row_to_track_data_with_artist_data(row: Any) -> TrackDataWithArtistData:
    return TrackDataWithArtistData(
        id=int(str(row.id)),
        path=str(row.path),
        album_path=str(row.album_path),
        artist_path=str(row.artist_path),
        size=0,
        format="mp3",
        title=str(row.title),
        artist=str(row.artist),
        albumartist=str(row.albumartist),
        album=str(row.album),
        genre=str(row.genre),
        year=int(str(row.year)),
        duration=0,
        countryCode=str(row.countrycode),
        regionCode=str(row.regioncode),
        city=str(row.city),
        languageCode=str(row.languagecode),
    )


def df_to_track_data_with_artist_data_list(
    df: pd.DataFrame,
) -> List[TrackDataWithArtistData]:
    return [row_to_track_data_with_artist_data(row) for row in df.itertuples()]


TRACK_FILTER_COLUMNS: Tuple[Tuple[ArgType, str], ...] = (
    (ArgTypes.List.Str.Artist, "artist"),
    (ArgTypes.List.Str.AlbumArtist, "albumartist"),
    (ArgTypes.List.Str.Album, "album"),
    (ArgTypes.List.Str.Genre, "genre"),
    (ArgTypes.List.Str.Title, "title"),
    (ArgTypes.List.Str.Year, "year"),
    (ArgTypes.List.Str.CountryCode, "countrycode"),
    (ArgTypes.List.Str.RegionCode, "regioncode"),
    (ArgTypes.List.Str.City, "city"),
    (ArgTypes.List.Str.LanguageCode, "languagecode"),
)


def _with_track_columns(tracks: pd.DataFrame) -> pd.DataFrame:
    """Expose track fields under their canonical names when joins alias collisions."""
    result = tracks.copy()
    for column in (
        "id",
        "path",
        "artistid",
        "albumid",
        "title",
        "artist",
        "albumartist",
        "album",
        "genre",
        "year",
    ):
        alias = f"track_{column}"
        if alias in result.columns:
            result[column] = result[alias]
    for column in (
        "album_path",
        "artist_path",
        "countrycode",
        "regioncode",
        "city",
        "languagecode",
    ):
        if column in result:
            result[column] = result[column].fillna("")
    return result


def contains_any_ignore_case(
    column: "pd.Series[Any]", substrings: List[str]
) -> "pd.Series[bool]":
    """Vectorized any_substr_in_str_ignore_case; str() keeps missing values as "nan"."""
    lowered = column.map(str).str.lower()
    matches = pd.Series(False, index=column.index)
    for substring in substrings:
        matches |= lowered.str.contains(substring.lower(), regex=False)
    return matches


def expand_artist_args(args: ArgsDict) -> ArgsDict:
    """
    Add each comma-separated part of every 'artist' value as an additional value,
    keeping the original. Returns a new dict without modifying the input.
    """
    values = cast(ArgValueListStr, args.get(ArgTypes.List.Str.Artist, []))
    if not values:
        return args
    expanded: List[str] = []
    for value in values:
        if value not in expanded:
            expanded.append(value)
        for part in value.split(","):
            part = part.strip()
            if part and part not in expanded:
                expanded.append(part)
    return {**args, ArgTypes.List.Str.Artist: expanded}


def filter_tracks(
    app: Application, tracks: pd.DataFrame, args: ArgsDict
) -> pd.DataFrame:
    """Filter track rows; the dataframe should include joined artist data."""
    tracks = _with_track_columns(tracks)
    args_orig = args.copy()
    args = expand_artist_args(args)
    app.logger.info(
        "filter_tracks args[original]=%s args[expanded]=%s",
        args_dict_to_str(args_orig),
        args_dict_to_str(args),
    )
    if ArgTypes.Boolean.ExplicitCover in args:
        albums = get_mediascan_db_albums(app)
        explicit_cover = cast(bool, args[ArgTypes.Boolean.ExplicitCover])
        album_id_column = "album_id" if "album_id" in albums else "id"
        album_ids = albums.loc[
            albums["explicitcover"] == explicit_cover, album_id_column
        ]
        tracks = tracks[tracks["albumid"].isin(album_ids)]
    mask = pd.Series(True, index=tracks.index)
    min_year = cast(ArgValueScalarInt, args.get(ArgTypes.Scalar.Int.MinYear, 0))
    max_year = cast(ArgValueScalarInt, args.get(ArgTypes.Scalar.Int.MaxYear, 0))
    if min_year or max_year:
        years = tracks["year"].astype(float).astype(int)
        if min_year:
            mask &= years >= min_year
        if max_year:
            mask &= years <= max_year
    for arg_type, column in TRACK_FILTER_COLUMNS:
        values = cast(ArgValueListStr, args.get(arg_type, []))
        if values:
            app.logger.debug("filtering based on %s[] arg = [%s]", arg_type, values)
            mask &= contains_any_ignore_case(tracks[column], values)
    return tracks[mask]


def get_tracks_list(
    app: Application, tracks: pd.DataFrame, args: ArgsDict
) -> List[TrackDataWithArtistData]:
    return df_to_track_data_with_artist_data_list(filter_tracks(app, tracks, args))


def get_genres(tracks: List[TrackDataWithArtistData]) -> List[str]:
    return sorted({track.genre for track in tracks})


def get_genre_counts(tracks: pd.DataFrame, sort: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    tracks = _with_track_columns(tracks)
    for track in tracks.itertuples():
        genre = str(track.genre)
        counts[genre] = counts.get(genre, 0) + 1
    if sort == "name":
        return dict(sorted(counts.items()))
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


class TracksResult(NamedTuple):
    tracks: List[TrackDataWithArtistData]
    album: tuple[Any, ...] | None


def get_single_album(
    app: Application, tracks_filtered: pd.DataFrame
) -> tuple[Any, ...] | None:
    """Return album metadata only if all filtered tracks share one album ID."""
    if tracks_filtered.empty:
        return None
    album_ids = tracks_filtered["albumid"]
    if album_ids.isna().any():
        return None
    first_id = int(album_ids.iloc[0])
    if not (album_ids == first_id).all():
        return None
    albums = get_mediascan_db_albums(app)
    album_id_column = "album_id" if "album_id" in albums else "id"
    matches = albums.loc[albums[album_id_column] == first_id].head(1)
    metadata = _album_metadata_columns(matches)
    return next(metadata.itertuples(name="album", index=False), None)


def _album_metadata_columns(albums: pd.DataFrame) -> pd.DataFrame:
    column_names = {
        "id": "album_id" if "album_id" in albums else "id",
        "path": "album_path" if "album_path" in albums else "path",
        "name": "album_name" if "album_name" in albums else "name",
        "year": "album_year" if "album_year" in albums else "year",
        "explicitcover": (
            "album_explicitcover" if "album_explicitcover" in albums else "explicitcover"
        ),
    }
    return albums[[column_names[column] for column in column_names]].rename(
        columns={source: target for target, source in column_names.items()}
    )


def get_tracks(
    app: Application, tracks: pd.DataFrame, args: ArgsDict
) -> TracksResult:
    filtered = filter_tracks(app, tracks, args)
    album = get_single_album(app, filtered)

    sort = ArgValues.Scalar.Enum.Sort.Random
    if ArgTypes.Scalar.Enum.Sort in args:
        sort = args[ArgTypes.Scalar.Enum.Sort]

    if (
        ArgTypes.List.Str.Album not in args
        and ArgTypes.List.Str.Artist not in args
        and ArgTypes.List.Str.AlbumArtist not in args
    ):
        if sort == ArgValues.Scalar.Enum.Sort.Year:
            filtered = filtered.sort_values(by="year", ascending=False)
        elif sort == ArgValues.Scalar.Enum.Sort.Random:
            filtered = filtered.sample(frac=1)

    max_results = get_config(app).max_results
    if max_results > 0:
        filtered = filtered.head(max_results)

    return TracksResult(df_to_track_data_with_artist_data_list(filtered), album)


def get_artist_counts(
    app: Application, tracks: pd.DataFrame, args: ArgsDict
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for track in filter_tracks(app, tracks, args).itertuples():
        name = str(track.albumartist)
        counts[name] = counts.get(name, 0) + 1

    sort = ArgValues.Scalar.Enum.Sort.Year
    if ArgTypes.Scalar.Enum.Sort in args:
        sort = args[ArgTypes.Scalar.Enum.Sort]

    if sort == ArgValues.Scalar.Enum.Sort.Name:
        return dict(sorted(counts.items()))
    if sort == ArgValues.Scalar.Enum.Sort.Random:
        items = list(counts.items())
        random.shuffle(items)
        return dict(items)
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def get_word_cloud_data_genres(tracks: pd.DataFrame) -> List[Dict[str, str]]:
    return [
        {"text": genre}
        for genre in get_genres(
            df_to_track_data_with_artist_data_list(_with_track_columns(tracks))
        )
    ]


def get_cover_path(
    config: MediatunesServiceConfig, track: TrackDataWithArtistData
) -> Path:
    return get_album_cover_path(config, Path(track.album_path))


def get_album_cover_path(
    config: MediatunesServiceConfig, dir_path: Path
) -> Path:
    if config.album_covers_path != config.playback_methods.local.media_path:
        dir_path = Path(
            str(dir_path).replace(
                config.playback_methods.local.media_path, config.album_covers_path
            )
        )
    return dir_path / "cover.jpg"
