from typing import cast
import logging
import os
from pathlib import Path

import pandas as pd
from blacksheep import Application
from rodi import Container
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.types.config.mediatunes_svc_config import MediatunesServiceConfig
from app.utils.app_utils import AppState

logger = logging.getLogger(__name__)


def register_routes(app: Application, url_prefix: str = "") -> None:
    from app.main.routes import register_routes as register_main_routes
    from app.api.routes import register_routes as register_api_routes

    # media files (/getfile/<path>) are served from the root, not under url_prefix
    register_main_routes(app, "")
    # the JSON API lives under the configured url_prefix (e.g. "/api")
    register_api_routes(app, url_prefix)


def create_app(config: MediatunesServiceConfig) -> Application:
    server_config = config.server_config
    url_prefix = server_config.url_prefix or ""
    static_url_path = server_config.static_url_path
    app = Application(show_error_details=server_config.debug)
    app.logger.debug("server_config.url_prefix: %s", url_prefix)
    app.logger.debug("server_config.static_url_path: %s", static_url_path)

    db_path = config.mediascan_database_file_path
    if not db_path:
        error_msg = (
            "No mediascan database file path configured in mediatunes-svc config."
        )
        app.logger.error(error_msg)
        raise ValueError(error_msg)

    # Validate SQLite database file path if applicable
    if db_path.startswith("sqlite:///"):
        sqlite_file_str = db_path[len("sqlite:///") :]
        if sqlite_file_str and sqlite_file_str != ":memory:":
            sqlite_path = Path(sqlite_file_str).expanduser()
            resolved_sqlite_path = sqlite_path.resolve()
            app.logger.info(
                "Configured SQLite database path: '%s' (resolved: '%s')",
                db_path,
                resolved_sqlite_path,
            )
            if not resolved_sqlite_path.exists():
                error_msg = (
                    f"SQLite database file not found at '{resolved_sqlite_path}' "
                    f"(from config: '{db_path}', current directory: '{os.getcwd()}'). "
                    "Please verify that the database path in your config is correct and that the database file exists."
                )
                app.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            if resolved_sqlite_path.stat().st_size == 0:
                error_msg = (
                    f"SQLite database file at '{resolved_sqlite_path}' is empty (0 bytes). "
                    "Please populate the database using mediascan before running mediatunes-svc."
                )
                app.logger.error(error_msg)
                raise ValueError(error_msg)
    else:
        app.logger.info("Configured database URL: '%s'", db_path)

    try:
        engine = create_engine(db_path)
    except Exception as ex:
        app.logger.error("Failed to create SQLAlchemy engine for '%s': %s", db_path, ex)
        raise

    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        app.logger.debug("Discovered database tables: %s", table_names)

        required_tables = ["mediafile", "artist"]
        missing_tables = [t for t in required_tables if t not in table_names]
        if missing_tables:
            error_msg = (
                f"Database '{db_path}' is missing required table(s): {missing_tables}. "
                f"Tables found in database: {table_names}. "
                "Please verify that this is a valid mediascan database."
            )
            app.logger.error(error_msg)
            raise ValueError(error_msg)
    except (SQLAlchemyError, ValueError):
        raise
    except Exception as ex:
        app.logger.error("Failed to inspect tables in database '%s': %s", db_path, ex)
        raise

    try:
        with engine.connect() as conn:
            app.logger.info("Loading 'mediafile' table from database...")
            files_df = pd.read_sql_query("SELECT * FROM mediafile", conn)

            app.logger.info("Loading 'artist' table from database...")
            artists_df = pd.read_sql_query("SELECT * FROM artist", conn)

            app.logger.info("Joining media files and artists...")
            joined_df = pd.read_sql_query(
                "SELECT * FROM mediafile LEFT JOIN artist ON mediafile.artistpath = artist.path",
                conn,
            )

            app.logger.info(
                "Successfully loaded %d media files and %d artists from database.",
                len(files_df),
                len(artists_df),
            )
    except SQLAlchemyError as ex:
        app.logger.error(
            "SQLAlchemy error executing queries on database '%s': %s",
            db_path,
            ex,
        )
        raise
    except Exception as ex:
        app.logger.error(
            "Unexpected error loading data from database '%s': %s", db_path, ex
        )
        raise

    static_folder = str(Path(__file__).parent / "static")
    # Application.services is typed as ContainerProtocol, whose stub lacks add_instance
    services = cast(Container, app.services)
    services.add_instance(  # pyright: ignore[reportUnknownMemberType] - rodi stub gap
        AppState(
            config=config,
            engine=engine,
            db_files=files_df,
            db_artists=artists_df,
            db_files_artists_joined=joined_df,
            static_folder=static_folder,
            logger=app.logger,
        )
    )

    register_routes(app, url_prefix)

    if static_url_path:
        app.serve_files(static_folder, root_path=static_url_path)

    return app
