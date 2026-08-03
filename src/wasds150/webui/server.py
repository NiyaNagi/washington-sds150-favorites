"""Local web UI server: stdlib ``http.server`` only, loopback-bound.

Serves the static SPA shell (``webui/static/``) with the per-run auth token
templated in, and the JSON API under ``/api/v1/`` via
:mod:`wasds150.webui.api`. No external web framework, no build step.
"""
from __future__ import annotations

import logging
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from wasds150.appctx import AppContext
from wasds150.webui import auth
from wasds150.webui.api import build_router
from wasds150.webui.router import RequestContext, Response, Router

logger = logging.getLogger("wasds150.webui")

STATIC_DIR = Path(__file__).parent / "static"

_STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def _make_handler_class(router: Router, token: str) -> type:
    class Handler(BaseHTTPRequestHandler):
        server_version = "wasds150/0.1"

        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            logger.info("%s - %s", self.address_string(), fmt % args)

        # -- shared dispatch -------------------------------------------------
        def _dispatch(self, method: str) -> None:
            split = urlsplit(self.path)
            path = split.path

            if path.startswith("/api/"):
                self._handle_api(method, path, split.query)
                return
            if method == "GET":
                self._handle_static(path)
                return
            self._send_response(Response.json(405, {"error": "method not allowed"}))

        def _handle_api(self, method: str, path: str, raw_query: str) -> None:
            if not auth.token_matches(token, self.headers):
                self._send_response(Response.json(401, {"error": "missing or invalid token"}))
                return

            match = router.resolve(method, path)
            if match is None:
                self._send_response(Response.json(404, {"error": f"no route for {method} {path}"}))
                return
            handler, params = match

            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else b""
            ctx = RequestContext(
                method=method,
                path=path,
                params=params,
                query=Router.parse_query(raw_query),
                body=body,
                headers=self.headers,
            )
            try:
                response = handler(ctx)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("API handler error")
                response = Response.json(500, {"error": str(exc)})
            self._send_response(response)

        def _handle_static(self, path: str) -> None:
            if path == "/":
                path = "/index.html"
            safe_name = Path(path).name
            file_path = STATIC_DIR / safe_name
            # Guard against path traversal; only ever serve a flat file
            # directly inside STATIC_DIR.
            if not file_path.is_file() or file_path.parent.resolve() != STATIC_DIR.resolve():
                self._send_response(Response(status=404, body=b"not found", content_type="text/plain"))
                return
            content = file_path.read_bytes()
            if file_path.suffix == ".html":
                content = content.replace(b"__WASDS150_TOKEN__", token.encode("ascii"))
            content_type = _STATIC_CONTENT_TYPES.get(file_path.suffix, "application/octet-stream")
            self._send_response(Response(status=200, body=content, content_type=content_type))

        def _send_response(self, response: Response) -> None:
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.end_headers()
            if response.body:
                self.wfile.write(response.body)

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_DELETE(self) -> None:  # noqa: N802
            self._dispatch("DELETE")

    return Handler


def build_server(ctx: AppContext, port: int = 0, host: str = "127.0.0.1"):
    router = build_router(ctx)
    token = auth.generate_token()
    handler_class = _make_handler_class(router, token)
    server = ThreadingHTTPServer((host, port), handler_class)
    return server, token


def run_server(ctx: AppContext, port: int = 0, open_browser: bool = True) -> int:
    server, token = build_server(ctx, port=port)
    host, actual_port = server.server_address[0], server.server_address[1]
    url = f"http://{host}:{actual_port}/"

    print(f"wasds150 web UI listening on {url}")
    print(f"(auth token: {token} — already embedded in the served page)")
    print("Press Ctrl+C to stop.")

    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
