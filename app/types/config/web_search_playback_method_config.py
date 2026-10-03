from dataclasses import dataclass, field

from app.types.config.playback_method_config import PlaybackMethodConfig


@dataclass
class WebSearchPlaybackMethodConfig(PlaybackMethodConfig):
    name: str = field(default="YouTube")
    search_query_url_format: str = field(
        default="https://www.youtube.com/results?search_query=+{artist}+{album}+{title}+official+music+video"
    )
