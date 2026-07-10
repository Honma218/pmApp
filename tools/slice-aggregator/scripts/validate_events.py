#!/usr/bin/env python3
"""
validate_events.py — スライス進捗イベント（NDJSON）の検証。

集計器の大原則「読むだけ／events は append-only・冪等」を PR 時点で機械保証する。
確定ログ §6-1（欠損を集計時ではなく PR 時に弾く）の実体。

検証する3点:
  1. スキーマ: 各行が slice-event.schema.json に適合するか（1行=1イベント）。
  2. 冪等性: event_id がファイル内で一意か（同一 webhook 再実行の二重行を検出）。
  3. append-only 整合: ファイル名 slice-NNNN.jsonl と各行 slice_id の一致／時刻 at の単調非減少。

終了コード: 0=全緑 / 1=検証失敗 / 2=実行前提エラー（依存欠落・ファイル不在）。
CLI:
  python validate_events.py [--schema PATH] FILES...
  未指定時は docs/metrics/events/**/*.jsonl を対象にする。
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from jsonschema import FormatChecker
except ImportError:
    print("ERROR: jsonschema が必要です → pip install jsonschema", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "slice-event.schema.json"
DEFAULT_GLOB = "docs/metrics/events/**/*.jsonl"
FNAME_RE = re.compile(r"^slice-(\d{4,})\.jsonl$")


def load_schema(path: Path) -> Draft202012Validator:
    with path.open(encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_file(path: Path, validator: Draft202012Validator) -> list[str]:
    errors: list[str] = []
    rel = path.name

    m = FNAME_RE.match(rel)
    expected_slice = int(m.group(1)) if m else None
    if expected_slice is None:
        errors.append(f"{rel}: ファイル名が slice-NNNN.jsonl 形式でない")

    seen_ids: dict[str, int] = {}
    prev_at: str | None = None

    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue  # 空行は許容
            # 1. パース
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{rel}:{lineno}: JSON パース不能: {e}")
                continue
            # 2. スキーマ
            for err in sorted(validator.iter_errors(event), key=lambda e: e.path):
                loc = "/".join(str(p) for p in err.path) or "(root)"
                errors.append(f"{rel}:{lineno}: schema [{loc}] {err.message}")
            # 3. 冪等性（event_id 一意）
            eid = event.get("event_id")
            if isinstance(eid, str):
                if eid in seen_ids:
                    errors.append(
                        f"{rel}:{lineno}: event_id 重複 '{eid}'（初出 line {seen_ids[eid]}）"
                        f" — 冪等性違反"
                    )
                else:
                    seen_ids[eid] = lineno
            # 4. ファイル名 slice_id 整合
            sid = event.get("slice_id")
            if expected_slice is not None and isinstance(sid, int) and sid != expected_slice:
                errors.append(
                    f"{rel}:{lineno}: slice_id={sid} がファイル名 slice-{expected_slice:04d} と不一致"
                )
            # 5. append-only の時刻単調性（at 非減少）
            at = event.get("at")
            if isinstance(at, str):
                if prev_at is not None and at < prev_at:
                    errors.append(
                        f"{rel}:{lineno}: at='{at}' が前行 '{prev_at}' より過去 — "
                        f"append-only の時刻逆転"
                    )
                prev_at = at

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="スライス進捗イベント(NDJSON)の検証")
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("files", nargs="*", help="検証対象 .jsonl（未指定なら既定 glob）")
    args = ap.parse_args()

    if not args.schema.exists():
        print(f"ERROR: スキーマが見つからない: {args.schema}", file=sys.stderr)
        return 2
    validator = load_schema(args.schema)

    if args.files:
        targets = [Path(p) for p in args.files]
    else:
        targets = [Path(p) for p in glob.glob(str(REPO_ROOT / DEFAULT_GLOB), recursive=True)]

    if not targets:
        print("検証対象の .jsonl なし（events が未生成）。OK。")
        return 0

    all_errors: list[str] = []
    for path in sorted(targets):
        if not path.exists():
            all_errors.append(f"{path}: ファイル不在")
            continue
        all_errors.extend(validate_file(path, validator))

    if all_errors:
        print(f"✗ 検証失敗: {len(all_errors)} 件", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"✓ {len(targets)} ファイル検証 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
