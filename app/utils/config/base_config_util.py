from abc import abstractmethod
from pathlib import Path
from typing import Optional, TextIO, TypeVar, Generic

T = TypeVar("T")


class BaseConfigUtil(Generic[T]):
    """
    Abstract base utility class for loading configuration from YAML config file"""

    yaml_filename = ""
    _yaml_resource_path = None

    def __init__(self, yaml_filename: str) -> None:
        self.yaml_filename = yaml_filename

    def load_config(self, path: Optional[Path] = None) -> T:
        """Loads and returns the configuration."""
        if path is not None:
            return self._load_config_yaml_filepath(path)
        else:
            return self._load_default_config()

    def _load_config_yaml_filepath(self, filepath: Path) -> T:
        with open(filepath, "r", encoding="utf-8") as f:
            return self._load_config_from_filestream(f)

    @abstractmethod
    def _load_config_from_filestream(self, filestream: TextIO) -> T:
        pass

    @abstractmethod
    def _load_default_config(self) -> T:
        pass
