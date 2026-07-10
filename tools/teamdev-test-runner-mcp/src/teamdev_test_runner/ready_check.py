"""ready 判定の 4 strategy と、それを回す polling loop。

各 strategy は `is_ready(runtime)` を持ち、`wait_until_ready()` が 500ms 間隔で
`bootTimeoutMs` まで叩く。

  - Express     → `/health` に 200        … Http200Check
  - Next.js     → `/` に 200              … Http200Check
  - HTTP を話さない → port が listen       … TcpListenCheck
"""

from __future__ import annotations

import asyncio
import socket
import time
from typing import Protocol
from urllib.parse import urljoin, urlparse

import httpx

from .runtime_config import (
    Http200Ready,
    HttpStatusReady,
    RuntimeConfig,
    TcpListenReady,
    TextInResponseReady,
)

HTTP_TIMEOUT_SEC = 2.0
POLL_INTERVAL_SEC = 0.5


class ReadyStrategy(Protocol):
    async def is_ready(self, runtime: RuntimeConfig) -> bool: ...


def _base_url(runtime: RuntimeConfig) -> str:
    if runtime.entry_url:
        return runtime.entry_url
    if runtime.port:
        return f"http://localhost:{runtime.port}"
    raise ValueError("entryUrl も port も無いので HTTP の ready 判定ができません")


async def _get(runtime: RuntimeConfig, path: str) -> httpx.Response | None:
    url = urljoin(_base_url(runtime).rstrip("/") + "/", path.lstrip("/"))
    try:
        # trust_env=False: HTTP_PROXY / ALL_PROXY があってもローカルの ready 判定を
        # プロキシ経由にしない。企業プロキシ設定のある開発機で readyCheck が壊れる。
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC, trust_env=False) as client:
            return await client.get(url)
    except (httpx.HTTPError, OSError):
        return None


class Http200Check:
    def __init__(self, spec: Http200Ready) -> None:
        self._spec = spec

    async def is_ready(self, runtime: RuntimeConfig) -> bool:
        r = await _get(runtime, self._spec.path)
        return r is not None and r.status_code == 200


class HttpStatusCheck:
    def __init__(self, spec: HttpStatusReady) -> None:
        self._spec = spec

    async def is_ready(self, runtime: RuntimeConfig) -> bool:
        r = await _get(runtime, self._spec.path)
        return r is not None and r.status_code == self._spec.expect_status


class TextInResponseCheck:
    def __init__(self, spec: TextInResponseReady) -> None:
        self._spec = spec

    async def is_ready(self, runtime: RuntimeConfig) -> bool:
        r = await _get(runtime, self._spec.path)
        return r is not None and self._spec.contains in r.text


class TcpListenCheck:
    def __init__(self, spec: TcpListenReady) -> None:
        self._spec = spec

    @staticmethod
    def _host_of(runtime: RuntimeConfig) -> str:
        if runtime.entry_url:
            return urlparse(runtime.entry_url).hostname or "localhost"
        return "localhost"

    @staticmethod
    def _try_connect(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=HTTP_TIMEOUT_SEC):
                return True
        except OSError:
            return False

    async def is_ready(self, runtime: RuntimeConfig) -> bool:
        port = self._spec.port or runtime.port
        if not port:
            return False
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._try_connect, self._host_of(runtime), port
        )


def strategy_for(runtime: RuntimeConfig) -> ReadyStrategy:
    spec = runtime.ready_check
    if isinstance(spec, Http200Ready):
        return Http200Check(spec)
    if isinstance(spec, HttpStatusReady):
        return HttpStatusCheck(spec)
    if isinstance(spec, TextInResponseReady):
        return TextInResponseCheck(spec)
    if isinstance(spec, TcpListenReady):
        return TcpListenCheck(spec)
    raise ValueError(f"未知の readyCheck: {spec!r}")


async def wait_until_ready(
    runtime: RuntimeConfig,
    *,
    is_alive: "callable[[], bool] | None" = None,
) -> bool:
    """ready になったら True。`bootTimeoutMs` を超えたら False。

    `is_alive` が渡され、それが False を返したら**待たずに諦める**
    （プロセスが即死したのにタイムアウトまで待つのは枠の無駄）。
    """
    strategy = strategy_for(runtime)
    deadline = time.monotonic() + runtime.boot_timeout_ms / 1000.0

    while time.monotonic() < deadline:
        if is_alive is not None and not is_alive():
            return False
        try:
            if await strategy.is_ready(runtime):
                return True
        except ValueError:
            return False
        await asyncio.sleep(POLL_INTERVAL_SEC)
    return False
