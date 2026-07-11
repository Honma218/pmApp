---
name: brief
description: スライス指示書（必須6項目）を docs/slices/slice-NN.md に作成し、main マージ後に GitHub issue をポインタとして起票する上流コマンド。担当はリーダー（枠・禁止事項）＋AIアーキ（技術の形）＋PM（受入基準）。Use when the user runs /brief with a slice ID.
disable-model-invocation: true
---

# /brief <slice>

## 禁止事項（最初に読む）

- **指示書の正本は `docs/slices/slice-NN.md`。issue 本文に指示を書かない**（ADR-0006。issue はポインタのみ）。
- **issue の起票は指示書が main にマージされた後**。順序を逆にしない。
- `slice_id` は**不変・再利用禁止・単調増加**（確定ログ #A）。破棄されたスライスの番号を使い回さない。
  次の番号は `docs/slices/README.md`「スライス一覧」の最大値 +1。
- `CLAUDE.md`・`docs/adr/**` を変更しない（AI編集不可）。

## 手順

1. **指示書作成**: `docs/slices/slice-NN-<slug>.md` を必須6項目で書く。
   frontmatter に `slice_id: NN`（`issue` は起票後に追記・任意）。

   1. **ゴール** — 1〜2文
   2. **検証方法** — 何をもって完了とするか（`tools/slice-aggregator/tests/` のどこを緑にするか等）
   3. **触ってよいファイル範囲** — 変更許可リスト
   4. **貼り付け用の枠** — Claude Code へそのまま渡す指示文（`/pickup NN` の1行で足りることが多い）
   5. **完了の定義** — pytest緑（生ログ）＋シークレット/PII 無し
   6. **禁止事項** — commit/push 先の制限・範囲外ファイル・`CLAUDE.md`/`docs/adr/**` 変更・migration

   分担: 受入基準（2・5）＝PM／技術の形（3）＝AIアーキ／枠・禁止事項（4・6）＝リーダー。
   受入基準が**3〜5を超えるならスライスが大きすぎる**——分割を提案して停止。

2. **一覧更新**: `docs/slices/README.md` のスライス一覧（ID／ゴール／依存／issue／状態）に1行追記。

3. **PR 作成・マージ待ち**: 指示書＋一覧更新を含む PR（`feature/*` か `spec/*`。どちらでも可）を提示し、
   3者の確認を待つ。マージは統合役。

4. **issue 起票**（マージ後）: GitHub MCP（または `gh issue create`）で issue を作る。本文は**ポインタだけ**:

   ```
   指示書: docs/slices/slice-NN-<slug>.md（main）
   検証方法: tools/slice-aggregator/tests/（pytest全緑）＋ validate_events.py

   ---
   指示書の正本は上記ファイル。issue本文はポインタのみ（ADR-0006）。
   ```

5. **一覧更新（2回目）**: `docs/slices/README.md` の issue 列に番号を追記。

## 報告フォーマット

- 指示書パス／6項目の要約（各1行）／issue URL／一覧の追記行。
