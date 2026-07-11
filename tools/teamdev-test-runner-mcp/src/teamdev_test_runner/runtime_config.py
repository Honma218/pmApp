"""`test-harness.runtime.json` の読み込みと検証（Pydantic v2）。

配置: `<app_dir>/test-harness.runtime.json`

    {
      "$schema": "../tools/teamdev-test-runner-mcp/schema/runtime.schema.json",
      "bootCommand": "npm run start:dev",
      "cwd": ".",
      "env": {},
      "entryUrl": "http://localhost:3000",
      "port": 3000,
      "bootTimeoutMs": 60000,
      "readyCheck": { "type": "http_200", "path": "/health" },
      "shutdownGracefulMs": 5000
    }

`readyCheck.type` は `http_200` / `http_status` / `tcp_listen` / `text_in_response` の
discriminated union。未知のキーは `extra="forbid"` で弾く——**設定ミスを黙って無視しない**。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError

CONFIG_FILENAME = "test-harness.runtime.json"


class RuntimeConfigError(Exception):
    """設定が読めない・壊れている。呼び出し側はそのままモデルに返してよい。"""


class _ReadyCheckBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Http200Ready(_ReadyCheckBase):
    """`path` に GET して 200 なら ready。"""

    type: Literal["http_200"]
    path: str


class HttpStatusReady(_ReadyCheckBase):
    """`path` に GET して `expectStatus` と一致すれば ready。"""

    type: Literal["http_status"]
    path: str
    expect_status: int = Field(alias="expectStatus")


class TcpListenReady(_ReadyCheckBase):
    """`port` が listen していれば ready。HTTP を話さないサーバー向け。"""

    type: Literal["tcp_listen"]
    port: int | None = None


class TextInResponseReady(_ReadyCheckBase):
    """`path` の body に `contains` が含まれれば ready。"""

    type: Literal["text_in_response"]
    path: str
    contains: str


ReadyCheck = Annotated[
    Union[Http200Ready, HttpStatusReady, TcpListenReady, TextInResponseReady],
    Field(discriminator="type"),
]


class RuntimeConfig(BaseModel):
    """`test-harness.runtime.json` の型。

    - `cwd` は `app_dir` からの相対（既定 "."）
    - `env` は起動時に環境変数へマージされる
    - `port` は harness_status の listening 判定に使う
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    boot_command: str = Field(alias="bootCommand", min_length=1)
    cwd: str = "."
    env: dict[str, str] = Field(default_factory=dict)
    entry_url: str | None = Field(default=None, alias="entryUrl")
    port: int | None = None
    boot_timeout_ms: int = Field(default=30_000, alias="bootTimeoutMs", ge=1_000)
    shutdown_graceful_ms: int = Field(default=5_000, alias="shutdownGracefulMs", ge=0)
    ready_check: ReadyCheck = Field(alias="readyCheck")


def load_runtime_config(app_dir: Path) -> RuntimeConfig:
    path = app_dir / CONFIG_FILENAME
    if not path.is_file():
        raise RuntimeConfigError(
            f"{CONFIG_FILENAME} が見つかりません: {path}\n"
            f"アプリごとの起動設定はリポジトリに同梱します（設定ごと共有される）。"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeConfigError(f"{path} が JSON として壊れています: {e}") from e

    raw.pop("$schema", None)
    try:
        return RuntimeConfig.model_validate(raw)
    except ValidationError as e:
        raise RuntimeConfigError(f"{path} の内容が不正です:\n{e}") from e
