import json
import os
import random
from typing import cast, Any, Dict, List, Set, Tuple
from urllib.parse import quote_plus  # type: ignore
from pathlib import Path
import pandas as pd

from blacksheep import Application

from dataclasses import dataclass


@dataclass
class MediaFile:
    """
    MediaFile dataclass
    (Like mediascan.MediaFile but with the addition of the artist geo data from mediascan.ArtistData)

    This is a convenient way for player to show the artist geo links.

    """

    path: str
    size: int
    format: str
    title: str
    artist: str
    albumartist: str
    album: str
    genre: str
    year: int
    duration: int
    countryCode: str
    regionCode: str
    city: str
    languageCode: str


from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.types.arg_types import (
    args_dict_to_str,
    ArgsDict,
    ArgType,
    ArgTypes,
    ArgValues,
    ArgValueListStr,
    ArgValueScalarInt,
)
from app.types.album_info import AlbumInfo
from app.utils.string_utils import str_in_list_ignore_case
from app.utils.app_utils import get_config, get_state

NameAndUrl = Tuple[str, str]
ArtistGeoCounts = Dict[NameAndUrl, int]


def row_to_mediafile(row: Any) -> MediaFile:
    mf = MediaFile(
        path=str(row.path),
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
    return mf


def df_to_mediafile_list(df: pd.DataFrame) -> List[MediaFile]:
    ret: List[MediaFile] = []
    for row in df.itertuples():
        ret.append(row_to_mediafile(row))
    return ret


def file_and_artist_paths_match(file_path: str, artist_path: str):
    """
    compare the artist and track (media file) paths
    this is is the most foolproof method,
    since we can assume a given file was scanned from a given artist directory
    if the leading part of the file path (i.e. the artist dir path) is identical.
    TODO: Add validation to ensure artist_name[0] matches ID3 tag albumartist value(s).

    # Prevent incomplete match e.g. these do not match:
    # "/data/Music/M"
    # "/data/Music/Municipal Waste/Hazardous Mutation [2005]/01 - Intro - Deathripper.mp3"
    """
    # below was SLOW:
    #   return str(Path(file_path).parent.parent) == artist_path
    # so now have this:
    tokens = file_path.split(os.sep)
    # leading slash results in first token being '', this ensures leading slash will be restored by the join
    file_artist_path = "/".join(tokens[:-2])
    # as processed above, file_artist_path will not have a trailing slash, so use startswith
    # just in case file_path has a trailing slash
    return artist_path.startswith(file_artist_path)


def filter_files(app: Application, files: pd.DataFrame, args: ArgsDict) -> pd.DataFrame:
    """
    Note: This is now meant to be used with joined dataframe containing both file and artist data
    """
    app.logger.info("filter_files args=%s", args_dict_to_str(args))
    results: List[Any] = []
    for row in files.itertuples():
        # ArgTypeScalarInt:
        arg_type = ArgTypes.Scalar.Int.MinYear
        if arg_type in args:
            arg_value = cast(ArgValueScalarInt, args[arg_type])
            if arg_value and int(float(str(row.year))) < arg_value:
                app.logger.debug(
                    "skipping file (value=%s) based on filter arg %s=%s",
                    arg_value,
                    arg_type,
                    arg_value,
                )
                app.logger.debug("filter_files args=%s", args_dict_to_str(args))
                continue
        arg_type = ArgTypes.Scalar.Int.MaxYear
        if arg_type in args:
            arg_value = cast(ArgValueScalarInt, args[arg_type])
            if arg_value and int(float(str(row.year))) > arg_value:
                app.logger.debug(
                    "skipping file (value=%s) based on filter arg %s=%s",
                    arg_value,
                    arg_type,
                    arg_value,
                )
                app.logger.debug("filter_files args=%s", args_dict_to_str(args))
                continue
        # ArgTypeListStr:
        skip = False
        country_code = ""
        region_code = ""
        city = ""
        country_code = str(row.countrycode)
        region_code = str(row.regioncode)
        city = str(row.city)
        language_code = str(row.languagecode)
        arg_type_list_file_value_map: Dict[ArgType, str] = {
            ArgTypes.List.Str.Artist: str(row.artist),
            ArgTypes.List.Str.AlbumArtist: str(row.albumartist),
            ArgTypes.List.Str.Album: str(row.album),
            ArgTypes.List.Str.Genre: str(row.genre),
            ArgTypes.List.Str.Title: str(row.title),
            ArgTypes.List.Str.Year: str(row.year),
            ArgTypes.List.Str.CountryCode: country_code,
            ArgTypes.List.Str.RegionCode: region_code,
            ArgTypes.List.Str.City: str(city),
            ArgTypes.List.Str.LanguageCode: language_code,
        }
        for arg_type, file_value in arg_type_list_file_value_map.items():
            if arg_type in args:
                arg_value_list = cast(ArgValueListStr, args[arg_type])
                app.logger.debug(
                    "filtering based on %s[] arg = [%s]", arg_type, arg_value_list
                )
                if len(arg_value_list) and not str_in_list_ignore_case(
                    file_value, arg_value_list
                ):
                    app.logger.debug(
                        "skipping file (value=%s) based on %s[] arg = [%s]",
                        file_value,
                        arg_type,
                        arg_value_list,
                    )
                    app.logger.debug("filter_files args=%s", args_dict_to_str(args))
                    skip = True
                    break
        if not skip:
            results.append(row)
    return pd.DataFrame(results)


def filter_artists(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> pd.DataFrame:
    app.logger.info("filter_artists args=%s", args_dict_to_str(args))
    results: List[Any] = []
    for row in artists.itertuples():
        # ArgTypeListStr:
        skip = False
        name = str(row.name)
        country_code = str(row.countrycode)
        region_code = str(row.regioncode)
        city = str(row.city)
        language_code = str(row.languagecode)
        arg_type_list_file_value_map: Dict[ArgType, str] = {
            ArgTypes.List.Str.Artist: name,
            ArgTypes.List.Str.CountryCode: country_code,
            ArgTypes.List.Str.RegionCode: region_code,
            ArgTypes.List.Str.City: city,
            ArgTypes.List.Str.LanguageCode: language_code,
        }
        for arg_type, file_value in arg_type_list_file_value_map.items():
            if arg_type in args:
                arg_value_list = cast(ArgValueListStr, args[arg_type])
                app.logger.debug(
                    "filtering artist based on %s[] arg = [%s]",
                    arg_type,
                    arg_value_list,
                )
                if len(arg_value_list) and not str_in_list_ignore_case(
                    file_value, arg_value_list
                ):
                    app.logger.debug(
                        "skipping artist (value=%s) based on %s[] arg = [%s]",
                        file_value,
                        arg_type,
                        arg_value_list,
                    )
                    app.logger.debug("filter_artists args=%s", args_dict_to_str(args))
                    skip = True
                    break
        if not skip:
            # app.logger.info("appending artist %s", f)
            # app.logger.info("filter_artists args=%s", args_dict_to_str(args))
            results.append(row)
    return pd.DataFrame(results)


def get_files_list(
    app: Application, files: pd.DataFrame, artists: pd.DataFrame, args: ArgsDict
) -> List[MediaFile]:
    files_list = filter_files(app, files, args)
    return df_to_mediafile_list(files_list)


def get_genres(files: List[MediaFile]) -> List[str]:
    ret: Set[str] = set()  # type: ignore
    for f in files:
        ret.add(f.genre)
    return sorted(ret)


def get_genre_counts(files: pd.DataFrame, sort: str) -> Dict[str, int]:
    ret: Dict[str, int] = {}
    for f in files.itertuples():
        if str(f.genre) in ret:
            ret[str(f.genre)] += 1
        else:
            ret[str(f.genre)] = 1
    if sort == "name":
        return dict(sorted(ret.items(), key=lambda item: item[0], reverse=False))
    else:  # default sort: by count
        return dict(sorted(ret.items(), key=lambda item: item[1], reverse=True))


def get_tracks(
    app: Application, files: pd.DataFrame, artists: pd.DataFrame, args: ArgsDict
) -> List[MediaFile]:
    df = filter_files(app, files, args)

    sort = ArgValues.Scalar.Enum.Sort.Random
    if ArgTypes.Scalar.Enum.Sort in args:
        sort = args[ArgTypes.Scalar.Enum.Sort]

    # Don't reorder tracks if displaying tracks for single album or a specific artist
    if (
        ArgTypes.List.Str.Album not in args
        and ArgTypes.List.Str.Artist not in args
        and ArgTypes.List.Str.AlbumArtist not in args
    ):
        if sort == ArgValues.Scalar.Enum.Sort.Year:
            """
            ret = list(
                sorted(
                    ret,
                    key=lambda x: getattr(x, "year"),
                    reverse=True,
                )
            )
            """
            df = df.sort_values(by="year", ascending=False)
        elif sort == ArgValues.Scalar.Enum.Sort.Random:
            # random.shuffle(ret)
            df = df.sample(frac=1)

    return df_to_mediafile_list(df)


def get_artist_counts(
    app: Application, files: pd.DataFrame, artists: pd.DataFrame, args: ArgsDict
) -> Dict[str, int]:
    """
    TODO: I want this function to get track counts from files but filter based on countryCode etc.
    TODO: Update filter files to filter on countryCode, etc., since we're using the table joined data frame.
    """
    ret: Dict[str, int] = {}

    files_filtered = filter_files(app, files, args)
    for f in files_filtered.itertuples():
        name = str(
            f.albumartist
        )  # alternatively could use f.name (artist name from artist.yml data)
        if name in ret:
            ret[name] += 1
        else:
            ret[name] = 1

    sort = ArgValues.Scalar.Enum.Sort.Year
    if ArgTypes.Scalar.Enum.Sort in args:
        sort = args[ArgTypes.Scalar.Enum.Sort]

    if sort == ArgValues.Scalar.Enum.Sort.Name:
        return dict(sorted(ret.items(), key=lambda item: item[0], reverse=False))
    elif sort == ArgValues.Scalar.Enum.Sort.Random:
        items = list(ret.items())
        random.shuffle(items)
        return dict(items)
    else:  # default sort: by count
        items = sorted(ret.items(), key=lambda item: item[1], reverse=True)
        ret = dict(items)

    return ret


def get_static_json_data(app: Application, filename: str) -> Dict[str, Any]:
    full_path = os.path.join(get_state(app).static_folder, "json_data", filename)
    try:
        with open(full_path, "r") as json_file:
            data = json.load(json_file)
            if isinstance(data, dict):
                return cast(Dict[str, Any], data)
    except FileNotFoundError:
        app.logger.error("Data file not found")
    except json.JSONDecodeError:
        app.logger.error("Could not decode JSON from file")
    return {}


def get_country_code_name_map(app: Application) -> Dict[str, str]:
    return get_static_json_data(app, "country_code_name_map.json")


def get_region_code_name_map(app: Application) -> Dict[str, str]:
    return get_static_json_data(app, "region_code_name_map.json")


def get_language_code_name_map(app: Application) -> Dict[str, str]:
    return get_static_json_data(app, "language_code_name_map.json")


class ArtistQueryCountInfo:
    """
    Represents an artist query url (url) with a single (for now) criteria (name, value)
    and the number of matching artists (count)
    E.g. the filter criteria could be countryCode and in that case the values might be:

        name="Country"
        value="United States"
        url="http://localhost/mediatunes-svc/artists?sort=count&countryCode=US"
        count=1611

    Observe that name and value are user-facing strings describing the query,
    not the URL parameter name(s) and value(s) (codes).
    """

    def __init__(self, name: str, value: str, url: str, count: int) -> None:
        self.name = name
        self.value = value
        self.url = url
        self.count = count


# TODO: Consolidate these count functions (lots of duplication)


def get_artist_country_code_counts(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> List[ArtistQueryCountInfo]:
    code_name_map = get_country_code_name_map(app)

    counts: ArtistGeoCounts = {}
    for artist in artists.itertuples():
        code = str(artist.countrycode)
        if code not in code_name_map:
            app.logger.error(
                "Failed to find name for countrycode=%s artist=%s", code, artist
            )
        else:
            value = code_name_map[code]
            url = f"/artists?sort=count&countryCode={quote_plus(code)}"
            uniq_key = (value, url)
            if uniq_key in counts:
                counts[uniq_key] += 1
            else:
                counts[uniq_key] = 1

    # default sort: by count
    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    counts = dict(items)

    ret: List[ArtistQueryCountInfo] = []
    for k, v in counts.items():
        ret.append(ArtistQueryCountInfo(name="Country", value=k[0], url=k[1], count=v))
    return ret


def get_artist_region_code_counts(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> List[ArtistQueryCountInfo]:
    code_name_map = get_region_code_name_map(app)

    counts: ArtistGeoCounts = {}
    for artist in artists.itertuples():
        code = str(artist.regioncode)
        if code not in code_name_map:
            app.logger.error(
                "Failed to find name for regioncode=%s artist=%s", code, artist
            )
        else:
            value = code_name_map[code]
            url = f"/artists?sort=count&regionCode={quote_plus(code)}"
            uniq_key = (value, url)
            if uniq_key in counts:
                counts[uniq_key] += 1
            else:
                counts[uniq_key] = 1

    # default sort: by count
    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    counts = dict(items)

    ret: List[ArtistQueryCountInfo] = []
    for k, v in counts.items():
        ret.append(ArtistQueryCountInfo(name="Region", value=k[0], url=k[1], count=v))
    return ret


def get_artist_language_code_counts(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> List[ArtistQueryCountInfo]:
    code_name_map = get_language_code_name_map(app)

    counts: ArtistGeoCounts = {}
    for artist in artists.itertuples():
        code = str(artist.languagecode)
        if code not in code_name_map:
            app.logger.error(
                "Failed to find name for languagecode=%s artist=%s", code, artist
            )
        else:
            value = code_name_map[code]
            url = f"/artists?sort=count&languageCode={quote_plus(code)}"
            uniq_key = (value, url)
            if uniq_key in counts:
                counts[uniq_key] += 1
            else:
                counts[uniq_key] = 1

    # default sort: by count
    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    counts = dict(items)

    ret: List[ArtistQueryCountInfo] = []
    for k, v in counts.items():
        ret.append(ArtistQueryCountInfo(name="Language", value=k[0], url=k[1], count=v))
    return ret


def get_artist_city_counts(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> List[ArtistQueryCountInfo]:
    country_code_name_map = get_country_code_name_map(app)
    region_code_name_map = get_region_code_name_map(app)

    counts: ArtistGeoCounts = {}
    for artist in artists.itertuples():
        city_qualifiers: List[str] = []
        cc = str(artist.countrycode)
        rc = str(artist.regioncode)
        if rc in region_code_name_map:
            region_name = region_code_name_map[rc]
            city_qualifiers.append(region_name)
        if cc in country_code_name_map:
            country_name = country_code_name_map[cc]
            city_qualifiers.append(country_name)
        city = str(artist.city)
        city_uniq = city
        if len(city_qualifiers):
            city_uniq = f"{city_uniq} ({', '.join(city_qualifiers)})"
        value = city_uniq
        url = (
            f"/artists?sort=count&city={quote_plus(city)}"
            f"&regionCode={quote_plus(rc)}&countryCode={quote_plus(cc)}"
        )
        uniq_key = (value, url)
        if uniq_key in counts:
            counts[uniq_key] += 1
        else:
            counts[uniq_key] = 1

    # default sort: by count
    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    counts = dict(items)

    ret: List[ArtistQueryCountInfo] = []
    for k, v in counts.items():
        ret.append(ArtistQueryCountInfo(name="City", value=k[0], url=k[1], count=v))
    return ret


def get_artists(
    app: Application, files: pd.DataFrame, artists: pd.DataFrame, args: ArgsDict
) -> List[str]:
    """
    This is currently only used by the word cloud
    """
    ARTISTS_FROM_FILES = False
    if ARTISTS_FROM_FILES:
        # O.G. behavior: get artists from files db table (originally files yaml) (more thorough but slow)
        # To be deleted, most likely
        ret: Set[str] = set()  # type: ignore
        files_filtered = filter_files(app, files, args)
        for f in files_filtered.itertuples():
            ret.add(str(f.artist))
        return sorted(ret)
    else:
        # New behavior: get artists from artists db table (derived from artist.yml files)
        # (faster but depends on presence of artist.yml files)
        ret: Set[str] = set()
        artists_filtered = filter_artists(app, artists, args)
        for a in artists_filtered.itertuples(name="artist", index=False):
            ret.add(str(a.name))
        return sorted(ret)


def get_artist(
    app: Application, files: pd.DataFrame, artists: pd.DataFrame, args: ArgsDict
) -> tuple[Any, ...] | None:
    """
    Similar to get_artists but only gets a single artists and displays links (album, tracks, shuffle)
    """
    artists_filtered = filter_artists(app, artists, args)
    if not artists_filtered.empty:
        return next(artists_filtered.itertuples(name="artist", index=False))
    return None


def get_word_cloud_data_genres(files: pd.DataFrame) -> List[Dict[str, str]]:
    ret: List[Dict[str, str]] = []
    genres = get_genres(df_to_mediafile_list(files))
    for g in genres:
        ret.append({"text": g})
    return ret


def get_word_cloud_data_artists(
    app: Application, files: pd.DataFrame, artists: pd.DataFrame, args: ArgsDict
) -> List[Dict[str, str]]:
    ret: List[Dict[str, str]] = []
    artists_filtered = get_artists(app, files, artists, args)
    for a in artists_filtered:
        ret.append({"text": a})
    return ret


def get_cover_path(config: MediatunesServiceConfig, file: MediaFile) -> Path:
    dir_path = Path(file.path.replace(os.path.basename(file.path), ""))
    if config.album_covers_path != config.playback_methods.local.media_path:
        # e.g. "/data/Music/Logic/Orville%20[2022]/cover.jpg"
        # config.playback_methods.local.media_path = "/data/Music/"
        # config.album_covers_path = "/var/www/html/Covers/"
        dir_path = Path(
            str(dir_path).replace(
                config.playback_methods.local.media_path, config.album_covers_path
            )
        )
    return dir_path / "cover.jpg"


def get_albums(
    app: Application,
    files: pd.DataFrame,
    artists: pd.DataFrame,
    args: ArgsDict,
) -> List[AlbumInfo]:
    """Returns a list of one AlbumInfo per unique album"""
    album_set: Set[AlbumInfo] = set()  # type: ignore
    config = get_config(app)
    files_filtered = filter_files(app, files, args)
    for f in files_filtered.itertuples():
        # try to go with albumartist first, in order to better group files
        # in the same album together, but fallback to artist as key if
        # albumartist is not set
        artist = str(f.albumartist)
        if not len(artist):
            artist = str(f.artist)
        album_set.add(
            AlbumInfo(
                artist,
                str(f.album),
                int(float(str(f.year))),
                get_cover_path(config, row_to_mediafile(f)),
            )
        )

    ret: List[AlbumInfo] = list(album_set)
    sort = ArgValues.Scalar.Enum.Sort.Random
    if ArgTypes.Scalar.Enum.Sort in args:
        sort = args[ArgTypes.Scalar.Enum.Sort]

    if sort == ArgValues.Scalar.Enum.Sort.Artist:
        ret = sorted(ret, key=lambda album: album.artist)
    elif sort == ArgValues.Scalar.Enum.Sort.Album:
        ret = sorted(ret, key=lambda album: album.album)
    elif sort == ArgValues.Scalar.Enum.Sort.Year:
        # sort by year (descending)
        ret = sorted(ret, key=lambda album: album.year, reverse=True)
    elif sort == ArgValues.Scalar.Enum.Sort.Random:
        random.shuffle(ret)

    # now that we have it sorted as specified, slice if necessary to keep the
    # result count below the configured max results limit for album covers
    if (
        config.max_results_album_covers > 0
        and len(ret) > config.max_results_album_covers
    ):
        ret = ret[: config.max_results_album_covers]

    return ret
