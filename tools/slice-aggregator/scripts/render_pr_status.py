#!/usr/bin/env python3
"""
render_pr_status.py — PR速報コメント用の現在地1行を生成する（P5 ①）。

自分のPRにのみ投稿する（他スライスの状態は見せない・確定ログ #I）。
このスクリプトは書き込みを行わない（メッセージを標準出力するだけ）。
コメントの投稿・更新（find-or-create）はワークフロー側（gh api）が担う。
出力1行目の HTML コメントはワークフローが「自分の投稿したコメントか」を識別するマーカー。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fold import load_events, fold, SliceStatus  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

MARKER_TEMPLATE = "<!-- slice-aggregator:status:{slice_id} -->"

PHASE_LABEL = {
    "issued": "起票済み",
    "submitted": "提出済み（ゲート待ち）",
    "gated_go": "GO判定済み（マージ待ち）",
    "completed": "完了",
    "unknown": "未起票（issuedイベント待ち）",
}


def render(slice_id: int, statuses: dict[int, SliceStatus]) -> str:
    s = statuses.get(slice_id)
    marker = MARKER_TEMPLATE.format(slice_id=slice_id)
    if s is None:
        return f"{marker}\n📍 slice_id={slice_id}: events未生成（`issued` イベント待ち）"

    if s.phase == "abandoned":
        label = f"破棄（{s.abandoned_reason}）"
    else:
        label = PHASE_LABEL.get(s.phase, s.phase)

    details = []
    if s.rescued:
        details.append("救援あり")
    if s.rejected_count:
        details.append(f"統合役NG {s.rejected_count}回")
    if s.rework_count:
        details.append(f"rework {s.rework_count}回")
    detail_str = f"（{', '.join(details)}）" if details else ""

    return f"{marker}\n📍 slice_id={slice_id}: {label}{detail_str}"


def main() -> int:
    ap = argparse.ArgumentParser(description="PR速報コメント用の現在地1行を生成する")
    ap.add_argument("--slice-id", type=int, required=True)
    args = ap.parse_args()

    path = REPO_ROOT / "docs" / "metrics" / "events" / f"slice-{args.slice_id:04d}.jsonl"
    events = load_events([str(path)])
    statuses = fold(events)

    print(render(args.slice_id, statuses))
    return 0


if __name__ == "__main__":
    sys.exit(main())
