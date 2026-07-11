#!/usr/bin/env python3
"""
fold.py — スライス進捗イベント列から状態を再構成する純関数（P2・確定ログ §6-2）。

大原則：集計器は Git への投影（projection / read model）。状態は常に
`fold(events, as_of)` から再構成する。**同じ入力には常に同じ出力を返す**
（決定性はテストで担保。P2完了基準「同一 events 列から fold が常に同一
status を返す」）。

状態機械（8イベント型）：
  issued            -> phase="issued"
  submitted         -> phase="submitted"（提出を1件追記。diff/usage を蓄積）
  rescued           -> 救援カウンタ +1（打ち消しは rescue_revoked）
  rescue_revoked    -> 救援カウンタ -1（行は消さず追記で無効化。確定ログ #B）
  rejected          -> rejected_count +1。phase は submitted に戻る（再提出待ち）
  gate(verdict=GO)  -> phase="gated_go"（completed 待ち）
  gate(NO-GO,rework)      -> rework_count +1。phase は submitted に戻る
  gate(NO-GO,redecompose) -> redecompose_count +1（後続の abandoned:split を期待）
  abandoned         -> phase="abandoned"（終端。reason 必須）
  completed         -> phase="completed"（終端）

終端（completed/abandoned）に達したら、以降の非終端イベントは phase を書き換えない
（最初の終端イベントが確定。多重終端は異常データとして無視・上書きしない）。

KPI 6指標（確定ログ §3・P0承認パッケージ #1-8 GO・2026-07-11）は compute_kpis() で算出する。
**「スライス肥大率」の閾値化（何diff行・何日から"肥大"と判定するか）はこのファイルでは決めない。**
承認済みなのは「代理指標として diff行数・所要日数・abandoned:split・NO-GO:redecompose を使う」
ことだけで、具体的な閾値は新たな KPI 定義の決定（CLAUDE.md §7 で PM 承認が要る）。
実データが集まってから較正する（旧 ADR-0008 の golden 閾値と同じ「最初ゆるく→Flywheelで締める」方針）。
そのため compute_kpis() は生の信号（diff行数・所要日数・split/redecompose件数）を返すに留める。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GLOB = "docs/metrics/events/**/*.jsonl"

TERMINAL_PHASES = {"completed", "abandoned"}


@dataclass
class SliceStatus:
    slice_id: int
    phase: str = "unknown"
    abandoned_reason: str | None = None
    issued_at: str | None = None
    settled_at: str | None = None  # completed/abandoned の at（移動平均の順序キー・確定ログ #D）
    rescue_net: int = 0
    rejected_count: int = 0
    rework_count: int = 0
    redecompose_count: int = 0
    diff_add: int = 0
    diff_del: int = 0
    usage_usd: float | None = None
    usage_known: bool = False  # usage_usd が一度でも数値で得られたか（null許容・P0#3）
    completed_pr: int | None = None
    issue: int | None = None

    @property
    def rescued(self) -> bool:
        return self.rescue_net > 0

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "usage_known"}
        d["rescued"] = self.rescued
        return d


def load_events(paths: list[str]) -> list[dict]:
    events: list[dict] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def fold(events: list[dict], as_of: str | None = None) -> dict[int, SliceStatus]:
    """events（順不同でよい）から slice_id ごとの状態を再構成する。

    as_of を指定すると、その時刻以前（`at <= as_of`）のイベントのみを対象にする
    （過去スナップショットの再現に使う。P2完了基準）。
    events は変更しない（純関数。副作用なし）。
    """
    filtered = [e for e in events if as_of is None or e.get("at", "") <= as_of]
    # 時系列順に確定的に並べる（at 昇順。同時刻は event_id で安定ソート）。
    ordered = sorted(filtered, key=lambda e: (e.get("at", ""), e.get("event_id", "")))

    statuses: dict[int, SliceStatus] = {}

    for e in ordered:
        sid = e.get("slice_id")
        if not isinstance(sid, int):
            continue
        s = statuses.setdefault(sid, SliceStatus(slice_id=sid))
        etype = e.get("type")
        at = e.get("at")

        # rescued/rescue_revoked は phase 遷移の外側にある独立軸の台帳なので、
        # 終端（completed/abandoned）後の訂正（例: 完了後に届く /unrescue）も常に反映する。
        # phase を書き換えるイベント種別だけを終端後は無視する（異常データへの防御）。
        if s.phase in TERMINAL_PHASES and etype not in ("completed", "abandoned", "rescued", "rescue_revoked"):
            continue

        if etype == "issued":
            s.phase = "issued"
            s.issued_at = at
            if isinstance(e.get("issue"), int):
                s.issue = e["issue"]
        elif etype == "submitted":
            if s.phase not in TERMINAL_PHASES:
                s.phase = "submitted"
            s.diff_add += e.get("diff_add") or 0
            s.diff_del += e.get("diff_del") or 0
            usage = e.get("usage_usd")
            if isinstance(usage, (int, float)):
                s.usage_usd = (s.usage_usd or 0) + usage
                s.usage_known = True
        elif etype == "rescued":
            s.rescue_net += 1
        elif etype == "rescue_revoked":
            s.rescue_net -= 1
        elif etype == "rejected":
            s.rejected_count += 1
            if s.phase not in TERMINAL_PHASES:
                s.phase = "submitted"
        elif etype == "gate":
            verdict = e.get("verdict")
            kind = e.get("kind")
            if verdict == "GO":
                if s.phase not in TERMINAL_PHASES:
                    s.phase = "gated_go"
            elif verdict == "NO-GO":
                if kind == "rework":
                    s.rework_count += 1
                    if s.phase not in TERMINAL_PHASES:
                        s.phase = "submitted"
                elif kind == "redecompose":
                    s.redecompose_count += 1
        elif etype == "abandoned":
            if s.phase not in TERMINAL_PHASES:
                s.phase = "abandoned"
                s.abandoned_reason = e.get("reason")
                s.settled_at = at
        elif etype == "completed":
            if s.phase not in TERMINAL_PHASES:
                s.phase = "completed"
                s.settled_at = at
                if isinstance(e.get("pr"), int):
                    s.completed_pr = e["pr"]

    return statuses


def compute_kpis(statuses: dict[int, SliceStatus]) -> dict:
    """確定ログ §3／P0承認パッケージ §2（8件GO・2026-07-11）の確定KPI定義に基づく算出。

    「スライス肥大率」は閾値未確定のため raw signal のみ返す（モジュール docstring 参照）。
    """
    values = list(statuses.values())
    completed = [s for s in values if s.phase == "completed"]
    abandoned_failed = [s for s in values if s.phase == "abandoned" and s.abandoned_reason == "failed"]
    abandoned_split = [s for s in values if s.phase == "abandoned" and s.abandoned_reason == "split"]
    abandoned_descoped = [s for s in values if s.phase == "abandoned" and s.abandoned_reason == "descoped"]

    # --- AFK完走率（北極星）: 分子=救援0で完了 / 分母=完了∪abandoned:failed ---
    afk_denominator = len(completed) + len(abandoned_failed)
    afk_numerator = sum(1 for s in completed if not s.rescued)
    afk_completion_rate = (afk_numerator / afk_denominator) if afk_denominator else None

    # --- 差し戻し率: 分子=統合役NG(rejected)+NO-GO:rework の総イベント数 / 分母=完了 ---
    rework_numerator = sum(s.rejected_count + s.rework_count for s in values)
    rework_rate = (rework_numerator / len(completed)) if completed else None

    # --- スライス肥大率: raw signal のみ（閾値は未確定・PM承認待ち） ---
    bloat_signal = {
        "completed_diff_lines": [s.diff_add + s.diff_del for s in completed],
        "abandoned_split_count": len(abandoned_split),
        "redecompose_event_count": sum(s.redecompose_count for s in values),
        "denominator": len(completed) + len(abandoned_split),
        "note": "閾値未確定。diff行数・所要日数から「肥大」と判定する基準はPM未承認（生信号のみ）。",
    }

    # --- 枠効率($/task): 分子=破棄分を含む全消費 / 分母=完了。取得元未定のためnull許容 ---
    usage_known_any = any(s.usage_known for s in values)
    usage_total = sum((s.usage_usd or 0) for s in values if s.usage_known) if usage_known_any else None
    cost_efficiency = (usage_total / len(completed)) if (usage_total is not None and completed) else None

    # --- 指示書進捗: 分子=完了 / 分母=issued − abandoned:descoped ---
    issued_count = sum(1 for s in values if s.issued_at is not None)
    progress_denominator = issued_count - len(abandoned_descoped)
    progress_rate = (len(completed) / progress_denominator) if progress_denominator else None

    return {
        "afk_completion_rate": afk_completion_rate,
        "afk_completion_rate_detail": {"numerator": afk_numerator, "denominator": afk_denominator},
        "rework_rate": rework_rate,
        "rework_rate_detail": {"numerator": rework_numerator, "denominator": len(completed)},
        "slice_bloat_signal": bloat_signal,
        "cost_efficiency_usd_per_task": cost_efficiency,
        "instruction_progress_rate": progress_rate,
        "instruction_progress_detail": {"numerator": len(completed), "denominator": progress_denominator},
        "weekly_completed_count_observed": len(completed),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="events から状態を再構成し KPI を出力する")
    ap.add_argument("--as-of", default=None, help="ISO8601。指定時刻以前のイベントのみで再構成")
    ap.add_argument("files", nargs="*", help="対象 .jsonl（未指定なら既定 glob）")
    args = ap.parse_args()

    if args.files:
        targets = args.files
    else:
        targets = glob.glob(str(REPO_ROOT / DEFAULT_GLOB), recursive=True)

    events = load_events(targets)
    statuses = fold(events, as_of=args.as_of)
    kpis = compute_kpis(statuses)

    print(json.dumps({
        "as_of": args.as_of,
        "slices": {sid: s.to_dict() for sid, s in sorted(statuses.items())},
        "kpis": kpis,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
