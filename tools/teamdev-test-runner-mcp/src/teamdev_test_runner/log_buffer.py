"""子プロセスの stdout / stderr を溜めるリングバッファ。

reader thread が byte 行を decode して push する。`max_lines` で上限を切るので
メモリは O(max_lines * 行長) に収まる。thread-safe。
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True, frozen=True)
class LogLine:
    stream: str  # "stdout" | "stderr"
    text: str
    ts: str  # ISO8601 UTC


class LogBuffer:
    """thread-safe な行バッファ。"""

    def __init__(self, max_lines: int = 2000) -> None:
        self._lines: deque[LogLine] = deque(maxlen=max_lines)
        self._lock = threading.Lock()

    def append(self, stream: str, text: str) -> None:
        line = LogLine(
            stream=stream,
            text=text.rstrip("\r\n"),
            ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        with self._lock:
            self._lines.append(line)

    def tail(self, lines: int = 50, stream: str | None = None) -> list[LogLine]:
        """末尾 `lines` 行。`stream` を指定すると stdout / stderr で絞る。"""
        with self._lock:
            snapshot = list(self._lines)
        if stream:
            snapshot = [l for l in snapshot if l.stream == stream]
        return snapshot[-lines:]

    def clear(self) -> None:
        with self._lock:
            self._lines.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._lines)
