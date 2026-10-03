from dataclasses import dataclass, field

from app.types.config.playback_method_config import PlaybackMethodConfig


@dataclass
class LocalPlaybackMethodConfig(PlaybackMethodConfig):
    # !!! Important security note !!!
    # Do not expose more than you need to with the music lib path below,
    # Every file under this path will be exposed by the server!
    # See the /getfile/ route.
    # TODO: Support multiple specific paths e.g. /data/Music and /data/MusicOther
    media_path: str = field(default="/data/")
