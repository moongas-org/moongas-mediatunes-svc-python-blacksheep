"""Utilities for retrieving streaming links from the mediascan database."""

from typing import List

from blacksheep import Application
from mediascan.utils.db.trackstreaming.trackstreaming_data import (
    TrackStreamingData,
    row_to_trackstreaming_data,
)

from app.utils.app_utils import get_mediascan_db_trackstreaming


def get_trackstreaming(app: Application, track_id: int) -> List[TrackStreamingData]:
    """Return all streaming rows for a track, preserving their stored order."""
    trackstreaming = get_mediascan_db_trackstreaming(app)
    matching_trackstreaming = trackstreaming.loc[
        trackstreaming["trackid"] == track_id
    ]
    return [
        row_to_trackstreaming_data(row)
        for _, row in matching_trackstreaming.iterrows()
    ]
