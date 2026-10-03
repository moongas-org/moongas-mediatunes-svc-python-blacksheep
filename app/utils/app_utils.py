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
    db_files: pd.DataFrame
    db_artists: pd.DataFrame
    db_files_artists_joined: pd.DataFrame
    static_folder: str
    logger: logging.Logger


def get_state(app: Application) -> AppState:
    # rodi stub gap: ContainerProtocol.resolve's type is partially unknown
    return app.services.resolve(AppState)  # pyright: ignore[reportUnknownMemberType]


def get_config(app: Application) -> MediatunesServiceConfig:
    return get_state(app).config


def get_mediascan_db_files(app: Application) -> pd.DataFrame:
    return get_state(app).db_files


def get_mediascan_db_artists(app: Application) -> pd.DataFrame:
    return get_state(app).db_artists


def get_mediascan_db_files_artists_joined(app: Application) -> pd.DataFrame:
    return get_state(app).db_files_artists_joined
