import logging
from dataclasses import dataclass

import pandas as pd
import sqlalchemy as sa
from blacksheep import Application

from app.types.config.mediatunes_svc_config import MediatunesServiceConfig


@dataclass
class AppState:
    """Application-scoped state, registered in the BlackSheep services container."""

    config: MediatunesServiceConfig
    engine: sa.Engine
    db_tracks: pd.DataFrame
    db_artists: pd.DataFrame
    db_albums: pd.DataFrame
    db_mediafiles: pd.DataFrame
    db_tracks_album_artist_joined: pd.DataFrame
    static_folder: str
    logger: logging.Logger


def get_state(app: Application) -> AppState:
    # rodi stub gap: ContainerProtocol.resolve's type is partially unknown
    return app.services.resolve(AppState)  # pyright: ignore[reportUnknownMemberType]


def get_config(app: Application) -> MediatunesServiceConfig:
    return get_state(app).config


def get_mediascan_db_tracks(app: Application) -> pd.DataFrame:
    return get_state(app).db_tracks


def get_mediascan_db_artists(app: Application) -> pd.DataFrame:
    return get_state(app).db_artists


def get_mediascan_db_albums(app: Application) -> pd.DataFrame:
    """Return album metadata enriched with related track and artist filter fields."""
    return get_state(app).db_albums


def get_mediascan_db_mediafiles(app: Application) -> pd.DataFrame:
    return get_state(app).db_mediafiles


def get_mediascan_db_tracks_album_artist_joined(app: Application) -> pd.DataFrame:
    return get_state(app).db_tracks_album_artist_joined
