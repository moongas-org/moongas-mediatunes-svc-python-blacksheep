from typing import Optional

from dataclasses import dataclass, field
from dataclass_wizard.v0 import YAMLWizard


@dataclass
class ServerConfig(YAMLWizard):
    host: str = field(default="0.0.0.0")
    port: int = field(default=5000)
    static_url_path: Optional[str] = field(default=None)
    url_prefix: Optional[str] = field(default=None)
    debug: bool = field(default=True)
    use_reloader: bool = field(default=True)
