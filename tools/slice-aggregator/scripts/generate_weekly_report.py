#!/usr/bin/env python3
"""
generate_weekly_report.py — 週次 Markdown レポートを生成する（P5 ③）。

Harness-Keeper が読む。直近5スライスの移動平均（CONTEXT.md の AFK完走率の定義）と、
Flywheel 観察項目（差し戻し・肥大シグナルのあるスライス）を自動抽出する。

同じ ISO週（YYYY-Www。as_of から導出）のファイルは日次cronのたびに上書きする
（週の途中でも最新化される。確定ログ #J：集約の書き手は日次cron1本だけ）。

終了コード: 0=成功 / 2=実行前提エラー。
"""
from __future__ import annotations

import argparse
import glob
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fold import load_events, fold, compute_kpis, SliceStatus  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_GLOB = "docs/metrics/events/**/*.jsonl"
WEEKLY_DIR = REPO_ROOT / "docs" / "status" / "weekly"

MOVING_AVERAGE_WINDOW = 5


def parse_as_of(as_of: str) -> datetime:
    return datetime.fromisoformat(as_of.replace("Z", "+00:00"))


def iso_week_str(as_of: str) -> str:
    year, week, _ = parse_as_of(as_of).isocalendar()
    return f"{year}-W{week:02d}"


def last_n_afk_rate(statuses: dict[int, SliceStatus], n: int = MOVING_AVERAGE_WINDOW) -> dict:
    """CONTEXT.md「AFK完走率は直近5スライスの移動平均で見る」の実体。
    分母は settled（completed または abandoned:failed）したスライスの直近 n 件。
    """
    settled = [
        s for s in statuses.values()
        if s.settled_at and (s.phase == "completed" or (s.phase == "abandoned" and s.abandoned_reason == "failed"))
    ]
    settled.sort(key=lambda s: s.settled_at)
    window = settled[-n:]
    denom = len(window)
    numer = sum(1 for s in window if s.phase == "completed" and not s.rescued)
    return {
        "window_size": denom,
        "numerator": numer,
        "rate": (numer / denom) if denom else None,
    }


def flywheel_observations(statuses: dict[int, SliceStatus]) -> list[str]:
    """差し戻し・肥大シグナルのあるスライスを Harness-Keeper 向けに列挙する。"""
    obs: list[str] = []
    for sid, s in sorted(statuses.items()):
        flags = []
        if s.rejected_count:
            flags.append(f"統合役NG {s.rejected_count}回")
        if s.rework_count:
            flags.append(f"NO-GO:rework {s.rework_count}回")
        if s.redecompose_count:
            flags.append(f"NO-GO:redecompose {s.redecompose_count}回")
        if s.phase == "abandoned" and s.abandoned_reason == "failed":
            flags.append("abandoned:failed")
        if flags:
            obs.append(f"- slice_id={sid}: {', '.join(flags)}")
    return obs


def fmt_rate(x) -> str:
    return f"{x:.1%}" if isinstance(x, (int, float)) else "null"


def render_markdown(iso_week: str, as_of: str, kpis: dict, moving_avg: dict, observations: list[str]) -> str:
    lines: list[str] = [
        f"# 週次ステータス — {iso_week}",
        "",
        f"as_of: {as_of}",
        "",
        "## KPI（累計）",
        "",
        f"- AFK完走率: {fmt_rate(kpis['afk_completion_rate'])}"
        f"（{kpis['afk_completion_rate_detail']['numerator']}"
        f"/{kpis['afk_completion_rate_detail']['denominator']}）",
        f"- 差し戻し率: {fmt_rate(kpis['rework_rate'])}"
        f"（{kpis['rework_rate_detail']['numerator']}/{kpis['rework_rate_detail']['denominator']}）",
        f"- 指示書進捗: {fmt_rate(kpis['instruction_progress_rate'])}"
        f"（{kpis['instruction_progress_detail']['numerator']}"
        f"/{kpis['instruction_progress_detail']['denominator']}）",
        "- 枠効率($/task): "
        + (
            f"{kpis['cost_efficiency_usd_per_task']:.2f}"
            if kpis["cost_efficiency_usd_per_task"] is not None
            else "null（取得元未定）"
        ),
        f"- 週次消化件数（観察）: {kpis['weekly_completed_count_observed']}",
        "",
        "## AFK完走率（直近5スライスの移動平均・北極星指標）",
        "",
    ]
    if moving_avg["window_size"]:
        lines.append(
            f"直近{moving_avg['window_size']}件中 {moving_avg['numerator']}件が救援なしで完了"
            f"（{fmt_rate(moving_avg['rate'])}）。"
        )
    else:
        lines.append("まだ完了・断念したスライスが無く算出不可。")
    lines += [
        "",
        "## スライス肥大率（生信号・閾値未確定）",
        "",
        f"- 完了スライスのdiff行数: {kpis['slice_bloat_signal']['completed_diff_lines']}",
        f"- abandoned:split件数: {kpis['slice_bloat_signal']['abandoned_split_count']}",
        f"- NO-GO:redecompose件数: {kpis['slice_bloat_signal']['redecompose_event_count']}",
        "",
        "## Flywheel 観察項目（差し戻し・肥大シグナルのあるスライス）",
        "",
    ]
    lines += observations if observations else ["（観察対象なし）"]
    lines.append("")
    return "\n".join(lines)


def generate(as_of: str, events: list[dict]) -> tuple[str, str]:
    """(iso_week, markdown) を返す純関数（テスト容易性のため I/O を分離）。"""
    statuses = fold(events, as_of=as_of)
    kpis = compute_kpis(statuses)
    moving_avg = last_n_afk_rate(statuses)
    observations = flywheel_observations(statuses)
    week = iso_week_str(as_of)
    md = render_markdown(week, as_of, kpis, moving_avg, observations)
    return week, md


def main() -> int:
    ap = argparse.ArgumentParser(description="週次レポートを生成する")
    ap.add_argument("--as-of", required=True, help="ISO8601。再現性のため呼び出し側が固定して渡す")
    args = ap.parse_args()

    try:
        parse_as_of(args.as_of)
    except ValueError as e:
        print(f"ERROR: --as-of の形式が不正: {e}", file=sys.stderr)
        return 2

    events = load_events(glob.glob(str(REPO_ROOT / EVENTS_GLOB), recursive=True))
    week, md = generate(args.as_of, events)

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    (WEEKLY_DIR / f"{week}.md").write_text(md, encoding="utf-8")

    print(f"weekly/{week}.md を生成しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
