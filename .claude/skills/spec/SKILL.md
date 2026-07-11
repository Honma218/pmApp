---
name: spec
description: 廃止（旧スコープ専用）。/brief を使うこと。Use when the user runs /spec — respond that it is retired and point to /brief.
disable-model-invocation: true
---

# /spec（廃止）

> **【スコープ変更・2026-07-11】廃止。** `/spec` は「PM の仕様表（`docs/spec/slice-NN.md`）を
> `acceptance/` の実行可能テストへ翻訳し、参照モックで緑→golden撮影→backend で赤を確認する」
> 工程だった。業務アプリ再実装（旧スコープ）専用のコマンドで、`acceptance/`・`reference-mock/`・
> `backend/`・golden のいずれも現行スコープ（スライス進捗集計アプリのみ）には存在しない。

**現行スコープでは `/spec` は使わない。** 指示書作成（旧 `/spec`＋`/brief` の統合）は
`/brief <slice>` 1本で行う。

このコマンドが呼ばれたら、上記を報告して `/brief` へ誘導し、何も実行しない。

関連: `docs/memory-bank/pending-scope-pivot-claude-md-and-adr.md`（ADR-0001/0004/0005/0008/0009
廃止判定）。
