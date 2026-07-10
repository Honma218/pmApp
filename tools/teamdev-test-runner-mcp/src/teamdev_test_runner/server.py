"""teamdev-test-runner MCP server（stdio）。

公開ツールは4つだけ:
    - harness_start   アプリを起動して ready まで待つ
    - harness_status  生きているか / listening か
    - harness_logs    stdout / stderr の末尾
    - harness_stop    graceful → force で停止

**このサーバーは実行環境係であって採点係ではない。** 合否はテストFW
（`@playwright/test` 等）が出す。ツール名も `verb_noun` で1ツール=1操作に保つ。

repo root は `TEAMDEV_REPO_ROOT` を優先し、未設定なら cwd から上へマーカーを探す
（`.mcp.json` は Claude Code が repo ルートを cwd にして stdio サーバーを起動するため）。
`app_dir` は repo root の内側に限る——外を指されたら **refuse**。

**stdout に何も書かないこと。** stdio プロトコルが壊れる。ログは stderr へ。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from . import __version__
from .process_manager import ProcessManager
from .ready_check import wait_until_ready
from .runtime_config import RuntimeConfigError, load_runtime_config

SERVER_NAME = "teamdev-test-runner"
ROOT_MARKERS = (".mcp.json", ".git", "CLAUDE.md")

_manager = ProcessManager()


# --- パス解決 --------------------------------------------------------------


def _repo_root() -> Path:
    env = os.environ.get("TEAMDEV_REPO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # `.mcp.json` の ${workspaceFolder} は展開されないので、cwd から自動検出する。
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if any((candidate / m).exists() for m in ROOT_MARKERS):
            return candidate
    return cwd


def _resolve_app_dir(app_dir_arg: str) -> Path:
    """`app_dir` を repo root 配下に閉じ込める。外を指されたら raise。"""
    root = _repo_root()
    p = Path(app_dir_arg).expanduser()
    resolved = (p if p.is_absolute() else root / p).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(
            f"app_dir={resolved} is outside TEAMDEV_REPO_ROOT={root}. refuse."
        ) from None
    if not resolved.is_dir():
        raise ValueError(f"app_dir does not exist: {resolved}")
    return resolved


# --- ツール定義 ------------------------------------------------------------

_APP_DIR_PROP = {
    "app_dir": {
        "type": "string",
        "description": "repo root からの相対パス（例: 'backend', 'frontend'）。"
        "そのディレクトリの test-harness.runtime.json を読む。",
    }
}

TOOLS: list[types.Tool] = [
    types.Tool(
        name="harness_start",
        description=(
            "app_dir のアプリを test-harness.runtime.json に従って起動し、readyCheck が"
            " 通るまで待つ。テストを実行する前に必ず呼ぶ。**合否は返さない**——"
            "起動できたかどうかだけを返す。既に起動中なら二重起動せず error を返す。"
        ),
        inputSchema={
            "type": "object",
            "properties": _APP_DIR_PROP,
            "required": ["app_dir"],
        },
    ),
    types.Tool(
        name="harness_status",
        description=(
            "app_dir のアプリが生きているか、ポートが listening かを返す。"
            "テストが接続できない原因が「落ちている」のか「まだ ready でない」のかを切り分けるときに使う。"
        ),
        inputSchema={
            "type": "object",
            "properties": _APP_DIR_PROP,
            "required": ["app_dir"],
        },
    ),
    types.Tool(
        name="harness_logs",
        description=(
            "app_dir のアプリの stdout / stderr の末尾を返す。テストが赤いとき、"
            "コードを直す前にまずこれを読む（trace / screenshot と合わせて原因を特定する）。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **_APP_DIR_PROP,
                "lines": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
                "stream": {"type": "string", "enum": ["stdout", "stderr"]},
            },
            "required": ["app_dir"],
        },
    ),
    types.Tool(
        name="harness_stop",
        description=(
            "app_dir のアプリを停止する（SIGTERM で graceful → 期限切れで SIGKILL）。"
            "テストが緑になったら停止して報告すること。ポートを掴んだまま次のスライスに進まない。"
        ),
        inputSchema={
            "type": "object",
            "properties": _APP_DIR_PROP,
            "required": ["app_dir"],
        },
    ),
]


# --- ハンドラ --------------------------------------------------------------


async def _handle_start(app_dir: Path) -> dict[str, Any]:
    runtime = load_runtime_config(app_dir)
    result = _manager.start(app_dir, runtime)
    if not result.started:
        return {"started": False, "ready": False, "error": result.error, "pid": result.pid}

    ready = await wait_until_ready(runtime, is_alive=lambda: _manager.is_alive(app_dir))
    payload: dict[str, Any] = {
        "started": True,
        "ready": ready,
        "pid": result.pid,
        "port": result.port,
        "entryUrl": result.entry_url,
        "startedAt": result.started_at,
    }
    if not ready:
        alive = _manager.is_alive(app_dir)
        payload["error"] = (
            f"bootTimeoutMs={runtime.boot_timeout_ms} 以内に ready になりませんでした"
            if alive
            else "プロセスが起動直後に終了しました"
        )
        payload["lastLogLines"] = [l.text for l in _manager.logs(app_dir, lines=20)]
    return payload


def _handle_status(app_dir: Path) -> dict[str, Any]:
    s = _manager.status(app_dir)
    return {
        "running": s.running,
        "pid": s.pid,
        "port": s.port,
        "listening": s.listening,
        "startedAt": s.started_at,
        "lastLogLines": s.last_log_lines,
    }


def _handle_logs(app_dir: Path, lines: int, stream: str | None) -> dict[str, Any]:
    return {
        "lines": [
            {"ts": l.ts, "stream": l.stream, "text": l.text}
            for l in _manager.logs(app_dir, lines=lines, stream=stream)
        ]
    }


def _handle_stop(app_dir: Path) -> dict[str, Any]:
    r = _manager.stop(app_dir)
    return {
        "stopped": r.stopped,
        "exitCode": r.exit_code,
        "durationMs": r.duration_ms,
        "error": r.error,
    }


def build_server() -> Server:
    server: Server = Server(SERVER_NAME)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
        args = arguments or {}
        try:
            app_dir = _resolve_app_dir(args["app_dir"])
            if name == "harness_start":
                payload = await _handle_start(app_dir)
            elif name == "harness_status":
                payload = _handle_status(app_dir)
            elif name == "harness_logs":
                payload = _handle_logs(app_dir, int(args.get("lines", 50)), args.get("stream"))
            elif name == "harness_stop":
                payload = _handle_stop(app_dir)
            else:
                raise ValueError(f"unknown tool: {name}")
        except (KeyError, ValueError, RuntimeConfigError) as e:
            payload = {"error": str(e)}

        return [types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))]

    return server


async def _serve() -> None:
    server = build_server()
    async with mcp.server.stdio.stdio_server() as (read, write):
        try:
            await server.run(
                read,
                write,
                InitializationOptions(
                    server_name=SERVER_NAME,
                    server_version=__version__,
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        finally:
            # クライアントが落ちても子プロセスを取り残さない。
            _manager.stop_all()


def run() -> None:
    print(f"{SERVER_NAME} v{__version__} starting (repo_root={_repo_root()})", file=sys.stderr)
    asyncio.run(_serve())
