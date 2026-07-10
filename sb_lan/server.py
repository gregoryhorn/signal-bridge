"""Background stdlib HTTP server for LAN phone viewer (SSE + static web_lan)."""

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from sb_lan.config import LanConfig
from sb_lan.feed_buffer import FeedBuffer
from sb_lan.security import check_token, safe_static_path
from sb_lan.theme_css import theme_to_css_variables


def discover_lan_ip() -> str:
    """Best-effort LAN IPv4 for QR/URL display (not 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


class LanServer:
    def __init__(self, web_root: Path | None = None):
        self._web_root = Path(web_root) if web_root else self._default_web_root()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._config = LanConfig()
        self._buffer = FeedBuffer()
        self._theme: dict = {}
        self._clients_lock = threading.Lock()
        self._sse_queues: list[queue.Queue] = []

    @staticmethod
    def _default_web_root() -> Path:
        # Prefer package-adjacent web_lan/, then app root.
        here = Path(__file__).resolve().parent.parent
        return here / "web_lan"

    @property
    def web_root(self) -> Path:
        return self._web_root

    def start(self, config: LanConfig, buffer: FeedBuffer | None = None, theme: dict | None = None) -> str:
        self.stop()
        self._config = config
        if buffer is not None:
            self._buffer = buffer
        if theme is not None:
            self._theme = theme
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def _token(self) -> str | None:
                qs = parse_qs(urlparse(self.path).query)
                vals = qs.get("token") or []
                return vals[0] if vals else self.headers.get("X-SB-Token")

            def _unauthorized(self):
                self.send_response(401)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"unauthorized")

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path or "/"
                if path.startswith("/api/"):
                    if not check_token(server._config, self._token()):
                        self._unauthorized()
                        return
                    if path == "/api/snapshot":
                        body = json.dumps(
                            {
                                "rows": server._buffer.snapshot(),
                                "theme": server._theme,
                                "seq": server._buffer.seq,
                            }
                        ).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    if path == "/api/stream":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.send_header("Connection", "keep-alive")
                        self.end_headers()
                        q: queue.Queue = queue.Queue(maxsize=200)
                        with server._clients_lock:
                            server._sse_queues.append(q)
                        try:
                            self.wfile.write(b"event: hello\ndata: {}\n\n")
                            self.wfile.flush()
                            while server._httpd is not None:
                                try:
                                    row = q.get(timeout=0.5)
                                except queue.Empty:
                                    # keepalive comment
                                    try:
                                        self.wfile.write(b": ping\n\n")
                                        self.wfile.flush()
                                    except Exception:
                                        break
                                    continue
                                data = json.dumps(row, ensure_ascii=False)
                                self.wfile.write(f"event: row\ndata: {data}\n\n".encode("utf-8"))
                                self.wfile.flush()
                        except Exception:
                            pass
                        finally:
                            with server._clients_lock:
                                if q in server._sse_queues:
                                    server._sse_queues.remove(q)
                        return
                    if path == "/api/theme.css":
                        css = theme_to_css_variables(server._theme).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "text/css; charset=utf-8")
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Content-Length", str(len(css)))
                        self.end_headers()
                        self.wfile.write(css)
                        return
                    self.send_response(404)
                    self.end_headers()
                    return

                # Static shell (html/css/js) is public; feed APIs require token.
                # Page is still useless without ?token= for snapshot/stream.
                file_path = safe_static_path(server._web_root, path)
                if not file_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                data = file_path.read_bytes()
                ctype = "text/plain; charset=utf-8"
                if file_path.suffix == ".html":
                    ctype = "text/html; charset=utf-8"
                elif file_path.suffix == ".js":
                    ctype = "application/javascript; charset=utf-8"
                elif file_path.suffix == ".css":
                    ctype = "text/css; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        httpd = ThreadingHTTPServer((config.host, int(config.port)), Handler)
        httpd.daemon_threads = True
        self._httpd = httpd
        t = threading.Thread(target=httpd.serve_forever, name="sb-lan-server", daemon=True)
        self._thread = t
        t.start()
        return self.public_url()

    def public_url(self) -> str:
        ip = discover_lan_ip()
        port = self._config.port
        token = self._config.token
        return f"http://{ip}:{port}/?token={token}"

    def stop(self) -> None:
        httpd = self._httpd
        self._httpd = None
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                pass
            try:
                httpd.server_close()
            except Exception:
                pass
        with self._clients_lock:
            self._sse_queues.clear()
        self._thread = None

    def client_count(self) -> int:
        with self._clients_lock:
            return len(self._sse_queues)

    def publish(self, row: dict) -> None:
        payload = self._buffer.append(row)
        with self._clients_lock:
            queues = list(self._sse_queues)
        for q in queues:
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass

    def set_theme(self, theme: dict) -> None:
        self._theme = theme or {}

    @property
    def config(self) -> LanConfig:
        return self._config

    @property
    def buffer(self) -> FeedBuffer:
        return self._buffer
