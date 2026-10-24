"""
Route kept for the web frontend (which lives in a separate repo):

- /getfile/<path>  serves media files and album covers from disk (mounted at the
                   site root, NOT under serverConfig.urlPrefix)

All server-rendered page routes were removed; the frontend
single-page application renders pages client-side using the JSON API in
app/api/routes.py.
"""

import mimetypes
import os
import re
from collections.abc import AsyncIterable
from pathlib import Path

from blacksheep import Application, Request, Response, StreamedContent
from blacksheep.common.files.asyncfs import FilesHandler
from blacksheep.exceptions import NotFound

from app.utils.app_utils import get_config


def register_routes(app: Application, url_prefix: str = "") -> None:
    @app.router.head(url_prefix + "/getfile/{path:path}")
    @app.router.get(url_prefix + "/getfile/{path:path}")
    async def getfile(request: Request, path: str) -> Response:
        config = get_config(app)

        # path_prefix = /var/www/html/Covers/
        # path = /var/www/html/Covers/MusicOther/Johnny Cash/With His Hot and Blue Guitar [1957]/cover.jpg
        # path_without_prefix = MusicOther/Johnny Cash/With His Hot and Blue Guitar [1957]/cover.jpg

        if not path.startswith("/"):
            path = "/" + path
        path_prefix = config.playback_methods.local.media_path
        if path.startswith(config.album_covers_path):
            path_prefix = config.album_covers_path

        if not Path(path).exists():
            # if it's a jpg, try looking for webp instead of jpg
            # in case someone (me) converted the original jpgs to webp
            root, ext = os.path.splitext(path)
            if ext != ".jpg":
                app.logger.error('File not found (and not a jpg): "%s"', path)
                raise NotFound()
            oldpath = path
            path = root + ".webp"
            app.logger.warning(
                "Couldn't find file, trying different file extension:\noldpath=%s\nnewpath=%s",
                oldpath,
                path,
            )
        if not Path(path).exists():
            app.logger.error('File not found: "%s"', path)
            raise NotFound()
        else:
            app.logger.debug("File exists: %s", path)

        if not path_prefix.endswith("/"):
            path_prefix = path_prefix + "/"
        if not path.startswith(path_prefix):
            app.logger.warning(
                "path (%s) doesn't match expected media path prefix (%s), refusing to serve it",
                path,
                path_prefix,
            )
            raise NotFound()

        app.logger.debug('/getfile/ serving file: "%s"', path)
        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        size = Path(path).stat().st_size
        headers = [
            (b"Accept-Ranges", b"bytes"),
            (b"Content-Disposition", b"attachment"),
        ]
        if request.method == "HEAD":
            return Response(
                200,
                headers + [
                    (b"Content-Type", content_type.encode()),
                    (b"Content-Length", str(size).encode()),
                ],
            )

        start, end = 0, size - 1
        status = 200
        range_header = request.get_first_header(b"Range")
        # No validators are emitted by this route, so If-Range cannot match.
        if range_header and request.get_first_header(b"If-Range") is None:
            match = re.fullmatch(
                rb"bytes=([0-9]*)-([0-9]*)", range_header.strip(), re.IGNORECASE
            )
            # Unsupported units, malformed ranges and multipart requests are ignored.
            if match and any(match.groups()):
                first, last = match.groups()
                try:
                    requested_start = int(first) if first else None
                    requested_end = int(last) if last else None
                except ValueError:
                    app.logger.debug("Ignoring Range header with excessive integer digits")
                else:
                    if requested_start is None:
                        assert requested_end is not None
                        start = max(0, size - requested_end)
                        status = 206
                    elif requested_end is None or requested_end >= requested_start:
                        start = requested_start
                        end = min(requested_end, size - 1) if requested_end is not None else size - 1
                        status = 206

                    if status == 206 and start > end:
                        app.logger.debug("Requested byte range is unsatisfiable for %s", path)
                        return Response(
                            416,
                            headers + [
                                (b"Content-Range", f"bytes */{size}".encode()),
                                (b"Content-Length", b"0"),
                            ],
                        )
                    if status == 206:
                        headers.append((b"Content-Range", f"bytes {start}-{end}/{size}".encode()))

        length = end - start + 1

        async def chunks() -> AsyncIterable[bytes]:
            async with FilesHandler().open(path) as source:
                await source.seek(start)
                remaining = length
                while remaining:
                    chunk = await source.read(min(64 * 1024, remaining))
                    if not chunk:
                        raise OSError(f"Unexpected end of file while streaming {path}")
                    remaining -= len(chunk)
                    yield chunk
            yield b""

        return Response(
            status, headers, StreamedContent(content_type.encode(), chunks, length)
        )
