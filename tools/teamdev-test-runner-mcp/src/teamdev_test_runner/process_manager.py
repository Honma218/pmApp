"""`subprocess.Popen` の薄い wrapper。

  - bootCommand を `app_dir/cwd` で起動する
  - stdout/stderr を reader thread が LogBuffer へ流す
  - 停止は SIGTERM で graceful → 期限切れで SIGKILL

Windows / POSIX で process group の扱いが違うので、shell=True の子孫まで確実に殺す:
  Windows: `creationflags=CREATE_NEW_PROCESS_GROUP` + `taskkill /F /T /PID`
  POSIX:   `start_new_session=True`（setsid）+ `os.killpg(SIGTERM/SIGKILL)`

**1 app_dir = 1 プロセス。** 既に走っている app_dir に start を投げたら error を返す
（黙って二重起動しない。ポート衝突を「原因不明の赤」にしないため）。
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .log_buffer import LogBuffer, LogLine
from .runtime_config import RuntimeConfig

IS_WINDOWS = sys.platform.startswith("win")


@dataclass(slots=True)
class StartResult:
    started: bool
    pid: int | None = None
    port: int | None = None
    ready: bool = False
    entry_url: str | None = None
    started_at: str | None = None
    error: str | None = None


@dataclass(slots=True)
class StopResult:
    stopped: bool
    exit_code: int | None = None
    duration_ms: int = 0
    error: str | None = None


@dataclass(slots=True)
class StatusResult:
    running: bool
    pid: int | None = None
    port: int | None = None
    listening: bool = False
    started_at: str | None = None
    last_log_lines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _Handle:
    proc: "subprocess.Popen[bytes]"
    runtime: RuntimeConfig
    started_at: str
    log_buffer: LogBuffer = field(default_factory=lambda: LogBuffer(max_lines=2000))
    readers: list[threading.Thread] = field(default_factory=list)


def _is_listening(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=0.5):
            return True
    except OSError:
        return False


class ProcessManager:
    """app_dir を key にプロセスを1つだけ保持する。"""

    def __init__(self) -> None:
        self._handles: dict[str, _Handle] = {}
        self._lock = threading.Lock()

    # --- 起動 -------------------------------------------------------------

    def start(self, app_dir: Path, runtime: RuntimeConfig) -> StartResult:
        key = str(app_dir)
        with self._lock:
            existing = self._handles.get(key)
            if existing and existing.proc.poll() is None:
                return StartResult(
                    started=False,
                    pid=existing.proc.pid,
                    error=(
                        f"{key} は既に起動しています（pid={existing.proc.pid}）。"
                        f" 二重起動はしません。harness_stop してから start してください。"
                    ),
                )

            cwd = (app_dir / runtime.cwd).resolve()
            if not cwd.is_dir():
                return StartResult(started=False, error=f"cwd が存在しません: {cwd}")

            env = {**os.environ, **runtime.env}
            popen_kwargs: dict = {
                "cwd": str(cwd),
                "env": env,
                "shell": True,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
            }
            if IS_WINDOWS:
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["start_new_session"] = True

            try:
                proc = subprocess.Popen(runtime.boot_command, **popen_kwargs)
            except OSError as e:
                return StartResult(started=False, error=f"起動に失敗しました: {e}")

            handle = _Handle(
                proc=proc,
                runtime=runtime,
                started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            for name, pipe in (("stdout", proc.stdout), ("stderr", proc.stderr)):
                t = threading.Thread(
                    target=self._pump, args=(pipe, name, handle.log_buffer), daemon=True
                )
                t.start()
                handle.readers.append(t)

            self._handles[key] = handle

        return StartResult(
            started=True,
            pid=proc.pid,
            port=runtime.port,
            entry_url=runtime.entry_url,
            started_at=handle.started_at,
        )

    @staticmethod
    def _pump(pipe, stream: str, buf: LogBuffer) -> None:
        if pipe is None:
            return
        for raw in iter(pipe.readline, b""):
            buf.append(stream, raw.decode("utf-8", errors="replace"))
        pipe.close()

    # --- 参照 -------------------------------------------------------------

    def is_alive(self, app_dir: Path) -> bool:
        h = self._handles.get(str(app_dir))
        return bool(h and h.proc.poll() is None)

    def status(self, app_dir: Path) -> StatusResult:
        h = self._handles.get(str(app_dir))
        if h is None:
            return StatusResult(running=False)
        running = h.proc.poll() is None
        port = h.runtime.port
        return StatusResult(
            running=running,
            pid=h.proc.pid,
            port=port,
            listening=bool(port and running and _is_listening(port)),
            started_at=h.started_at,
            last_log_lines=[l.text for l in h.log_buffer.tail(10)],
        )

    def logs(self, app_dir: Path, lines: int = 50, stream: str | None = None) -> list[LogLine]:
        h = self._handles.get(str(app_dir))
        return h.log_buffer.tail(lines, stream) if h else []

    # --- 停止 -------------------------------------------------------------

    def stop(self, app_dir: Path) -> StopResult:
        key = str(app_dir)
        with self._lock:
            h = self._handles.pop(key, None)
        if h is None:
            return StopResult(stopped=False, error=f"{key} は起動していません")

        t0 = time.monotonic()
        if h.proc.poll() is not None:
            return StopResult(stopped=True, exit_code=h.proc.returncode, duration_ms=0)

        grace = h.runtime.shutdown_graceful_ms / 1000.0
        self._terminate(h.proc, force=False)
        try:
            h.proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            self._terminate(h.proc, force=True)
            try:
                h.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return StopResult(
                    stopped=False,
                    duration_ms=int((time.monotonic() - t0) * 1000),
                    error=f"pid={h.proc.pid} を SIGKILL しても停止しませんでした",
                )

        return StopResult(
            stopped=True,
            exit_code=h.proc.returncode,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    def stop_all(self) -> None:
        for key in list(self._handles):
            self.stop(Path(key))

    @staticmethod
    def _terminate(proc: "subprocess.Popen[bytes]", *, force: bool) -> None:
        """shell=True の子孫ごと殺す。孫プロセスを取り残すとポートが解放されない。"""
        if IS_WINDOWS:
            if force:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                proc.terminate()
            return
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            proc.kill() if force else proc.terminate()
