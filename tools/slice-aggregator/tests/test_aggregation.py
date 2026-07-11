"""
test_aggregation.py — P5（三層集約）の純関数テスト。

generate_daily_snapshot.generate / generate_weekly_report.generate・
last_n_afk_rate・flywheel_observations / render_pr_status.render を検証する。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


daily_mod = _load("generate_daily_snapshot")
weekly_mod = _load("generate_weekly_report")
pr_status_mod = _load("render_pr_status")

sys.path.insert(0, str(SCRIPTS_DIR))
from fold import fold  # noqa: E402


def ev(event_id, type_, slice_id, at, **kw):
    e = {"event_id": event_id, "type": type_, "slice_id": slice_id, "at": at}
    e.update(kw)
    return e


SAMPLE_EVENTS = [
    ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
    ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=1, diff_add=10, diff_del=0),
    ev("e3", "completed", 1, "2026-07-02T01:00:00Z", pr=1),
    ev("e4", "issued", 2, "2026-07-01T00:00:00Z", actor="pm", spec_pr=2),
    ev("e5", "rescued", 2, "2026-07-01T06:00:00Z", actor="leader", note="質問", source="https://x/2"),
    ev("e6", "submitted", 2, "2026-07-02T00:00:00Z", pr=2, diff_add=5, diff_del=0),
    ev("e7", "completed", 2, "2026-07-02T02:00:00Z", pr=2),
]


# --- generate_daily_snapshot ---

def test_daily_generate_produces_expected_shape():
    slice_map, daily, date_str = daily_mod.generate("2026-07-03T00:00:00Z", SAMPLE_EVENTS)
    assert date_str == "2026-07-03"
    assert daily["date"] == "2026-07-03"
    assert daily["slice_count"] == {"total": 2, "completed": 2, "abandoned": 0, "in_progress": 0}
    assert set(slice_map["slices"].keys()) == {"1", "2"}
    assert slice_map["slices"]["2"]["rescued"] is True


def test_daily_generate_is_deterministic():
    r1 = daily_mod.generate("2026-07-03T00:00:00Z", SAMPLE_EVENTS)
    r2 = daily_mod.generate("2026-07-03T00:00:00Z", list(reversed(SAMPLE_EVENTS)))
    assert r1 == r2


def test_daily_generate_respects_as_of_before_completion():
    # 1件目が完了する前の時点では in_progress として数えられる
    slice_map, daily, date_str = daily_mod.generate("2026-07-01T12:00:00Z", SAMPLE_EVENTS)
    assert date_str == "2026-07-01"
    assert daily["slice_count"]["completed"] == 0
    assert daily["slice_count"]["in_progress"] == 2


# --- generate_weekly_report ---

def test_weekly_iso_week_str():
    # 2026-07-03 は ISO週で 2026-W27
    assert weekly_mod.iso_week_str("2026-07-03T00:00:00Z") == "2026-W27"


def test_weekly_last_n_afk_rate_excludes_rescued():
    statuses = fold(SAMPLE_EVENTS)
    result = weekly_mod.last_n_afk_rate(statuses, n=5)
    # slice1(救援なし完了)・slice2(救援あり完了) の2件がwindow。分子は救援なしの1件のみ
    assert result == {"window_size": 2, "numerator": 1, "rate": 0.5}


def test_weekly_last_n_afk_rate_empty_when_no_settled():
    statuses = fold([ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1)])
    result = weekly_mod.last_n_afk_rate(statuses)
    assert result == {"window_size": 0, "numerator": 0, "rate": None}


def test_weekly_flywheel_observations_lists_flagged_slices_only():
    events = SAMPLE_EVENTS + [
        ev("e8", "rejected", 1, "2026-07-01T12:00:00Z", by="integrator", reason="範囲外"),
    ]
    statuses = fold(events)
    obs = weekly_mod.flywheel_observations(statuses)
    assert len(obs) == 1
    assert "slice_id=1" in obs[0]
    assert "統合役NG 1回" in obs[0]


def test_weekly_generate_produces_markdown_with_week_header():
    week, md = weekly_mod.generate("2026-07-03T00:00:00Z", SAMPLE_EVENTS)
    assert week == "2026-W27"
    assert "# 週次ステータス — 2026-W27" in md
    assert "AFK完走率" in md
    assert "Flywheel 観察項目" in md


def test_weekly_generate_is_deterministic():
    r1 = weekly_mod.generate("2026-07-03T00:00:00Z", SAMPLE_EVENTS)
    r2 = weekly_mod.generate("2026-07-03T00:00:00Z", list(reversed(SAMPLE_EVENTS)))
    assert r1 == r2


def test_weekly_generate_handles_empty_events():
    week, md = weekly_mod.generate("2026-07-03T00:00:00Z", [])
    assert "まだ完了・断念したスライスが無く算出不可" in md
    assert "（観察対象なし）" in md


# --- render_pr_status ---

def test_pr_status_unknown_slice_reports_events_pending():
    msg = pr_status_mod.render(99, {})
    assert "slice-aggregator:status:99" in msg
    assert "events未生成" in msg


def test_pr_status_completed_no_rescue():
    statuses = fold(SAMPLE_EVENTS)
    msg = pr_status_mod.render(1, statuses)
    assert "slice_id=1" in msg
    assert "完了" in msg
    assert "救援あり" not in msg


def test_pr_status_completed_with_rescue_shows_detail():
    statuses = fold(SAMPLE_EVENTS)
    msg = pr_status_mod.render(2, statuses)
    assert "救援あり" in msg


def test_pr_status_abandoned_shows_reason():
    events = [
        ev("e1", "issued", 3, "2026-07-01T00:00:00Z", actor="pm", spec_pr=3),
        ev("e2", "abandoned", 3, "2026-07-05T00:00:00Z", reason="split"),
    ]
    statuses = fold(events)
    msg = pr_status_mod.render(3, statuses)
    assert "破棄（split）" in msg
