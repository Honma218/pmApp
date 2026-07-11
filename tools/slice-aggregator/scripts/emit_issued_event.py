#!/usr/bin/env python3
"""
emit_issued_event.py — docs/slices/slice-NN.md の merge を検知し issued イベントを記録する。

実装ロードマップ P1 §3 項目4／確定ログ #H の実体。
「起票時に確定：webhook で集計器が指示書 frontmatter の slice_id（＋あれば issue）を読み、
issued イベントに載せる」を、指示書が main へマージされた時点で行う。

書き込みは ADR-0012 の制約（bot・パス限定・append-only）に従う:
  - 書き込み先は docs/metrics/events/slice-NNNN.jsonl のみ。
  - 既存行は変更・削除しない（追記のみ）。
  - event_id は決定論的・冪等（"pr-<PR番号>-slice-<slice_id>"）。同一PRの再実行で二重化しない。

終了コード: 0=成功（0件でもOK） / 1=frontmatter不正など検証エラー / 2=実行前提エラー。
CLI:
  python emit_issued_event.py --pr-number N --at ISO8601 [--actor NAME] FILES...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml が必要です → pip install pyyaml", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_DIR = REPO_ROOT / "docs" / "metrics" / "events"


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    raw = text[3:end]
    data = yaml.safe_load(raw)
    return data if isinstance(data, dict) else None


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


def main() -> int:
    ap = argparse.ArgumentParser(description="docs/slices/ マージから issued イベントを生成")
    ap.add_argument("--pr-number", type=int, required=True)
    ap.add_argument("--actor", default="pm")
    ap.add_argument("--at", required=True, help="ISO8601 timestamp（PR の merged_at）")
    ap.add_argument("files", nargs="*", help="変更された docs/slices/slice-*.md")
    args = ap.parse_args()

    if not args.files:
        print("対象ファイルなし。OK。")
        return 0

    errors: list[str] = []
    emitted = 0

    for f in args.files:
        path = Path(f)
        if not path.exists():
            # 削除されたファイルはスキップ（issued の取り消しは対象外）
            continue
        fm = parse_frontmatter(path)
        if fm is None or "slice_id" not in fm:
            errors.append(f"{f}: frontmatter に slice_id が無い（起票イベントを記録できない）")
            continue
        slice_id = fm["slice_id"]
        if not isinstance(slice_id, int) or slice_id < 1:
            errors.append(f"{f}: slice_id は正の整数である必要がある（値: {slice_id!r}）")
            continue

        event_id = f"pr-{args.pr_number}-slice-{slice_id}"
        event: dict = {
            "event_id": event_id,
            "type": "issued",
            "slice_id": slice_id,
            "at": args.at,
            "actor": args.actor,
            "spec_pr": args.pr_number,
        }
        if isinstance(fm.get("issue"), int):
            event["issue"] = fm["issue"]

        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = EVENTS_DIR / f"slice-{slice_id:04d}.jsonl"

        if event_id in existing_event_ids(out_path):
            print(f"{f}: event_id '{event_id}' は記録済み（冪等・スキップ）")
            continue

        with out_path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(event, ensure_ascii=False) + "\n")
        emitted += 1
        print(f"{f}: issued イベントを記録 -> {out_path.relative_to(REPO_ROOT)}")

    if errors:
        print(f"✗ {len(errors)} 件のエラー", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"✓ {emitted} 件の issued イベントを記録")
    return 0


if __name__ == "__main__":
    sys.exit(main())
