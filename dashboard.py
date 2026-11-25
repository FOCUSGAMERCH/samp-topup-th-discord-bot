"""Read-only dashboard served to this computer only."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import database


DASHBOARD_FILE = Path(__file__).resolve().parent / "dashboard" / "index.html"
_server: ThreadingHTTPServer | None = None


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "LocalTopupDashboard"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._send_html()
        elif path == "/api/summary":
            self._send_summary()
        else:
            self.send_error(404)

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send_html(self) -> None:
        try:
            page = DASHBOARD_FILE.read_bytes()
        except OSError:
            self.send_error(500, "Dashboard page is missing")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(page)

    def _send_summary(self) -> None:
        try:
            payload = json.dumps(
                database.get_topup_summary(),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except Exception:
            payload = json.dumps(
                {"error": "เชื่อมต่อฐานข้อมูลไม่สำเร็จ"}, ensure_ascii=False
            ).encode("utf-8")
            self.send_response(503)
        else:
            self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


class LocalDashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_dashboard(port: int = 8765) -> str:
    """Start the dashboard once and return its loopback URL."""
    global _server
    if _server is None:
        _server = LocalDashboardServer(("127.0.0.1", int(port)), DashboardHandler)
        thread = threading.Thread(
            target=_server.serve_forever,
            name="topup-dashboard",
            daemon=True,
        )
        thread.start()
    return f"http://127.0.0.1:{_server.server_port}"
