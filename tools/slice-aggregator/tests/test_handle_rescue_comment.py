"""
test_handle_rescue_comment.py — /rescue・/unrescue コメント処理のテスト（P3）。

確定ログ #B のセキュリティ・解決優先順位・冪等性を検証する。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"

spec = importlib.util.spec_from_file_location("handle_rescue_comment", SCRIPTS_DIR / "handle_rescue_comment.py")
hrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hrc)  # type: ignore[union-attr]


# --- 純関数: extract_command_and_reason ---

def test_extract_rescue_with_reason():
    assert hrc.extract_command_and_reason("/rescue 環境変数の置き場所が分からず") == ("rescue", "環境変数の置き場所が分からず")


def test_extract_rescue_strips_slice_flag_from_reason():
    cmd, reason = hrc.extract_command_and_reason("/rescue --slice 7 環境変数の置き場所が分からず")
    assert cmd == "rescue"
    assert reason == "環境変数の置き場所が分からず"


def test_extract_unrescue():
    assert hrc.extract_command_and_reason("/unrescue 誤記録でした") == ("unrescue", "誤記録でした")


def test_extract_non_command_returns_none():
    assert hrc.extract_command_and_reason("これはただのコメントです") is None
    assert hrc.extract_command_and_reason("") is None
    assert hrc.extract_command_and_reason("   ") is None


def test_extract_uses_first_line_only():
    body = "/rescue 一文目の理由\n本文の続き\nさらに続く"
    cmd, reason = hrc.extract_command_and_reason(body)
    assert reason == "一文目の理由"


# --- 純関数: resolve_slice_id（確定ログ #B の優先順位） ---

def test_resolve_explicit_flag_wins_over_branch_and_issue():
    sid = hrc.resolve_slice_id("--slice 9 理由", pr_head_ref="feature/slice-3-foo", issue_body="docs/slices/slice-5.md")
    assert sid == 9


def test_resolve_from_pr_branch():
    sid = hrc.resolve_slice_id("/rescue 理由", pr_head_ref="feature/slice-0007-events-schema", issue_body=None)
    assert sid == 7


def test_resolve_from_issue_body():
    sid = hrc.resolve_slice_id(
        "/rescue 理由", pr_head_ref=None,
        issue_body="slice-01-report-create\n指示書: docs/slices/slice-01.md（main）",
    )
    assert sid == 1


def test_resolve_unresolvable_returns_none():
    sid = hrc.resolve_slice_id("/rescue 理由", pr_head_ref="feature/unrelated-branch", issue_body="関係ない本文")
    assert sid is None


# --- main() の統合テスト（環境変数経由・スクリプトの本来の呼ばれ方） ---

def run_main(body, **env_overrides):
    env = {
        "COMMENT_BODY": body,
        "COMMENT_ID": "123",
        "COMMENT_AUTHOR": "leader-taro",
        "COMMENT_CREATED_AT": "2026-07-20T10:00:00Z",
        "COMMENT_HTML_URL": "https://github.com/x/y/pull/1#issuecomment-123",
    }
    env.update(env_overrides)
    old = {k: os.environ.get(k) for k in env}
    old_pr = os.environ.get("PR_HEAD_REF")
    old_issue = os.environ.get("ISSUE_BODY")
    os.environ.update(env)
    try:
        return hrc.main()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if old_pr is None:
            os.environ.pop("PR_HEAD_REF", None)
        if old_issue is None:
            os.environ.pop("ISSUE_BODY", None)


def read_events(slice_id, events_dir):
    path = events_dir / f"slice-{slice_id:04d}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_main_records_rescued_event(tmp_path, monkeypatch):
    monkeypatch.setattr(hrc, "EVENTS_DIR", tmp_path)
    rc = run_main("/rescue --slice 7 環境変数の置き場所が分からず")
    assert rc == 0
    events = read_events(7, tmp_path)
    assert len(events) == 1
    assert events[0] == {
        "event_id": "gh-comment-123",
        "type": "rescued",
        "slice_id": 7,
        "at": "2026-07-20T10:00:00Z",
        "actor": "leader-taro",
        "source": "https://github.com/x/y/pull/1#issuecomment-123",
        "note": "環境変数の置き場所が分からず",
    }


def test_main_is_idempotent_on_same_comment_id(tmp_path, monkeypatch):
    monkeypatch.setattr(hrc, "EVENTS_DIR", tmp_path)
    run_main("/rescue --slice 7 理由その1")
    rc = run_main("/rescue --slice 7 理由その1")  # 同一 COMMENT_ID の再実行（ワークフロー再実行を想定）
    assert rc == 0
    events = read_events(7, tmp_path)
    assert len(events) == 1  # 二重化しない


def test_main_unrescue_without_resolvable_slice_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(hrc, "EVENTS_DIR", tmp_path)
    rc = run_main("/unrescue 打ち消し", **{"COMMENT_ID": "456"})
    # このコメントには --slice も PR_HEAD_REF も ISSUE_BODY も無いので解決できず記録されない
    assert rc == 1
    assert list(tmp_path.iterdir()) == []


def test_main_unrescue_with_explicit_slice(tmp_path, monkeypatch):
    monkeypatch.setattr(hrc, "EVENTS_DIR", tmp_path)
    rc = run_main("/unrescue --slice 7 打ち消し", **{"COMMENT_ID": "789"})
    assert rc == 0
    events = read_events(7, tmp_path)
    assert len(events) == 1
    assert events[0]["type"] == "rescue_revoked"
    assert "note" not in events[0]


def test_main_unresolvable_slice_id_fails_without_recording(tmp_path, monkeypatch):
    monkeypatch.setattr(hrc, "EVENTS_DIR", tmp_path)
    rc = run_main("/rescue 番号なしの理由")
    assert rc == 1
    assert list(tmp_path.iterdir()) == []  # 何も書き込まれない（誤記録より記録漏れを許容）


def test_main_empty_reason_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(hrc, "EVENTS_DIR", tmp_path)
    rc = run_main("/rescue --slice 7")
    assert rc == 1
    assert list(tmp_path.iterdir()) == []


def test_main_resolves_via_pr_head_ref(tmp_path, monkeypatch):
    monkeypatch.setattr(hrc, "EVENTS_DIR", tmp_path)
    rc = run_main("/rescue 分岐名から解決", PR_HEAD_REF="feature/slice-0012-foo")
    assert rc == 0
    events = read_events(12, tmp_path)
    assert len(events) == 1
