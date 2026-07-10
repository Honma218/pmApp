import asyncio
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from teamdev_test_runner.ready_check import wait_until_ready
from teamdev_test_runner.runtime_config import RuntimeConfig


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"nope")

    def log_message(self, *a):  # stdout を汚さない
        pass


@pytest.fixture
def http_server():
    port = _free_port()
    srv = HTTPServer(("localhost", port), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield port
    srv.shutdown()


def _cfg(port, ready_check, timeout=3000):
    return RuntimeConfig.model_validate(
        {
            "bootCommand": "x",
            "entryUrl": f"http://localhost:{port}",
            "port": port,
            "bootTimeoutMs": timeout,
            "readyCheck": ready_check,
        }
    )


async def test_http_200(http_server):
    assert await wait_until_ready(_cfg(http_server, {"type": "http_200", "path": "/health"}))


async def test_http_200_はパスが違えば_ready_にならない(http_server):
    cfg = _cfg(http_server, {"type": "http_200", "path": "/missing"}, timeout=1000)
    assert not await wait_until_ready(cfg)


async def test_http_status(http_server):
    cfg = _cfg(http_server, {"type": "http_status", "path": "/missing", "expectStatus": 404})
    assert await wait_until_ready(cfg)


async def test_text_in_response(http_server):
    cfg = _cfg(http_server, {"type": "text_in_response", "path": "/health", "contains": "ok"})
    assert await wait_until_ready(cfg)


async def test_tcp_listen(http_server):
    assert await wait_until_ready(_cfg(http_server, {"type": "tcp_listen"}))


async def test_tcp_listen_は誰もいなければ_false():
    cfg = _cfg(_free_port(), {"type": "tcp_listen"}, timeout=1000)
    assert not await wait_until_ready(cfg)


async def test_プロセスが死んだら待たずに諦める(http_server):
    """bootTimeoutMs を待たずに即 False。枠を無駄にしない。"""
    cfg = _cfg(_free_port(), {"type": "tcp_listen"}, timeout=30000)
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    assert not await wait_until_ready(cfg, is_alive=lambda: False)
    assert loop.time() - t0 < 1.0
