"""
JSON API routes consumed by the mediatunes-svc web frontend.

The frontend single-page application lives in a separate repo; these
endpoints expose the media library data as JSON so it can render pages
client-side. They reuse the filtering/counting logic in
app/utils/media_files_utils.py.
"""

import random
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, cast

from blacksheep import Application, Request, Response, json
from blacksheep.exceptions import NotFound

from app.types.arg_types import args_dict_to_str
from app.utils.app_utils import (
    get_config,
    get_mediascan_db_artists,
    get_mediascan_db_files_artists_joined,
)
from app.utils.media_files_utils import (
    MediaFile,
    get_albums,
    get_artist,
    get_artist_counts,
    get_country_code_name_map,
    get_cover_path,
    get_files_list,
    get_genre_counts,
    get_language_code_name_map,
    get_region_code_name_map,
    get_tracks,
    get_word_cloud_data_artists,
    get_word_cloud_data_genres,
)
from app.utils.request_args_utils import get_request_args


class ArtistRow(NamedTuple):
    """
    Typed view of an artist row, as returned by get_artist()
    (a pandas namedtuple built from the 'artist' table).
    """

    name: Any
    countrycode: Any
    regioncode: Any
    city: Any
    languagecode: Any


def _artist_geo_counts(app: Application, kind: str) -> List[Dict[str, Any]]:
    """
    Count artists by a geo attribute and return user-facing names plus the
    filter criteria (so the client can build its own router links).
    """
    artists_df = get_mediascan_db_artists(app)

    country_map = get_country_code_name_map(app)
    region_map = get_region_code_name_map(app)
    language_map = get_language_code_name_map(app)

    # uniq_key -> [display_value, criteria_dict, count]
    counts: Dict[str, List[Any]] = {}
    name = ""
    for row in artists_df.itertuples():
        cc = str(row.countrycode)
        rc = str(row.regioncode)
        city = str(row.city)
        lc = str(row.languagecode)
        criteria: Dict[str, str] = {}
        if kind == "countries":
            name = "Country"
            if cc not in country_map:
                app.logger.error("Failed to find name for countrycode=%s", cc)
                continue
            value = country_map[cc]
            criteria = {"countryCode": cc}
        elif kind == "regions":
            name = "Region"
            if rc not in region_map:
                app.logger.error("Failed to find name for regioncode=%s", rc)
                continue
            value = region_map[rc]
            criteria = {"regionCode": rc}
        elif kind == "languages":
            name = "Language"
            if lc not in language_map:
                app.logger.error("Failed to find name for languagecode=%s", lc)
                continue
            value = language_map[lc]
            criteria = {"languageCode": lc}
        elif kind == "cities":
            name = "City"
            qualifiers: List[str] = []
            if rc in region_map:
                qualifiers.append(region_map[rc])
            if cc in country_map:
                qualifiers.append(country_map[cc])
            value = city
            if len(qualifiers):
                value = f"{city} ({', '.join(qualifiers)})"
            criteria = {"city": city, "regionCode": rc, "countryCode": cc}
        else:
            raise NotFound()

        uniq_key = f"{value}|{sorted(criteria.items())}"
        if uniq_key in counts:
            counts[uniq_key][2] += 1
        else:
            counts[uniq_key] = [value, criteria, 1]

    # default sort: by count (descending)
    items = sorted(counts.values(), key=lambda item: item[2], reverse=True)
    return [
        {"name": name, "value": value, "criteria": criteria, "count": count}
        for value, criteria, count in items
    ]


def register_routes(app: Application, url_prefix: str = "") -> None:
    # url_prefix is used verbatim (from serverConfig.urlPrefix); to serve the
    # API under /api, set urlPrefix: /api in the config — it is NOT appended here.
    @app.router.get(url_prefix + "/config")
    async def api_config() -> Response:
        """Client-facing configuration (playback methods, limits, feature flags)."""
        cfg = get_config(app)
        return json(
            {
                "playbackMethodLocalEnabled": cfg.playback_methods.local.enabled,
                "webSearchPlaybackMethods": [
                    {"name": m.name, "searchQueryUrlFormat": m.search_query_url_format}
                    for m in cfg.playback_methods.webSearch
                    if m.enabled
                ],
                "ageVerification": cfg.age_verification,
                "limitBandwidth": cfg.limit_bandwidth,
                "maxResults": cfg.max_results,
                "maxResultsAlbumCovers": cfg.max_results_album_covers,
                "presentYear": datetime.now().year,
            }
        )

    @app.router.get(url_prefix + "/albums")
    async def albums(request: Request) -> Response:
        args = get_request_args(request)
        app.logger.debug("api/albums args=%s", args_dict_to_str(args))
        album_list = get_albums(
            app,
            get_mediascan_db_files_artists_joined(app),
            get_mediascan_db_artists(app),
            args,
        )
        return json(
            {
                "albums": [
                    {
                        "artist": album.artist,
                        "album": album.album,
                        "year": album.year,
                        "coverPath": str(album.cover_path),
                    }
                    for album in album_list
                ]
            }
        )

    @app.router.get(url_prefix + "/tracks")
    async def tracks(request: Request) -> Response:
        args = get_request_args(request)
        app.logger.debug("api/tracks args=%s", args_dict_to_str(args))
        track_list: List[MediaFile] = get_tracks(
            app,
            get_mediascan_db_files_artists_joined(app),
            get_mediascan_db_artists(app),
            args,
        )
        cover_path: Path = Path()
        if len(track_list):
            cover_path = get_cover_path(get_config(app), track_list[0])
        return json(
            {
                "files": [asdict(t) for t in track_list],
                "coverPath": str(cover_path),
            }
        )

    @app.router.get(url_prefix + "/artists")
    async def artists(request: Request) -> Response:
        args = get_request_args(request)
        app.logger.debug("api/artists args=%s", args_dict_to_str(args))
        artist_counts = get_artist_counts(
            app,
            get_mediascan_db_files_artists_joined(app),
            get_mediascan_db_artists(app),
            args,
        )
        return json(
            {
                "artists": [
                    {"name": name, "count": count}
                    for name, count in artist_counts.items()
                ]
            }
        )

    @app.router.get(url_prefix + "/artist")
    async def artist(request: Request) -> Response:
        args = get_request_args(request)
        app.logger.debug("api/artist args=%s", args_dict_to_str(args))
        result = cast(
            ArtistRow | None,
            get_artist(
                app,
                get_mediascan_db_files_artists_joined(app),
                get_mediascan_db_artists(app),
                args,
            ),
        )
        if result is None:
            app.logger.error("Artist not found for request arguments: %s", args)
            raise NotFound()
        return json(
            {
                "artist": {
                    "name": str(result.name),
                    "countryCode": str(result.countrycode),
                    "regionCode": str(result.regioncode),
                    "city": str(result.city),
                    "languageCode": str(result.languagecode),
                }
            }
        )

    @app.router.get(url_prefix + "/genres")
    async def genres(request: Request) -> Response:
        sort: str = ""
        values = request.query.get("sort")
        if values:
            sort = values[0]
        genre_counts = get_genre_counts(
            get_mediascan_db_files_artists_joined(app), sort=sort
        )
        return json(
            {
                "genres": [
                    {"genre": genre, "count": count}
                    for genre, count in genre_counts.items()
                ]
            }
        )

    @app.router.get(url_prefix + "/artist-geo/{kind}")
    async def artist_geo(kind: str) -> Response:
        """kind is one of: countries, regions, cities, languages"""
        if kind not in ("countries", "regions", "cities", "languages"):
            raise NotFound()
        return json({"items": _artist_geo_counts(app, kind)})

    @app.router.get(url_prefix + "/wordcloud/genres")
    async def wordcloud_genres() -> Response:
        return json(
            {
                "words": get_word_cloud_data_genres(
                    get_mediascan_db_files_artists_joined(app)
                )
            }
        )

    @app.router.get(url_prefix + "/wordcloud/artists")
    async def wordcloud_artists(request: Request) -> Response:
        return json(
            {
                "words": get_word_cloud_data_artists(
                    app,
                    get_mediascan_db_files_artists_joined(app),
                    get_mediascan_db_artists(app),
                    get_request_args(request),
                )
            }
        )

    @app.router.get(url_prefix + "/random-track")
    async def random_track(request: Request) -> Response:
        """
        Same behavior as main.api_track (/api/track on the main router):
        returns a single random track matching the filter args.
        """
        cfg = get_config(app)
        args = get_request_args(request)
        app.logger.debug("api/random-track args=%s", args_dict_to_str(args))
        files_list: List[MediaFile] = get_files_list(
            app,
            get_mediascan_db_files_artists_joined(app),
            get_mediascan_db_artists(app),
            args,
        )
        if not len(files_list):
            raise NotFound()
        media_file = random.choice(files_list)
        cover_path = get_cover_path(cfg, media_file)
        return json(
            {
                "path": media_file.path,
                "coverPath": str(cover_path),
                "artist": media_file.artist,
                "album": media_file.album,
                "title": media_file.title,
                "genre": media_file.genre,
                "year": media_file.year,
                "countryCode": media_file.countryCode,
                "regionCode": media_file.regionCode,
                "city": media_file.city,
                "languageCode": media_file.languageCode,
            }
        )
