from typing import Tuple
from pathlib import Path

# Tuple of [Artist, Album, Year, CoverPath]
AlbumInfoTuple = Tuple[str, str, int, str]


class AlbumInfo:
    def __init__(self, artist: str, album: str, year: int, cover_path: Path):
        self.artist = artist
        self.album = album
        self.year = year
        self.cover_path = cover_path

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AlbumInfo):
            return NotImplemented
        return (
            self.artist == other.artist
            and self.album == other.album
            and self.year == other.year
            and self.cover_path == other.cover_path
        )

    def __hash__(self):
        return hash(self.to_tuple())

    def to_tuple(self) -> AlbumInfoTuple:
        return (self.artist, self.album, self.year, str(self.cover_path))
