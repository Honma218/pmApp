#!/usr/bin/env python3
"""
handle_rescue_comment.py — /rescue・/unrescue コメントから rescued/rescue_revoked イベントを生成する。

実装ロードマップ P3／確定ログ #B の実体。GitHub Actions（issue_comment）から
**環境変数経由で**呼ばれる（コメント本文を shell 展開・argv に晒さないため。script injection 対策。
ADR-0012／P3セキュリティ完了基準）。

slice_id 解決の優先順位（確定ログ #B）:
  1. コメント内の `--slice <N>` 明示
  2. PR コメントなら head ブランチ名 `feature/slice-<N>-*` から抽出
  3. issue コメントなら issue 本文の `docs/slices/slice-<N>` 参照から抽出
  解決不能なら**記録せず**終了する（誤記録 > 記録漏れ、の非対称性・確定ログ #B）。

書き込みは ADR-0012 の制約（bot・パス限定・append-only）に従う。
event_id は "gh-comment-<comment.id>" で決定論的・冪等（同一コメントの再実行で二重化しない）。
at はコメントの created_at（実行時刻ではない）。

**呼び出し前提**：ワークフロー側の job `if:`（`startsWith(comment.body, '/rescue')` 等）で
既に `/rescue`・`/unrescue` コメントだけに絞り込まれた後に呼ばれる。このスクリプト内の
コマンド判定は防御的なフォールバックに過ぎない。

終了コード:
  0 = 正常に処理した（記録 or 同一コメントの再実行による冪等スキップ）
  1 = 解決失敗・入力不正（対象コマンドでない・slice_id不明・reason空 等）。記録しない
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
BRANCH_SLICE_RE = re.compile(r"feature/slice-0*(\d+)")
ISSUE_BODY_SLICE_RE = re.compile(r"docs/slices/slice-0*(\d+)")
ISSUE_BODY_FALLBACK_RE = re.compile(r"slice[-_]0*(\d+)")

NOT_A_COMMAND = "対象コマンドではない"


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


def extract_command_and_reason(body: str) -> tuple[str, str] | None:
    """先頭行から /rescue または /unrescue と、--slice を除いた理由文を取り出す。"""
    stripped = body.strip()
    if not stripped:
        return None
    first_line = stripped.splitlines()[0].strip()
    if first_line.startswith("/unrescue"):
        cmd = "unrescue"
        rest = first_line[len("/unrescue"):]
    elif first_line.startswith("/rescue"):
        cmd = "rescue"
        rest = first_line[len("/rescue"):]
    else:
        return None
    rest = SLICE_ID_FLAG_RE.sub("", rest).strip()
    return cmd, rest


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

    parsed = extract_command_and_reason(body)
    if parsed is None:
        # 通常ここには来ない（呼び出し前提のワークフロー側 if で既にフィルタ済み）。防御的フォールバック。
        print(NOT_A_COMMAND)
        return 1
    cmd, reason = parsed

    comment_id = os.environ.get("COMMENT_ID", "")
    actor = os.environ.get("COMMENT_AUTHOR", "")
    at = os.environ.get("COMMENT_CREATED_AT", "")
    source = os.environ.get("COMMENT_HTML_URL", "")
    if not comment_id or not actor or not at or not source:
        print("実行前提エラー: COMMENT_ID/COMMENT_AUTHOR/COMMENT_CREATED_AT/COMMENT_HTML_URL が必要", file=sys.stderr)
        return 2

    pr_head_ref = os.environ.get("PR_HEAD_REF") or None
    issue_body = os.environ.get("ISSUE_BODY") or None

    slice_id = resolve_slice_id(body, pr_head_ref, issue_body)
    if slice_id is None:
        print(
            "slice_id を特定できませんでした。`--slice <番号>` を付けて打ち直してください "
            "（例: `/rescue --slice 7 環境変数の置き場所が分からず`）。"
        )
        return 1

    if cmd == "rescue" and not reason:
        print("理由が空です。`/rescue <理由>` の形式で1文書いてください。")
        return 1

    event_id = f"gh-comment-{comment_id}"
    event: dict = {
        "event_id": event_id,
        "type": "rescued" if cmd == "rescue" else "rescue_revoked",
        "slice_id": slice_id,
        "at": at,
        "actor": actor,
        "source": source,
    }
    if cmd == "rescue":
        event["note"] = reason

    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVENTS_DIR / f"slice-{slice_id:04d}.jsonl"

    if event_id in existing_event_ids(out_path):
        print(f"event_id '{event_id}' は記録済み（冪等・スキップ）")
        return 0

    with out_path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(event, ensure_ascii=False) + "\n")

    verb = "救援を記録しました" if cmd == "rescue" else "救援の打ち消しを記録しました"
    print(f"{verb}（slice_id={slice_id}）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
