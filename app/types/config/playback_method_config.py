from dataclasses import dataclass, field
from dataclass_wizard.v0 import YAMLWizard


@dataclass
class PlaybackMethodConfig(YAMLWizard):
    enabled: bool = field(default=True)
