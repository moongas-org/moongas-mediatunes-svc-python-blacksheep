import logging
import os
import sys
from pathlib import Path

import uvicorn
from blacksheep import Application

from app import create_app
from app.utils.config.mediatunes_svc_config_util import MediatunesServiceConfigUtil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mediatunes_svc")


def create_app_from_env() -> Application:
    """Application factory used by uvicorn when running with reload enabled.

    Reads the config file path from the MEDIATUNES_CONFIG environment variable.
    """
    config_filepath_str = os.environ.get("MEDIATUNES_CONFIG")
    config_filepath = Path(config_filepath_str) if config_filepath_str else None
    config = MediatunesServiceConfigUtil().load_config(config_filepath)
    return create_app(config)


def main():
    config_filepath = None
    if len(sys.argv) > 1:
        config_filepath = Path(sys.argv[1])
        logger.info("Loading configuration from file: %s", config_filepath)
    else:
        logger.warning("No config file specified, loading default configuration")

    try:
        config = MediatunesServiceConfigUtil().load_config(config_filepath)
    except Exception as ex:
        logger.error("Failed to load configuration from '%s': %s", config_filepath, ex)
        sys.exit(1)

    if config.server_config.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    try:
        app = create_app(config)
    except Exception as ex:
        logger.error("Failed to initialize mediatunes-svc application: %s", ex)
        sys.exit(1)

    if config_filepath is None:
        app.logger.warning(
            "No config file specified, running with default configuration"
        )
    else:
        app.logger.info("Loaded configuration from file: %s", config_filepath)

    server_config = config.server_config
    log_level = "debug" if server_config.debug else "info"

    try:
        if server_config.use_reloader:
            # uvicorn's reloader requires an import string (a new process
            # re-imports the module), so the config file path is passed to the
            # child process via the MEDIATUNES_CONFIG environment variable.
            if config_filepath is not None:
                os.environ["MEDIATUNES_CONFIG"] = str(config_filepath)
            uvicorn.run(
                "run:create_app_from_env",
                factory=True,
                reload=True,
                host=server_config.host,
                port=server_config.port,
                log_level=log_level,
            )
        else:
            uvicorn.run(
                app,
                host=server_config.host,
                port=server_config.port,
                log_level=log_level,
            )
    except Exception as ex:
        logger.error("Error while running mediatunes-svc: %s", ex)
        sys.exit(1)


if __name__ == "__main__":
    main()
