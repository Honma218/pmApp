"""
test_handle_gate_comment.py — /gate・/reject コメント処理のテスト（P6準備）。
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("handle_gate_comment", SCRIPTS_DIR / "handle_gate_comment.py")
hgc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hgc)  # type: ignore[union-attr]


# --- parse_command ---

def test_parse_gate_go():
    assert hgc.parse_command("/gate GO") == {"type": "gate", "verdict": "GO"}


def test_parse_gate_go_lowercase():
    assert hgc.parse_command("/gate go") == {"type": "gate", "verdict": "GO"}


def test_parse_gate_nogo_rework():
    assert hgc.parse_command("/gate NO-GO --kind rework") == {"type": "gate", "verdict": "NO-GO", "kind": "rework"}


def test_parse_gate_nogo_redecompose_flag_order_independent():
    assert hgc.parse_command("/gate --kind redecompose NO-GO") == {
        "type": "gate", "verdict": "NO-GO", "kind": "redecompose",
    }


def test_parse_gate_nogo_without_kind_errors():
    result = hgc.parse_command("/gate NO-GO")
    assert result["type"] == "gate"
    assert "kind" in result["error"]


def test_parse_gate_invalid_verdict_errors():
    result = hgc.parse_command("/gate MAYBE")
    assert "error" in result


def test_parse_reject_with_reason():
    assert hgc.parse_command("/reject 範囲外ファイルが含まれている") == {
        "type": "rejected", "reason": "範囲外ファイルが含まれている",
    }


def test_parse_reject_empty_reason_errors():
    result = hgc.parse_command("/reject")
    assert result["type"] == "rejected"
    assert "理由" in result["error"]


def test_parse_non_command_returns_none():
    assert hgc.parse_command("ただのコメント") is None
    assert hgc.parse_command("") is None


def test_parse_strips_slice_flag_from_gate():
    assert hgc.parse_command("/gate GO --slice 7") == {"type": "gate", "verdict": "GO"}


# --- resolve_slice_id（/rescue と同じ優先順位） ---

def test_resolve_explicit_flag_wins():
    assert hgc.resolve_slice_id("--slice 9", pr_head_ref="feature/slice-3-foo", issue_body=None) == 9


def test_resolve_from_pr_branch():
    assert hgc.resolve_slice_id("/gate GO", pr_head_ref="feature/slice-0007-x", issue_body=None) == 7


def test_resolve_unresolvable_returns_none():
    assert hgc.resolve_slice_id("/gate GO", pr_head_ref="feature/unrelated", issue_body=None) is None


# --- main() 統合テスト ---

def run_main(body, **env_overrides):
    env = {
        "COMMENT_BODY": body,
        "COMMENT_ID": "500",
        "COMMENT_AUTHOR": "pm",
        "COMMENT_CREATED_AT": "2026-07-20T10:00:00Z",
    }
    env.update(env_overrides)
    old = {k: os.environ.get(k) for k in env}
    old_pr = os.environ.get("PR_HEAD_REF")
    old_issue = os.environ.get("ISSUE_BODY")
    os.environ.update(env)
    try:
        return hgc.main()
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


def test_main_records_gate_go(tmp_path, monkeypatch):
    monkeypatch.setattr(hgc, "EVENTS_DIR", tmp_path)
    rc = run_main("/gate GO --slice 7")
    assert rc == 0
    events = read_events(7, tmp_path)
    assert events[0] == {
        "event_id": "gh-comment-500",
        "type": "gate",
        "slice_id": 7,
        "at": "2026-07-20T10:00:00Z",
        "by": "pm",
        "verdict": "GO",
    }


def test_main_records_gate_nogo_with_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(hgc, "EVENTS_DIR", tmp_path)
    rc = run_main("/gate NO-GO --kind redecompose --slice 7")
    assert rc == 0
    events = read_events(7, tmp_path)
    assert events[0]["verdict"] == "NO-GO"
    assert events[0]["kind"] == "redecompose"


def test_main_records_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(hgc, "EVENTS_DIR", tmp_path)
    rc = run_main("/reject 範囲外ファイル --slice 7")
    assert rc == 0
    events = read_events(7, tmp_path)
    assert events[0] == {
        "event_id": "gh-comment-500",
        "type": "rejected",
        "slice_id": 7,
        "at": "2026-07-20T10:00:00Z",
        "by": "pm",
        "reason": "範囲外ファイル",
    }


def test_main_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(hgc, "EVENTS_DIR", tmp_path)
    run_main("/gate GO --slice 7")
    rc = run_main("/gate GO --slice 7")
    assert rc == 0
    assert len(read_events(7, tmp_path)) == 1


def test_main_nogo_without_kind_fails_without_recording(tmp_path, monkeypatch):
    monkeypatch.setattr(hgc, "EVENTS_DIR", tmp_path)
    rc = run_main("/gate NO-GO --slice 7")
    assert rc == 1
    assert list(tmp_path.iterdir()) == []


def test_main_unresolvable_slice_fails_without_recording(tmp_path, monkeypatch):
    monkeypatch.setattr(hgc, "EVENTS_DIR", tmp_path)
    rc = run_main("/gate GO")
    assert rc == 1
    assert list(tmp_path.iterdir()) == []


def test_main_resolves_via_pr_head_ref(tmp_path, monkeypatch):
    monkeypatch.setattr(hgc, "EVENTS_DIR", tmp_path)
    rc = run_main("/reject ダメ", PR_HEAD_REF="feature/slice-0012-foo")
    assert rc == 0
    assert len(read_events(12, tmp_path)) == 1
