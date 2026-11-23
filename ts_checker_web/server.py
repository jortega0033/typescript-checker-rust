"""Local-only HTTP server (127.0.0.1) for the checker UI and JSON API."""

import json
import os
import re
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .checker import CheckerError, CheckerRunner

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(PACKAGE_DIR, "static")  # tests may patch this

BIND_HOST = "127.0.0.1"
SOCKET_TIMEOUT = 10
MAX_BODY_BYTES = 262144
MAX_SOURCE_BYTES = 65536
DRAIN_LIMIT = 1024 * 1024

# Exact allowlist: URL path -> (file name inside STATIC_DIR, content type).
# File names are constants; nothing from the request is ever joined to a path.
STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/tokens.css": ("tokens.css", "text/css; charset=utf-8"),
    "/static/app.css": ("app.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/fixtures.json": ("fixtures.json", "application/json; charset=utf-8"),
}

# Path -> the single allowed method.
ROUTES = {path: "GET" for path in STATIC_ROUTES}
ROUTES["/api/v1/health"] = "GET"
ROUTES["/api/v1/check"] = "POST"

SECURITY_HEADERS = (
    ("Cache-Control", "no-store"),
    ("X-Content-Type-Options", "nosniff"),
    (
        "Content-Security-Policy",
        "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    ),
    ("Referrer-Policy", "no-referrer"),
)

# Used by send_error() so protocol-level failures also produce JSON.
HTTP_ERROR_CODES = {
    400: "invalid_request",
    404: "not_found",
    405: "method_not_allowed",
    408: "request_timeout",
    411: "length_required",
    413: "too_large",
    414: "invalid_request",
    431: "invalid_request",
    501: "method_not_allowed",
    505: "invalid_request",
}


def prepare_data_dir(data_dir):
    """Validate/create the data dir. Writes nothing into it. Raises ValueError."""
    if not isinstance(data_dir, str) or not data_dir.strip():
        raise ValueError("--data-dir must not be empty")
    try:
        if os.path.exists(data_dir):
            if not os.path.isdir(data_dir):
                raise ValueError("data dir exists but is not a directory")
        else:
            os.makedirs(data_dir, exist_ok=True)
    except OSError as exc:
        raise ValueError("cannot use data dir: %s" % (exc.strerror or "error"))
    return data_dir


def _no_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _reject_constant(name):
    raise ValueError("non-standard JSON constant")


class CheckerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR would let another process share the port.
    allow_reuse_address = False

    def __init__(self, address, handler, runner, data_dir):
        self.runner = runner
        self.data_dir = data_dir
        super().__init__(address, handler)

    def handle_error(self, request, client_address):
        # Dropped/timed-out connections are routine for a local server.
        import sys

        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    server_version = "ts-checker-web"
    sys_version = ""
    protocol_version = "HTTP/1.0"  # one request per connection
    timeout = SOCKET_TIMEOUT

    def log_message(self, format, *args):
        pass

    def finish(self):
        try:
            super().finish()
            if getattr(self, "command", None) == "POST" and getattr(self, "_body", None) is None:
                self._linger()
        except OSError:
            pass

    def _linger(self):
        """The body was not (fully) consumed. Close our sending side and drain
        briefly so the client can read our response instead of seeing a reset."""
        try:
            self.connection.shutdown(socket.SHUT_WR)
            self.connection.settimeout(0.5)
            total = 0
            while total < DRAIN_LIMIT:
                chunk = self.connection.recv(65536)
                if not chunk:
                    break
                total += len(chunk)
        except OSError:
            pass

    # ---- response helpers ----

    def _send(self, status, body, content_type, extra_headers=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status, payload, extra_headers=()):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", extra_headers)

    def _error(self, status, code, message, extra_headers=()):
        self._send_json(status, {"error": {"code": code, "message": message}}, extra_headers)

    def send_error(self, code, message=None, explain=None):
        self._error(code, HTTP_ERROR_CODES.get(code, "invalid_request"), "Request could not be processed.")

    # ---- request checks ----

    def _port(self):
        return self.server.server_address[1]

    def _host_ok(self):
        host = self.headers.get("Host")
        if host is None:
            return False
        port = self._port()
        return host.lower() in ("127.0.0.1:%d" % port, "localhost:%d" % port)

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        port = self._port()
        return origin in ("http://127.0.0.1:%d" % port, "http://localhost:%d" % port)

    # ---- dispatch ----

    def _prefetch_body(self):
        """Consume a POST body before any response is sent.

        Replying without reading the body can make the client see a reset
        instead of our error response. Oversized bodies are drained only up
        to DRAIN_LIMIT; beyond that the connection is simply closed.
        """
        self._length_headers = self.headers.get_all("Content-Length") or []
        self._chunked = self.headers.get("Transfer-Encoding") is not None
        self._body = None
        if self._chunked or len(self._length_headers) != 1:
            return
        raw = self._length_headers[0].strip()
        if not re.fullmatch(r"[0-9]{1,10}", raw):
            return
        length = int(raw)
        try:
            if length <= MAX_BODY_BYTES:
                self._body = self.rfile.read(length)
            elif length <= DRAIN_LIMIT:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
        except (TimeoutError, OSError):
            self._body = None
            self.close_connection = True

    def _dispatch(self, method):
        self._length_headers = []
        self._chunked = False
        self._body = None
        if method == "POST":
            self._prefetch_body()
        if not self._host_ok():
            self.close_connection = True
            return self._error(403, "forbidden_origin", "Host not allowed.")
        # Apply the allowlist before duplicative leading slashes are normalized.
        path = self.requestline.split(maxsplit=2)[1].split("?", 1)[0]
        allow = ROUTES.get(path)
        if method == "OPTIONS":
            return self._error(405, "method_not_allowed", "Method not allowed.", [("Allow", allow or "GET, POST")])
        if allow is None:
            return self._error(404, "not_found", "Not found.")
        if method != allow:
            return self._error(405, "method_not_allowed", "Method not allowed.", [("Allow", allow)])
        if path in STATIC_ROUTES:
            return self._serve_static(path)
        if path == "/api/v1/health":
            return self._health()
        return self._check()

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_OPTIONS(self):
        self._dispatch("OPTIONS")

    # ---- handlers ----

    def _serve_static(self, path):
        name, content_type = STATIC_ROUTES[path]
        try:
            with open(os.path.join(STATIC_DIR, name), "rb") as handle:
                body = handle.read()
        except OSError:
            return self._error(404, "not_found", "Not found.")
        self._send(200, body, content_type)

    def _health(self):
        self._send_json(
            200,
            {
                "status": "ok",
                "schema_version": 1,
                "checker": {"available": self.server.runner.available()},
            },
        )

    def _read_source(self):
        """Validate the request and return the source string, or None if an
        error response was already sent."""
        if not self._origin_ok():
            self._error(403, "forbidden_origin", "Origin not allowed.")
            return None

        content_type = self.headers.get("Content-Type", "")
        if content_type.split(";", 1)[0].strip().lower() != "application/json":
            self._error(415, "unsupported_media_type", "Content-Type must be application/json.")
            return None

        lengths = self._length_headers
        if self._chunked or not lengths:
            self._error(411, "length_required", "Content-Length is required.")
            return None
        if len(lengths) > 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0].strip()):
            self._error(400, "invalid_request", "Invalid Content-Length.")
            return None
        length = int(lengths[0].strip())
        if length > MAX_BODY_BYTES:
            self._error(413, "too_large", "Request body is too large.")
            return None
        if self._body is None:  # read failed or timed out; just drop the connection
            self.close_connection = True
            return None
        body = self._body
        if len(body) != length:
            self._error(400, "invalid_request", "Incomplete request body.")
            return None

        try:
            payload = json.loads(
                body.decode("utf-8"),
                object_pairs_hook=_no_duplicate_keys,
                parse_constant=_reject_constant,
            )
        except (ValueError, RecursionError):
            self._error(400, "invalid_request", "Body must be valid JSON.")
            return None
        if not isinstance(payload, dict) or set(payload) != {"source"} or not isinstance(payload["source"], str):
            self._error(400, "invalid_request", 'Body must be {"source": "<string>"}.')
            return None
        source = payload["source"]
        try:
            size = len(source.encode("utf-8"))
        except UnicodeEncodeError:  # lone surrogate from a \ud800 escape
            self._error(400, "invalid_request", "Source is not valid text.")
            return None
        if size > MAX_SOURCE_BYTES:
            self._error(413, "too_large", "Source is too large.")
            return None
        return source

    def _check(self):
        source = self._read_source()
        if source is None:
            return
        try:
            result = self.server.runner.run_check(source)
        except CheckerError as exc:
            return self._error(exc.status, exc.code, exc.message)
        except Exception:
            return self._error(502, "checker_failed", "The checker failed.")
        self._send_json(200, result)


def create_server(data_dir, port, checker_path=None, runner=None):
    """Build (but do not start) the server bound to 127.0.0.1:<port>.

    Raises ValueError for a bad data dir or port. `runner` is a
    CheckerRunner override for tests.
    """
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer 0..65535")
    prepare_data_dir(data_dir)
    if runner is None:
        runner = CheckerRunner(checker_path)
    return CheckerHTTPServer((BIND_HOST, port), Handler, runner, data_dir)
