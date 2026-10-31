import json
import logging
import os
from typing import Any, Dict, List, cast

import pandas as pd
from blacksheep import Application

from app.types.arg_types import ArgsDict, ArgType, ArgTypes, ArgValueListStr, args_dict_to_str
from app.utils.app_utils import get_state
from app.utils.string_utils import any_substr_in_str_ignore_case


def filter_artists(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> pd.DataFrame:
    app.logger.info("filter_artists args=%s", args_dict_to_str(args))
    results: List[Any] = []
    for row in artists.itertuples():
        artist_values: Dict[ArgType, str] = {
            ArgTypes.List.Str.Artist: str(row.name),
            ArgTypes.List.Str.CountryCode: str(row.countrycode),
            ArgTypes.List.Str.RegionCode: str(row.regioncode),
            ArgTypes.List.Str.City: str(row.city),
            ArgTypes.List.Str.LanguageCode: str(row.languagecode),
        }
        for arg_type, artist_value in artist_values.items():
            if arg_type in args:
                arg_values = cast(ArgValueListStr, args[arg_type])
                app.logger.debug(
                    "filtering artist based on %s[] arg = [%s]", arg_type, arg_values
                )
                if arg_values and not any_substr_in_str_ignore_case(
                    artist_value, arg_values
                ):
                    app.logger.debug(
                        "skipping artist (value=%s) based on %s[] arg = [%s]",
                        artist_value,
                        arg_type,
                        arg_values,
                    )
                    if app.logger.isEnabledFor(logging.DEBUG):
                        app.logger.debug("filter_artists args=%s", args_dict_to_str(args))
                    break
        else:
            results.append(row)
    return pd.DataFrame(results)


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


def get_artists(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> List[str]:
    filtered = filter_artists(app, artists, args)
    return sorted({str(artist.name) for artist in filtered.itertuples()})


def get_artist(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> tuple[Any, ...] | None:
    """Return one artist row matching the requested filters."""
    filtered = filter_artists(app, artists, args)
    if not filtered.empty:
        return next(filtered.itertuples(name="artist", index=False))
    return None


def get_word_cloud_data_artists(
    app: Application, artists: pd.DataFrame, args: ArgsDict
) -> List[Dict[str, str]]:
    return [{"text": artist} for artist in get_artists(app, artists, args)]
