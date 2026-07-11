#!/usr/bin/env python3
"""
generate_gates_log.py — gate イベントから docs/metrics/gates.md の判定ログ表を生成する（slice-02）。

docs/metrics/gates.md はこれまで「PM が手で書く任意ログ」と「KPI 計算が読む gate イベント」の
**二重管理**になっていた（docs/memory-bank/pending-gate-before-merge-procedure.md で発見）。
本スクリプトは docs/metrics/index/slice-map.json と同じ「events から生成する派生物」として
gates.md を再生成する。**手動編集は禁止**（日次cronの度に上書きされる）。

「代理」「備考」列は旧手動フォーマットにあったが gate イベントのスキーマに存在しないため、
生成表には含めない（イベントに無い情報を捏造しない）。`by` 列で記録者は分かる。

終了コード: 0=成功。
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fold import load_events  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_GLOB = "docs/metrics/events/**/*.jsonl"
GATES_MD_PATH = REPO_ROOT / "docs" / "metrics" / "gates.md"

HEADER = """# 層境ゲート判定ログ（ADR-0007 / 改訂 2026-07-11）

> **status: 生成物（slice-02・2026-07-11）。手動編集しないこと。**
> `docs/metrics/events/**` の `gate` イベントから日次cronが再生成する
> （`docs/metrics/index/slice-map.json` と同じ扱い）。判定は `/gate GO` 等のコメント
> コマンドで記録する（`tools/slice-aggregator/README.md` 参照）。

全 PR に層境ゲートが掛かる（ADR-0007）。**判定者は PM**（代理はリーダー1名。`GATE_KEEPERS` で強制）。
**NO-GO のときは種別（`rework`/`redecompose`）が必須**——`/gate` コマンド自体が入力を強制する
（ADR-0007 改訂の実体）。

## 記録ルール

- `rework` … 修正で足りる。**同一 slice_id を継続**。→ 差し戻し率の分子。
- `redecompose` … 分解し直し。**子スライスを新規 slice_id で起票**。→ 肥大率側（分解の失敗）。
- 種別を分けるのは、両者の原因が異なる（実装の雑さ vs 分解の雑さ）ため。混ぜると CLAUDE.md §3 の2分類原則が働かない。

## 判定ログ（`gate` イベントから生成。手動編集しないこと）
"""


def build_rows(events: list[dict]) -> list[dict]:
    """gate イベントを at 昇順で行データに変換する（純関数）。"""
    gate_events = [e for e in events if e.get("type") == "gate"]
    gate_events.sort(key=lambda e: (e.get("at") or "", e.get("event_id") or ""))
    rows = []
    for e in gate_events:
        at = e.get("at") or ""
        rows.append({
            "slice_id": e.get("slice_id"),
            "date": at[:10] if len(at) >= 10 else at,
            "verdict": e.get("verdict") or "",
            "kind": e.get("kind") or "",
            "by": e.get("by") or "",
        })
    return rows


def render_markdown(rows: list[dict]) -> str:
    lines = [
        HEADER,
        "| slice_id | 日付 | 判定 | NO-GO種別 | PM/代理 |",
        "|---|---|---|---|---|",
    ]
    if rows:
        for r in rows:
            lines.append(f"| {r['slice_id']} | {r['date']} | {r['verdict']} | {r['kind']} | {r['by']} |")
    else:
        lines.append("| | | | | |")
    lines.append("")
    return "\n".join(lines)


def generate(events: list[dict]) -> str:
    """events -> gates.md 全文（純関数。決定的）。"""
    return render_markdown(build_rows(events))


def main() -> int:
    events = load_events(glob.glob(str(REPO_ROOT / EVENTS_GLOB), recursive=True))
    md = generate(events)
    GATES_MD_PATH.write_text(md, encoding="utf-8")
    gate_count = sum(1 for e in events if e.get("type") == "gate")
    print(f"gates.md を再生成しました（gate イベント {gate_count} 件）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
