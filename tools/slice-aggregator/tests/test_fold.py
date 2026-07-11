"""
test_fold.py — fold() の状態機械・決定性・KPI計算のテスト（P2完了基準の実体）。

完了基準（実装ロードマップ P2）:
  1. 同一 events 列から fold が常に同一 status を返す（決定性）。
  2. 状態機械の全遷移が単体テストで網羅。
  3. KPI 6指標が fold 出力から算出でき、分母定義が承認済み定義（P0・2026-07-11 GO）と一致。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fold import fold, compute_kpis  # noqa: E402


def ev(event_id, type_, slice_id, at, **kw):
    e = {"event_id": event_id, "type": type_, "slice_id": slice_id, "at": at}
    e.update(kw)
    return e


# --- 状態機械の遷移網羅 ---

def test_issued_only():
    events = [ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=10)]
    s = fold(events)[1]
    assert s.phase == "issued"
    assert s.issued_at == "2026-07-01T00:00:00Z"


def test_happy_path_completed_no_rescue():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=10),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=20, diff_add=100, diff_del=10),
        ev("e3", "gate", 1, "2026-07-03T00:00:00Z", by="pm", verdict="GO"),
        ev("e4", "completed", 1, "2026-07-03T01:00:00Z", pr=20),
    ]
    s = fold(events)[1]
    assert s.phase == "completed"
    assert s.completed_pr == 20
    assert s.rescued is False
    assert s.settled_at == "2026-07-03T01:00:00Z"
    assert s.diff_add == 100 and s.diff_del == 10


def test_rescue_and_revoke():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=10),
        ev("e2", "rescued", 1, "2026-07-01T01:00:00Z", actor="leader", note="質問", source="https://x/1"),
        ev("e3", "submitted", 1, "2026-07-02T00:00:00Z", pr=20, diff_add=10, diff_del=0),
        ev("e4", "completed", 1, "2026-07-02T01:00:00Z", pr=20),
    ]
    s = fold(events)[1]
    assert s.rescued is True  # 救援ありなので AFK 完走率の分子から除外される

    events_revoked = events + [ev("e5", "rescue_revoked", 1, "2026-07-02T02:00:00Z", actor="leader", source="https://x/1")]
    s2 = fold(events_revoked)[1]
    assert s2.rescued is False  # 打ち消しで救援なし扱いに戻る（確定ログ #B）


def test_rejected_then_resubmit_completed():
    events = [
        ev("e1", "issued", 2, "2026-07-01T00:00:00Z", actor="pm", spec_pr=11),
        ev("e2", "submitted", 2, "2026-07-02T00:00:00Z", pr=21, diff_add=50, diff_del=5),
        ev("e3", "rejected", 2, "2026-07-02T12:00:00Z", by="integrator", reason="範囲外ファイル"),
        ev("e4", "submitted", 2, "2026-07-03T00:00:00Z", pr=22, diff_add=20, diff_del=2),
        ev("e5", "gate", 2, "2026-07-03T06:00:00Z", by="pm", verdict="GO"),
        ev("e6", "completed", 2, "2026-07-03T07:00:00Z", pr=22),
    ]
    s = fold(events)[2]
    assert s.phase == "completed"
    assert s.rejected_count == 1
    # 破棄分を含む全消費の思想に合わせ diff は累積する
    assert s.diff_add == 70 and s.diff_del == 7


def test_gate_norework_then_completed():
    events = [
        ev("e1", "issued", 3, "2026-07-01T00:00:00Z", actor="pm", spec_pr=12),
        ev("e2", "submitted", 3, "2026-07-02T00:00:00Z", pr=30, diff_add=10, diff_del=1),
        ev("e3", "gate", 3, "2026-07-02T06:00:00Z", by="pm", verdict="NO-GO", kind="rework"),
        ev("e4", "submitted", 3, "2026-07-02T12:00:00Z", pr=31, diff_add=5, diff_del=0),
        ev("e5", "gate", 3, "2026-07-02T18:00:00Z", by="pm", verdict="GO"),
        ev("e6", "completed", 3, "2026-07-02T19:00:00Z", pr=31),
    ]
    s = fold(events)[3]
    assert s.phase == "completed"
    assert s.rework_count == 1


def test_gate_redecompose_then_abandoned_split():
    events = [
        ev("e1", "issued", 4, "2026-07-01T00:00:00Z", actor="pm", spec_pr=13),
        ev("e2", "submitted", 4, "2026-07-02T00:00:00Z", pr=40, diff_add=500, diff_del=50),
        ev("e3", "gate", 4, "2026-07-02T06:00:00Z", by="pm", verdict="NO-GO", kind="redecompose"),
        ev("e4", "abandoned", 4, "2026-07-02T07:00:00Z", reason="split"),
    ]
    s = fold(events)[4]
    assert s.phase == "abandoned"
    assert s.abandoned_reason == "split"
    assert s.redecompose_count == 1
    assert s.settled_at == "2026-07-02T07:00:00Z"


def test_abandoned_failed_no_submission():
    events = [
        ev("e1", "issued", 5, "2026-07-01T00:00:00Z", actor="pm", spec_pr=14),
        ev("e2", "abandoned", 5, "2026-07-05T00:00:00Z", reason="failed"),
    ]
    s = fold(events)[5]
    assert s.phase == "abandoned"
    assert s.abandoned_reason == "failed"


def test_terminal_events_are_not_overwritten():
    """終端到達後に非終端イベントが紛れ込んでも phase は変わらない（防御的）。"""
    events = [
        ev("e1", "issued", 6, "2026-07-01T00:00:00Z", actor="pm", spec_pr=15),
        ev("e2", "submitted", 6, "2026-07-02T00:00:00Z", pr=60, diff_add=1, diff_del=0),
        ev("e3", "completed", 6, "2026-07-02T01:00:00Z", pr=60),
        ev("e4", "rejected", 6, "2026-07-03T00:00:00Z", by="integrator", reason="遅延投稿"),
    ]
    s = fold(events)[6]
    assert s.phase == "completed"


# --- 決定性（P2完了基準1） ---

def test_fold_is_deterministic():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=10),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=20, diff_add=100, diff_del=10),
        ev("e3", "gate", 1, "2026-07-03T00:00:00Z", by="pm", verdict="GO"),
        ev("e4", "completed", 1, "2026-07-03T01:00:00Z", pr=20),
    ]
    r1 = fold(events)[1].to_dict()
    r2 = fold(list(reversed(events)))[1].to_dict()  # 入力順序を変えても結果は同じ
    assert r1 == r2

    r3 = fold(events)[1].to_dict()
    assert r1 == r3  # 同一入力の再実行でも同じ


def test_fold_as_of_gives_stable_historical_snapshot():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=10),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=20, diff_add=100, diff_del=10),
        ev("e3", "gate", 1, "2026-07-03T00:00:00Z", by="pm", verdict="GO"),
        ev("e4", "completed", 1, "2026-07-03T01:00:00Z", pr=20),
    ]
    snap_before_completion = fold(events, as_of="2026-07-02T12:00:00Z")[1]
    assert snap_before_completion.phase == "submitted"

    # 同じ as_of で何度計算しても同じスナップショットになる（再現テストの核）
    snap_again = fold(events, as_of="2026-07-02T12:00:00Z")[1]
    assert snap_before_completion.to_dict() == snap_again.to_dict()

    snap_after = fold(events, as_of="2026-07-03T01:00:00Z")[1]
    assert snap_after.phase == "completed"


# --- KPI 計算（P2完了基準3・P0承認パッケージの確定定義） ---

def test_kpi_afk_completion_rate_excludes_rescued():
    events = [
        # slice 1: 完了・救援なし
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
        ev("e2", "completed", 1, "2026-07-02T00:00:00Z", pr=1),
        # slice 2: 完了・救援あり
        ev("e3", "issued", 2, "2026-07-01T00:00:00Z", actor="pm", spec_pr=2),
        ev("e4", "rescued", 2, "2026-07-01T01:00:00Z", actor="leader", note="質問", source="https://x/2"),
        ev("e5", "completed", 2, "2026-07-02T00:00:00Z", pr=2),
        # slice 3: abandoned:failed（分母に入るが分子には入らない）
        ev("e6", "issued", 3, "2026-07-01T00:00:00Z", actor="pm", spec_pr=3),
        ev("e7", "abandoned", 3, "2026-07-05T00:00:00Z", reason="failed"),
        # slice 4: abandoned:descoped（分母に入らない）
        ev("e8", "issued", 4, "2026-07-01T00:00:00Z", actor="pm", spec_pr=4),
        ev("e9", "abandoned", 4, "2026-07-05T00:00:00Z", reason="descoped"),
    ]
    statuses = fold(events)
    kpis = compute_kpis(statuses)
    # 分母 = 完了(2) + abandoned:failed(1) = 3 / 分子 = 救援なしで完了(slice1のみ) = 1
    assert kpis["afk_completion_rate_detail"] == {"numerator": 1, "denominator": 3}
    assert kpis["afk_completion_rate"] == 1 / 3


def test_kpi_rework_rate():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=1, diff_add=1, diff_del=0),
        ev("e3", "rejected", 1, "2026-07-02T06:00:00Z", by="integrator", reason="x"),
        ev("e4", "gate", 1, "2026-07-02T12:00:00Z", by="pm", verdict="NO-GO", kind="rework"),
        ev("e5", "submitted", 1, "2026-07-02T18:00:00Z", pr=2, diff_add=1, diff_del=0),
        ev("e6", "completed", 1, "2026-07-03T00:00:00Z", pr=2),
    ]
    kpis = compute_kpis(fold(events))
    # 分子 = rejected(1) + rework(1) = 2 / 分母 = 完了(1)
    assert kpis["rework_rate_detail"] == {"numerator": 2, "denominator": 1}
    assert kpis["rework_rate"] == 2.0


def test_kpi_cost_efficiency_null_when_unknown():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=1, diff_add=1, diff_del=0, usage_usd=None),
        ev("e3", "completed", 1, "2026-07-03T00:00:00Z", pr=1),
    ]
    kpis = compute_kpis(fold(events))
    assert kpis["cost_efficiency_usd_per_task"] is None  # 取得元未定・null許容（P0#3）


def test_kpi_cost_efficiency_sums_including_abandoned():
    events = [
        # 完了スライス
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=1, diff_add=1, diff_del=0, usage_usd=2.0),
        ev("e3", "completed", 1, "2026-07-03T00:00:00Z", pr=1),
        # 破棄スライス（分子には算入・分母には算入しない）
        ev("e4", "issued", 2, "2026-07-01T00:00:00Z", actor="pm", spec_pr=2),
        ev("e5", "submitted", 2, "2026-07-02T00:00:00Z", pr=2, diff_add=1, diff_del=0, usage_usd=3.0),
        ev("e6", "abandoned", 2, "2026-07-04T00:00:00Z", reason="failed"),
    ]
    kpis = compute_kpis(fold(events))
    # 分子 = 2.0 + 3.0 = 5.0（破棄分を含む全消費） / 分母 = 完了(1)
    assert kpis["cost_efficiency_usd_per_task"] == 5.0


def test_kpi_instruction_progress_excludes_descoped():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
        ev("e2", "completed", 1, "2026-07-02T00:00:00Z", pr=1),
        ev("e3", "issued", 2, "2026-07-01T00:00:00Z", actor="pm", spec_pr=2),
        ev("e4", "abandoned", 2, "2026-07-02T00:00:00Z", reason="descoped"),
        ev("e5", "issued", 3, "2026-07-01T00:00:00Z", actor="pm", spec_pr=3),
    ]
    kpis = compute_kpis(fold(events))
    # 分母 = issued(3) - descoped(1) = 2 / 分子 = 完了(1)
    assert kpis["instruction_progress_detail"] == {"numerator": 1, "denominator": 2}
    assert kpis["instruction_progress_rate"] == 0.5


def test_kpi_bloat_signal_is_raw_not_thresholded():
    events = [
        ev("e1", "issued", 1, "2026-07-01T00:00:00Z", actor="pm", spec_pr=1),
        ev("e2", "submitted", 1, "2026-07-02T00:00:00Z", pr=1, diff_add=900, diff_del=100),
        ev("e3", "completed", 1, "2026-07-03T00:00:00Z", pr=1),
        ev("e4", "issued", 2, "2026-07-01T00:00:00Z", actor="pm", spec_pr=2),
        ev("e5", "gate", 2, "2026-07-01T06:00:00Z", by="pm", verdict="NO-GO", kind="redecompose"),
        ev("e6", "abandoned", 2, "2026-07-01T07:00:00Z", reason="split"),
    ]
    kpis = compute_kpis(fold(events))
    signal = kpis["slice_bloat_signal"]
    assert signal["completed_diff_lines"] == [1000]
    assert signal["abandoned_split_count"] == 1
    assert signal["redecompose_event_count"] == 1
    assert signal["denominator"] == 2  # completed(1) + abandoned:split(1)
    assert "閾値未確定" in signal["note"]


def test_empty_events_gives_empty_kpis():
    kpis = compute_kpis(fold([]))
    assert kpis["afk_completion_rate"] is None
    assert kpis["rework_rate"] is None
    assert kpis["cost_efficiency_usd_per_task"] is None
    assert kpis["instruction_progress_rate"] is None
