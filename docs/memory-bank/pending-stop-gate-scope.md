---
type: 運用方針（CLAUDE.md §2/§3 追記候補）
出典: docs/memory-bank/2026-07-11-harness-bootstrap-observations.md #(2)
status: pending（PM 承認待ち）
---

# Stop hook は「受け入れテストが要る変更かどうか」を diff で判定してからゲートする

## 提案

CLAUDE.md §2/§3 に、Stop hook（`stop-gate.sh`）の対象範囲を明文化する。

> `backend/` `frontend/` の実装ファイルに変更が無いタスク（hook 修正・設定変更のみ等）は
> 受け入れテスト実行結果を要求しない。

## 根拠

2ストライクルール該当。git 設定変更や hook 修正のみの完了時にも「受け入れテストの結果が見つからない」で
毎回ブロックされ、同一原因で2回停止してからユーザー指示で修正した。現状の CLAUDE.md §2 には
「テスト未実行で完了報告しない」としか書かれておらず、対象範囲（実装タスクのみ）が読み取れなかったことが
誤検知の遠因。

## 対応状況

hook 側の実装は `4e4d9fa` で対応済み（`main` との差分に `backend/`／`frontend/` の変更が無ければ
スキップする分岐を追加）。**未確定なのは CLAUDE.md 本体への文言追記のみ。**

## 判断待ちの点

PM 承認のうえ CLAUDE.md §2 または §3 に一文追記するか。
