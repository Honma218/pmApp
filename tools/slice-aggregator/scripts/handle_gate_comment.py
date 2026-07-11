#!/usr/bin/env python3
"""
handle_gate_comment.py — /gate・/reject・/abandon コメントから gate/rejected/abandoned
イベントを生成する。

`/rescue`（handle_rescue_comment.py）と同じ信頼モデル（コメントコマンド・env経由での
本文受け渡し・allowlist・bot直コミット）を、層境ゲート（PMのGO/NO-GO）・統合役の再検証NG・
破棄判定に拡張する。判定者が誰であるべきかは CLAUDE.md §7 に従い、呼び出し側ワークフローの
allowlist（GATE_KEEPERS。PM限定）で強制する——このスクリプト自体は認可を判断しない。

コマンド:
  /gate GO                       -> type=gate, verdict=GO
  /gate NO-GO --kind rework      -> type=gate, verdict=NO-GO, kind=rework（差し戻し率の分子）
  /gate NO-GO --kind redecompose -> type=gate, verdict=NO-GO, kind=redecompose（肥大率側）
  /reject <理由>                  -> type=rejected, reason=<理由>（統合役NG。差し戻し率の分子）
  /abandon --reason split|descoped|failed -> type=abandoned, reason=<reason>
      split      … 分解し直し（親を破棄・子を新規起票。通常 /gate NO-GO --kind redecompose とセット）
      descoped   … 要らないと判明（分母から除外・指示書進捗の計算対象外）
      failed     … 緑に至らず断念（ハーネスの欠陥。AFK完走率の分母に算入・確定ログ #D）

slice_id 解決の優先順位は /rescue と同じ（確定ログ #B 相当）：
  1. コメント内の --slice <N> 明示
  2. PR コメントなら head ブランチ名 feature/slice-<N>-* から抽出
  3. issue コメントなら issue 本文の docs/slices/slice-<N> 参照から抽出
  解決不能・verdict不正・kind欠落なら**記録せず**終了する（誤記録 > 記録漏れ、の非対称性）。

**呼び出し前提**：ワークフロー側の job `if:`（startsWith(comment.body, '/gate') 等）で
既に対象コメントに絞り込まれ、allowlist チェックも通過した後に呼ばれる。

終了コード:
  0 = 正常に処理した（記録 or 同一コメントの再実行による冪等スキップ）
  1 = 解決失敗・入力不正（対象コマンドでない・slice_id不明・verdict/kind不正・reason空 等）
  2 = 実行前提エラー（必須環境変数の欠落）
標準出力: ワークフロー側がコメント返信にそのまま使うメッセージ（最終行）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_DIR = REPO_ROOT / "docs" / "metrics" / "events"

SLICE_ID_FLAG_RE = re.compile(r"--slice[= ]+(\d+)")
KIND_FLAG_RE = re.compile(r"--kind[= ]+(rework|redecompose)")
REASON_FLAG_RE = re.compile(r"--reason[= ]+(split|descoped|failed)")
BRANCH_SLICE_RE = re.compile(r"feature/slice-0*(\d+)")
ISSUE_BODY_SLICE_RE = re.compile(r"docs/slices/slice-0*(\d+)")
ISSUE_BODY_FALLBACK_RE = re.compile(r"slice[-_]0*(\d+)")


def resolve_slice_id(body: str, pr_head_ref: str | None, issue_body: str | None) -> int | None:
    m = SLICE_ID_FLAG_RE.search(body)
    if m:
        return int(m.group(1))
    if pr_head_ref:
        m = BRANCH_SLICE_RE.search(pr_head_ref)
        if m:
            return int(m.group(1))
    if issue_body:
        m = ISSUE_BODY_SLICE_RE.search(issue_body)
        if m:
            return int(m.group(1))
        m = ISSUE_BODY_FALLBACK_RE.search(issue_body)
        if m:
            return int(m.group(1))
    return None


def parse_command(body: str) -> dict | None:
    """先頭行をコマンドとして解釈する。対象外なら None、対象だが不正なら error キー付き dict。"""
    stripped = body.strip()
    if not stripped:
        return None
    first_line = stripped.splitlines()[0].strip()

    if first_line.startswith("/gate"):
        rest = first_line[len("/gate"):]
        kind_match = KIND_FLAG_RE.search(rest)
        rest_wo_flags = KIND_FLAG_RE.sub("", rest)
        rest_wo_flags = SLICE_ID_FLAG_RE.sub("", rest_wo_flags).strip()
        tokens = rest_wo_flags.split()
        verdict_token = tokens[0].upper() if tokens else ""
        if verdict_token not in ("GO", "NO-GO"):
            return {"type": "gate", "error": f"verdict は GO か NO-GO のいずれか（受け取った値: '{verdict_token}'）"}
        result: dict = {"type": "gate", "verdict": verdict_token}
        if verdict_token == "NO-GO":
            if not kind_match:
                return {"type": "gate", "error": "NO-GO には `--kind rework` か `--kind redecompose` が必須"}
            result["kind"] = kind_match.group(1)
        return result

    if first_line.startswith("/reject"):
        rest = first_line[len("/reject"):]
        rest = SLICE_ID_FLAG_RE.sub("", rest).strip()
        if not rest:
            return {"type": "rejected", "error": "理由が空です。`/reject <理由>` の形式で書いてください。"}
        return {"type": "rejected", "reason": rest}

    if first_line.startswith("/abandon"):
        rest = first_line[len("/abandon"):]
        reason_match = REASON_FLAG_RE.search(rest)
        if not reason_match:
            return {
                "type": "abandoned",
                "error": "`--reason split` か `--reason descoped` か `--reason failed` が必須",
            }
        return {"type": "abandoned", "reason": reason_match.group(1)}

    return None


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
    body = os.environ.get("COMMENT_BODY", "")

    parsed = parse_command(body)
    if parsed is None:
        # 通常ここには来ない（呼び出し前提のワークフロー側 if で既にフィルタ済み）。防御的フォールバック。
        print("対象コマンドではない（/gate, /reject, /abandon のいずれでもない）")
        return 1
    if "error" in parsed:
        print(parsed["error"])
        return 1

    comment_id = os.environ.get("COMMENT_ID", "")
    actor = os.environ.get("COMMENT_AUTHOR", "")
    at = os.environ.get("COMMENT_CREATED_AT", "")
    if not comment_id or not actor or not at:
        print("実行前提エラー: COMMENT_ID/COMMENT_AUTHOR/COMMENT_CREATED_AT が必要", file=sys.stderr)
        return 2

    pr_head_ref = os.environ.get("PR_HEAD_REF") or None
    issue_body = os.environ.get("ISSUE_BODY") or None

    slice_id = resolve_slice_id(body, pr_head_ref, issue_body)
    if slice_id is None:
        print(
            "slice_id を特定できませんでした。`--slice <番号>` を付けて打ち直してください "
            "（例: `/gate GO --slice 7`）。"
        )
        return 1

    event_id = f"gh-comment-{comment_id}"
    event: dict = {
        "event_id": event_id,
        "type": parsed["type"],
        "slice_id": slice_id,
        "at": at,
        "by": actor,
    }
    if parsed["type"] == "gate":
        event["verdict"] = parsed["verdict"]
        if "kind" in parsed:
            event["kind"] = parsed["kind"]
    else:
        event["reason"] = parsed["reason"]

    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVENTS_DIR / f"slice-{slice_id:04d}.jsonl"

    if event_id in existing_event_ids(out_path):
        print(f"event_id '{event_id}' は記録済み（冪等・スキップ）")
        return 0

    with out_path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(event, ensure_ascii=False) + "\n")

    if parsed["type"] == "gate":
        if "kind" in parsed:
            verb = f"層境ゲート判定を記録しました（{parsed['verdict']}・{parsed['kind']}）"
        else:
            verb = f"層境ゲート判定を記録しました（{parsed['verdict']}）"
    elif parsed["type"] == "rejected":
        verb = "差し戻し（統合役NG）を記録しました"
    else:
        verb = f"破棄を記録しました（{parsed['reason']}）"
    print(f"{verb}（slice_id={slice_id}）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
