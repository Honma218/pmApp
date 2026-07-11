"""
test_emit_slice_pr_event.py — submitted/completed 自動記録のテスト（P6準備）。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("emit_slice_pr_event", SCRIPTS_DIR / "emit_slice_pr_event.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore[union-attr]


def read_events(slice_id, events_dir):
    path = events_dir / f"slice-{slice_id:04d}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_resolve_slice_id_variants():
    assert mod.resolve_slice_id("feature/slice-0007-events-schema") == 7
    assert mod.resolve_slice_id("feature/slice-1-retry") == 1
    assert mod.resolve_slice_id("feature/p5-three-layer-aggregation") is None


def test_submitted_event_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "EVENTS_DIR", tmp_path)
    ok = mod.append_event(7, {
        "event_id": "pr-152",
        "type": "submitted",
        "slice_id": 7,
        "at": "2026-07-20T10:00:00Z",
        "pr": 152,
        "diff_add": 120,
        "diff_del": 8,
    })
    assert ok is True
    events = read_events(7, tmp_path)
    assert len(events) == 1
    assert events[0]["type"] == "submitted"
    assert events[0]["pr"] == 152


def test_append_event_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "EVENTS_DIR", tmp_path)
    event = {
        "event_id": "pr-merged-152",
        "type": "completed",
        "slice_id": 7,
        "at": "2026-07-21T00:00:00Z",
        "pr": 152,
    }
    assert mod.append_event(7, event) is True
    assert mod.append_event(7, event) is False  # 2回目は冪等スキップ
    events = read_events(7, tmp_path)
    assert len(events) == 1


def test_main_skips_unresolvable_head_ref(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "EVENTS_DIR", tmp_path)
    import sys
    old_argv = sys.argv
    sys.argv = [
        "emit_slice_pr_event.py", "--type", "submitted", "--pr-number", "1",
        "--head-ref", "feature/unrelated-branch", "--at", "2026-07-20T10:00:00Z",
    ]
    try:
        rc = mod.main()
    finally:
        sys.argv = old_argv
    assert rc == 0
    assert list(tmp_path.iterdir()) == []
    assert "対象外としてスキップ" in capsys.readouterr().out


def test_main_records_completed_event(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "EVENTS_DIR", tmp_path)
    import sys
    old_argv = sys.argv
    sys.argv = [
        "emit_slice_pr_event.py", "--type", "completed", "--pr-number", "152",
        "--head-ref", "feature/slice-0007-events-schema", "--at", "2026-07-21T00:00:00Z",
    ]
    try:
        rc = mod.main()
    finally:
        sys.argv = old_argv
    assert rc == 0
    events = read_events(7, tmp_path)
    assert len(events) == 1
    assert events[0] == {
        "event_id": "pr-merged-152",
        "type": "completed",
        "slice_id": 7,
        "at": "2026-07-21T00:00:00Z",
        "pr": 152,
    }
