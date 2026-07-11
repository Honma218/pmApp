"""
test_generate_gates_log.py — gates.md 生成ロジックのテスト（slice-02）。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("generate_gates_log", SCRIPTS_DIR / "generate_gates_log.py")
ggl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ggl)  # type: ignore[union-attr]


def ev(event_id, type_, slice_id, at, **kw):
    e = {"event_id": event_id, "type": type_, "slice_id": slice_id, "at": at}
    e.update(kw)
    return e


def test_build_rows_ignores_non_gate_events():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=1, diff_add=1, diff_del=0),
    ]
    assert ggl.build_rows(events) == []


def test_build_rows_go():
    events = [ev("e1", "gate", 7, "2026-07-20T11:00:00Z", by="pm", verdict="GO")]
    rows = ggl.build_rows(events)
    assert rows == [{"slice_id": 7, "date": "2026-07-20", "verdict": "GO", "kind": "", "by": "pm"}]


def test_build_rows_nogo_with_kind():
    events = [ev("e1", "gate", 7, "2026-07-20T11:00:00Z", by="pm", verdict="NO-GO", kind="rework")]
    rows = ggl.build_rows(events)
    assert rows[0]["verdict"] == "NO-GO"
    assert rows[0]["kind"] == "rework"


def test_build_rows_sorted_by_at():
    events = [
        ev("e2", "gate", 9, "2026-07-22T00:00:00Z", by="pm", verdict="GO"),
        ev("e1", "gate", 7, "2026-07-20T00:00:00Z", by="pm", verdict="GO"),
    ]
    rows = ggl.build_rows(events)
    assert [r["slice_id"] for r in rows] == [7, 9]


def test_render_markdown_empty_shows_placeholder_row():
    md = ggl.render_markdown([])
    assert "| slice_id | 日付 | 判定 | NO-GO種別 | PM/代理 |" in md
    assert "| | | | | |" in md


def test_render_markdown_with_rows():
    rows = [{"slice_id": 7, "date": "2026-07-20", "verdict": "NO-GO", "kind": "rework", "by": "pm"}]
    md = ggl.render_markdown(rows)
    assert "| 7 | 2026-07-20 | NO-GO | rework | pm |" in md


def test_generate_is_deterministic():
    events = [
        ev("e1", "gate", 7, "2026-07-20T11:00:00Z", by="pm", verdict="NO-GO", kind="rework"),
        ev("e2", "gate", 7, "2026-07-21T00:00:00Z", by="pm", verdict="GO"),
    ]
    r1 = ggl.generate(events)
    r2 = ggl.generate(list(reversed(events)))
    assert r1 == r2


def test_generate_includes_header_status_note():
    md = ggl.generate([])
    assert "生成物" in md
    assert "手動編集しないこと" in md
