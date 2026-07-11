#!/usr/bin/env python3
"""
emit_slice_pr_event.py — feature/slice-<N>-* PR の open/merge を検知し
submitted/completed イベントを記録する（P6準備。issued/rescuedと同じ automation パターン）。

GitHub の PR ライフサイクルから機械的に決まる2種類のイベント:
  - submitted: PR が open（または reopen）された時点。diff・PR番号を記録
  - completed: PR が main へ merge された時点

（`rejected`・`gate` は人の判断そのものなので対象外。/reject・/gate コメントコマンドで別途扱う）

書き込みは ADR-0012 の制約（bot・パス限定・append-only）に従う。
event_id は決定論的・冪等（"pr-<PR番号>" / "pr-merged-<PR番号>"）。

終了コード: 0=成功（記録 or 対象外でスキップ） / 1=slice_id解決失敗 / 2=実行前提エラー。
CLI:
  python emit_slice_pr_event.py --type submitted --pr-number N --head-ref REF --at ISO8601 \
      [--diff-add N --diff-del N]
  python emit_slice_pr_event.py --type completed --pr-number N --head-ref REF --at ISO8601
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_DIR = REPO_ROOT / "docs" / "metrics" / "events"

BRANCH_SLICE_RE = re.compile(r"feature/slice-0*(\d+)")


def resolve_slice_id(head_ref: str) -> int | None:
    m = BRANCH_SLICE_RE.search(head_ref)
    return int(m.group(1)) if m else None


def existing_event_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            eid = json.loads(line).get("event_id")
        except json.JSONDecodeError:
            continue
        if isinstance(eid, str):
            ids.add(eid)
    return ids


def append_event(slice_id: int, event: dict) -> bool:
    """True を返せば新規追記、False なら冪等スキップ。"""
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVENTS_DIR / f"slice-{slice_id:04d}.jsonl"
    if event["event_id"] in existing_event_ids(out_path):
        return False
    with out_path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(event, ensure_ascii=False) + "\n")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="feature/slice-* PRのライフサイクルからイベントを生成")
    ap.add_argument("--type", choices=["submitted", "completed"], required=True)
    ap.add_argument("--pr-number", type=int, required=True)
    ap.add_argument("--head-ref", required=True)
    ap.add_argument("--at", required=True, help="ISO8601（submitted: PR作成時刻 / completed: merged_at）")
    ap.add_argument("--diff-add", type=int, default=None)
    ap.add_argument("--diff-del", type=int, default=None)
    args = ap.parse_args()

    slice_id = resolve_slice_id(args.head_ref)
    if slice_id is None:
        print(f"head_ref '{args.head_ref}' から slice_id を解決できない。対象外としてスキップ。")
        return 0

    if args.type == "submitted":
        event = {
            "event_id": f"pr-{args.pr_number}",
            "type": "submitted",
            "slice_id": slice_id,
            "at": args.at,
            "pr": args.pr_number,
            "diff_add": args.diff_add or 0,
            "diff_del": args.diff_del or 0,
        }
    else:
        event = {
            "event_id": f"pr-merged-{args.pr_number}",
            "type": "completed",
            "slice_id": slice_id,
            "at": args.at,
            "pr": args.pr_number,
        }

    if append_event(slice_id, event):
        print(f"{args.type} イベントを記録しました（slice_id={slice_id}, pr={args.pr_number}）。")
    else:
        print(f"event_id '{event['event_id']}' は記録済み（冪等・スキップ）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
