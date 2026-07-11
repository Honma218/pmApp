#!/usr/bin/env python3
"""
generate_daily_snapshot.py — 日次で全 events を再計算し、集約の派生物を生成する（P5 ②）。

大原則：**集約を書くのは日次 cron 1本だけ**（確定ログ #J）。`/submit`・`/rescue` は集約に触れない。
書き手が1つなので突合が原理的に起きない。

生成物:
  - docs/metrics/index/slice-map.json  … slice_id ごとの状態一覧（派生物。正本は events）
  - docs/status/daily/<as_of の日付>.json … その日の KPI スナップショット

`--as-of` は呼び出し側（cron）が実行時刻で固定して渡す。同一 (commit, as_of) の再実行が
同じ結果になることは fold() の決定性（P2）に依存する。日付・週は as_of から導出し、
別引数として渡さない（食い違いの余地を無くす。単一情報源）。

終了コード: 0=成功 / 2=実行前提エラー。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fold import load_events, fold, compute_kpis, SliceStatus  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_GLOB = "docs/metrics/events/**/*.jsonl"
INDEX_DIR = REPO_ROOT / "docs" / "metrics" / "index"
DAILY_DIR = REPO_ROOT / "docs" / "status" / "daily"


def parse_as_of(as_of: str) -> datetime:
    return datetime.fromisoformat(as_of.replace("Z", "+00:00"))


def build_slice_map(statuses: dict[int, SliceStatus]) -> dict:
    return {
        str(sid): {
            "phase": s.phase,
            "abandoned_reason": s.abandoned_reason,
            "issue": s.issue,
            "issued_at": s.issued_at,
            "settled_at": s.settled_at,
            "rescued": s.rescued,
            "completed_pr": s.completed_pr,
        }
        for sid, s in sorted(statuses.items())
    }


def generate(as_of: str, events: list[dict]) -> tuple[dict, dict, str]:
    """(slice_map, daily_snapshot, date_str) を返す純関数（テスト容易性のため I/O を分離）。"""
    statuses = fold(events, as_of=as_of)
    kpis = compute_kpis(statuses)

    slice_map = {
        "generated_at": as_of,
        "as_of": as_of,
        "slices": build_slice_map(statuses),
    }

    phases = [s.phase for s in statuses.values()]
    date_str = parse_as_of(as_of).date().isoformat()
    daily = {
        "date": date_str,
        "as_of": as_of,
        "kpis": kpis,
        "slice_count": {
            "total": len(statuses),
            "completed": phases.count("completed"),
            "abandoned": phases.count("abandoned"),
            "in_progress": len(statuses) - phases.count("completed") - phases.count("abandoned"),
        },
    }
    return slice_map, daily, date_str


def main() -> int:
    ap = argparse.ArgumentParser(description="日次スナップショットを生成する")
    ap.add_argument("--as-of", required=True, help="ISO8601。再現性のため呼び出し側が固定して渡す")
    args = ap.parse_args()

    try:
        parse_as_of(args.as_of)
    except ValueError as e:
        print(f"ERROR: --as-of の形式が不正: {e}", file=sys.stderr)
        return 2

    events = load_events(glob.glob(str(REPO_ROOT / EVENTS_GLOB), recursive=True))
    slice_map, daily, date_str = generate(args.as_of, events)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    (INDEX_DIR / "slice-map.json").write_text(
        json.dumps(slice_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    (DAILY_DIR / f"{date_str}.json").write_text(
        json.dumps(daily, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"slice-map.json（{len(slice_map['slices'])}件）と daily/{date_str}.json を生成しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
