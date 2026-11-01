"""Utilities for retrieving media files from the mediascan database."""

from typing import List

from blacksheep import Application
from mediascan.utils.db.mediafile.mediafile_data import (
    MediaFileData,
    row_to_mediafile_data,
)

from app.utils.app_utils import get_mediascan_db_mediafiles


def get_mediafiles(app: Application, track_id: int) -> List[MediaFileData]:
    """Return all media file rows for a track, preserving their stored order."""
    mediafiles = get_mediascan_db_mediafiles(app)
    matching_mediafiles = mediafiles.loc[mediafiles["trackid"] == track_id]
    return [
        row_to_mediafile_data(row)
        for _, row in matching_mediafiles.iterrows()
    ]
