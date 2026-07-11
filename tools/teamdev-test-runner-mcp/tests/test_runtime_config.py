import json

import pytest

from teamdev_test_runner.runtime_config import (
    Http200Ready,
    RuntimeConfigError,
    TcpListenReady,
    load_runtime_config,
)

VALID = {
    "$schema": "../tools/teamdev-test-runner-mcp/schema/runtime.schema.json",
    "bootCommand": "npm run start:dev",
    "cwd": ".",
    "entryUrl": "http://localhost:3000",
    "port": 3000,
    "bootTimeoutMs": 60000,
    "readyCheck": {"type": "http_200", "path": "/health"},
}


def _write(tmp_path, data):
    (tmp_path / "test-harness.runtime.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def test_alias_で読める(tmp_path):
    cfg = load_runtime_config(_write(tmp_path, VALID))
    assert cfg.boot_command == "npm run start:dev"
    assert cfg.boot_timeout_ms == 60000
    assert isinstance(cfg.ready_check, Http200Ready)
    assert cfg.ready_check.path == "/health"


def test_schema_キーは無視される(tmp_path):
    load_runtime_config(_write(tmp_path, VALID))  # "$schema" があっても extra=forbid に触れない


def test_既定値(tmp_path):
    data = {"bootCommand": "x", "port": 1234, "readyCheck": {"type": "tcp_listen"}}
    cfg = load_runtime_config(_write(tmp_path, data))
    assert cfg.cwd == "."
    assert cfg.boot_timeout_ms == 30000
    assert cfg.shutdown_graceful_ms == 5000
    assert isinstance(cfg.ready_check, TcpListenReady)


def test_ファイルが無い(tmp_path):
    with pytest.raises(RuntimeConfigError, match="見つかりません"):
        load_runtime_config(tmp_path)


def test_JSONが壊れている(tmp_path):
    (tmp_path / "test-harness.runtime.json").write_text("{ nope", encoding="utf-8")
    with pytest.raises(RuntimeConfigError, match="壊れています"):
        load_runtime_config(tmp_path)


def test_未知のキーは黙って無視しない(tmp_path):
    bad = {**VALID, "bootCommnad": "typo"}
    with pytest.raises(RuntimeConfigError):
        load_runtime_config(_write(tmp_path, bad))


def test_未知のreadyCheck型は弾く(tmp_path):
    bad = {**VALID, "readyCheck": {"type": "magic"}}
    with pytest.raises(RuntimeConfigError):
        load_runtime_config(_write(tmp_path, bad))


def test_bootCommandが空なら弾く(tmp_path):
    bad = {**VALID, "bootCommand": ""}
    with pytest.raises(RuntimeConfigError):
        load_runtime_config(_write(tmp_path, bad))
