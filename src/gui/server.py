"""HTTP layer for the DSDM Agents Console.

Deliberately built on `http.server` rather than a web framework: the console
must start with nothing installed beyond `requirements.txt`, on the same
machine as the CLI, for a single user.

That single-user, local assumption is enforced rather than assumed:

* the default bind address is loopback;
* the `Host` header is checked on every request, so a hostile page in the same
  browser cannot use DNS rebinding to drive the console;
* binding to a non-loopback address requires an access token, because at that
  point the console is reachable by other machines.
"""

from __future__ import annotations

import json
import mimetypes
import secrets
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from . import api

STATIC_DIR = Path(__file__).parent / "static"

LOOPBACK_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "[::1]", "0.0.0.0"}

MAX_BODY_BYTES = 1_000_000


def _is_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "::1", "localhost")


class ConsoleServer:
    """A running console instance."""

    def __init__(self, host: str, port: int, token: Optional[str] = None) -> None:
        self.host = host
        self.port = port
        self.token = token
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> "ConsoleServer":
        handler = _make_handler(self)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="dsdm-console", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    def serve_forever(self) -> None:
        if self._httpd is None:
            self.start()
        assert self._thread is not None
        while self._thread.is_alive():
            self._thread.join(0.5)

    # -- helpers ------------------------------------------------------------

    @property
    def url(self) -> str:
        host = "localhost" if self.host in ("0.0.0.0", "127.0.0.1", "::") else self.host
        base = f"http://{host}:{self.port}/"
        return f"{base}?token={self.token}" if self.token else base

    def host_allowed(self, host_header: str) -> bool:
        """Reject requests whose Host header is not one we bound to.

        Without this, a website the user visits could point a hostname it
        controls at 127.0.0.1 and issue authenticated requests to the console.
        """
        if not host_header:
            return False
        hostname = host_header.rsplit(":", 1)[0].strip().lower() if ":" in host_header else host_header.strip().lower()
        if hostname.startswith("[") and hostname.endswith("]"):
            hostname = hostname[1:-1]
        if hostname in LOOPBACK_HOSTNAMES:
            return True
        return hostname == self.host.lower()

    def token_valid(self, provided: Optional[str]) -> bool:
        if not self.token:
            return True
        return bool(provided) and secrets.compare_digest(provided, self.token)


def _guess_type(path: Path) -> str:
    kind, _ = mimetypes.guess_type(path.name)
    return kind or "application/octet-stream"


def _make_handler(server: ConsoleServer):
    class ConsoleRequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "DSDMConsole/1.0"

        # -- plumbing ---------------------------------------------------

        def log_message(self, fmt: str, *args: Any) -> None:
            """Silence per-request logging; the console is not a web service."""

        def _send(self, status: int, body: bytes, content_type: str, extra_headers: Optional[Dict[str, str]] = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
            self._send(status, api.encode(payload), "application/json; charset=utf-8", {"Cache-Control": "no-store"})

        def _read_body(self) -> Dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return {}
            if length <= 0:
                return {}
            if length > MAX_BODY_BYTES:
                raise ValueError("Request body is too large.")
            raw = self.rfile.read(length)
            if not raw:
                return {}
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Request body must be valid JSON.") from exc
            return parsed if isinstance(parsed, dict) else {}

        def _guard(self, query: Dict[str, str]) -> bool:
            """Common Host/token checks. Returns False when already answered."""
            if not server.host_allowed(self.headers.get("Host", "")):
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "Request blocked: unexpected Host header."})
                return False
            provided = self.headers.get("X-Console-Token") or query.get("token")
            if not server.token_valid(provided):
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "An access token is required."})
                return False
            return True

        @staticmethod
        def _parse(path: str) -> Tuple[str, Dict[str, str]]:
            parsed = urlparse(path)
            query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            return parsed.path, query

        # -- verbs ------------------------------------------------------

        def do_GET(self) -> None:
            path, query = self._parse(self.path)
            if not self._guard(query):
                return
            if path.startswith("/api/"):
                status, payload = api.dispatch("GET", path[len("/api/"):], query)
                self._send_json(status, payload)
                return
            self._serve_static(path)

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_POST(self) -> None:
            path, query = self._parse(self.path)
            if not self._guard(query):
                return
            if not path.startswith("/api/"):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            try:
                body = self._read_body()
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            status, payload = api.dispatch("POST", path[len("/api/"):], query, body)
            self._send_json(status, payload)

        # -- static -----------------------------------------------------

        def _serve_static(self, path: str) -> None:
            relative = "index.html" if path in ("", "/") else path.lstrip("/")
            target = (STATIC_DIR / relative).resolve()
            static_root = STATIC_DIR.resolve()
            if static_root not in target.parents and target != static_root:
                self._send(HTTPStatus.FORBIDDEN, b"Forbidden", "text/plain; charset=utf-8")
                return
            if not target.is_file():
                # Unknown paths fall back to the app shell so client-side
                # navigation survives a page reload.
                target = static_root / "index.html"
                if not target.is_file():
                    self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")
                    return
            self._send(
                HTTPStatus.OK,
                target.read_bytes(),
                _guess_type(target),
                {"Cache-Control": "no-cache"},
            )

    return ConsoleRequestHandler


def create_server(host: str = "127.0.0.1", port: int = 8770, token: Optional[str] = None) -> ConsoleServer:
    """Create (but do not start) a console server.

    A token is generated automatically when binding beyond loopback, since the
    console can then start real work on behalf of anyone who can reach it.
    """
    if token is None and not _is_loopback(host):
        token = secrets.token_urlsafe(24)
    return ConsoleServer(host=host, port=port, token=token)


def serve(
    host: str = "127.0.0.1",
    port: int = 8770,
    token: Optional[str] = None,
    open_browser: bool = True,
    printer=print,
) -> ConsoleServer:
    """Start the console and block until interrupted."""
    server = create_server(host=host, port=port, token=token)
    try:
        server.start()
    except OSError as exc:
        raise SystemExit(f"Could not start the console on {host}:{port} - {exc}") from exc

    printer(f"DSDM Agents Console is running at {server.url}")
    if server.token:
        printer("Access token required (the URL above already contains it).")
    printer("Press Ctrl+C to stop.")

    if open_browser:
        try:
            import webbrowser

            webbrowser.open(server.url)
        except Exception:  # pragma: no cover - headless machines have no browser
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        printer("\nStopping the console.")
    finally:
        server.stop()
    return server


def find_free_port(host: str = "127.0.0.1") -> int:
    """Return a free port - used when the requested one is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])
