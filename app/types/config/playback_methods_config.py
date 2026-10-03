from dataclasses import dataclass, field
from typing import List
from dataclass_wizard.v0 import YAMLWizard

from app.types.config.local_playback_method_config import LocalPlaybackMethodConfig
from app.types.config.web_search_playback_method_config import (
    WebSearchPlaybackMethodConfig,
)


@dataclass
class PlaybackMethodsConfig(YAMLWizard):
    local: LocalPlaybackMethodConfig = field(default_factory=LocalPlaybackMethodConfig)
    webSearch: List[WebSearchPlaybackMethodConfig] = field(
        default_factory=list[WebSearchPlaybackMethodConfig]
    )
