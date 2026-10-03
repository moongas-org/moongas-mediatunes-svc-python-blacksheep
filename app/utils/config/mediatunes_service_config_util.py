from typing import TextIO

from app.utils.config.base_config_util import BaseConfigUtil
from app.types.config.mediatunes_svc_config import MediatunesServiceConfig


class MediatunesServiceConfigUtil(BaseConfigUtil[MediatunesServiceConfig]):
    """
    Utility class for loading mediatunes-svc configuration from YAML config file
    """

    yaml_filename = "mediatunes-config.yml"
    _yaml_resource_path = None

    def __init__(self) -> None:
        super().__init__(self.yaml_filename)

    def _load_config_from_filestream(
        self, filestream: TextIO
    ) -> MediatunesServiceConfig:
        ret = MediatunesServiceConfig()
        data = MediatunesServiceConfig.from_yaml(filestream)  # type: ignore
        if isinstance(data, list):
            ret = data[0]
        else:
            ret = data
        return ret

    def _load_default_config(self) -> MediatunesServiceConfig:
        return MediatunesServiceConfig()
