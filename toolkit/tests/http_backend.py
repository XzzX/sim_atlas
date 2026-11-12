"""A minimal Sim Atlas backend served over a real socket.

``httpx2.MockTransport`` never opens connections, so it cannot show bugs in
connection handling (e.g. pooled connections bound to a closed event loop).
Tests that need real connections use this server instead.
"""

import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class _Handler(BaseHTTPRequestHandler):
    # Keep-alive, so the client pools connections between requests.
    protocol_version = "HTTP/1.1"
    nodes: dict[str, dict[str, Any]]

    def do_GET(self) -> None:
        node = self.nodes.get(self.path.rsplit("/", 1)[-1])
        if node is None:
            self._send(HTTPStatus.NOT_FOUND)
        else:
            self._send(HTTPStatus.OK, node)

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not self.path.endswith("/nodes"):
            self._send(HTTPStatus.SERVICE_UNAVAILABLE)
            return
        request = json.loads(body)
        node_id = request.get("id") or request["hash"]
        if node_id in self.nodes:
            self._send(HTTPStatus.CONFLICT, self.nodes[node_id])
            return
        node = {
            **request,
            "id": node_id,
            "creator_name": "test",
            "creator_email": "test@example.com",
            "creation_timestamp": "2026-01-01T00:00:00+00:00",
        }
        self.nodes[node_id] = node
        self._send(HTTPStatus.CREATED, node)

    def _send(self, status: HTTPStatus, body: Any = None) -> None:
        payload = b"" if body is None else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Silence per-request logging."""


@contextmanager
def http_backend() -> Generator[str]:
    """Serve an in-memory backend on localhost and yield its API URL.

    Supports ``GET /nodes/{id}`` and ``POST /nodes`` (201, or 409 for a known
    id); any other POST answers 503, i.e. embedding is not configured.
    """
    handler = type("Handler", (_Handler,), {"nodes": {}})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/api"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
