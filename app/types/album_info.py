from typing import Tuple
from pathlib import Path

# Tuple of [Artist, Album, Year, CoverPath, ExplicitCover]
AlbumInfoTuple = Tuple[str, str, int, str, bool]


class AlbumInfo:
    def __init__(
        self,
        artist: str,
        album: str,
        year: int,
        cover_path: Path,
        explicit_cover: bool,
    ):
        self.artist = artist
        self.album = album
        self.year = year
        self.cover_path = cover_path
        self.explicit_cover = explicit_cover

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AlbumInfo):
            return NotImplemented
        return (
            self.artist == other.artist
            and self.album == other.album
            and self.year == other.year
            and self.cover_path == other.cover_path
            and self.explicit_cover == other.explicit_cover
        )

    def __hash__(self):
        return hash(self.to_tuple())

    def to_tuple(self) -> AlbumInfoTuple:
        return (
            self.artist,
            self.album,
            self.year,
            str(self.cover_path),
            self.explicit_cover,
        )
