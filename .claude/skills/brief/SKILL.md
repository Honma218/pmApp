---
name: brief
description: スライス指示書（必須6項目）を docs/slices/slice-NN.md に作成し、main マージ後に GitHub issue をポインタとして起票する上流コマンド。担当はリーダー（枠・禁止事項）＋AIアーキ（技術の形）＋PM（受入基準）。Use when the user runs /brief with a slice ID.
disable-model-invocation: true
---

# /brief <slice>

## 禁止事項（最初に読む）

- **指示書の正本は `docs/slices/slice-NN.md`。issue 本文に指示を書かない**（ADR-0006。issue はポインタのみ）。
- **issue の起票は指示書が main にマージされた後**。順序を逆にしない。
- 指示書と `acceptance/` は**同じ `spec/slice-NN` ブランチ**で作り、まとめて main へマージする。
- `slice_id` は**不変・再利用禁止・単調増加**（確定ログ #A）。破棄されたスライスの番号を使い回さない。
- 対応する受け入れテスト（`/spec` の成果物）が無いスライスの指示書を書かない。

## 手順

1. **前提確認**: `docs/spec/slice-NN.md`（仕様表）と `acceptance/` の対応テストが同ブランチに存在するか確認。
   無ければ停止して「先に /spec」と報告。
2. **指示書作成**: `docs/slices/slice-NN-<slug>.md` を必須6項目で書く。frontmatter に `slice_id: NN`（`issue` は起票後に追記・任意）。

   1. **ゴール** — 1〜2文
   2. **受け入れテスト** — `acceptance/` のどのファイルを緑にするか（パス列挙）
   3. **触ってよいファイル範囲** — 変更許可リスト（backend の feature ディレクトリ＋frontend の対応範囲＋その unit テスト）
   4. **貼り付け用の枠** — Claude Code へそのまま渡す指示文（雛形は計画書 付録A-4）
   5. **完了の定義** — テスト緑（生ログ）＋golden 差分閾値内＋シークレット/PII 無し
   6. **禁止事項** — commit/push 先の制限・範囲外ファイル・acceptance/ 変更・migration

   分担: 受入基準（2・5）＝PM／技術の形（3）＝AIアーキ／枠・禁止事項（4・6）＝リーダー。
   受入基準が **3〜5 を超えるならスライスが大きすぎる**——分割を提案して停止。
3. **レビュー依頼**: 指示書を含む PR（`spec/slice-NN`）を提示し、3者の確認を待つ。マージは統合役。
4. **issue 起票**（マージ後）: GitHub MCP で issue を作る。本文は**ポインタだけ**:

   ```
   slice-NN-<slug>
   指示書: docs/slices/slice-NN-<slug>.md（main）
   受け入れテスト: acceptance/<feature>/<file>.spec.ts
   ```

5. **一覧更新**: `docs/slices/README.md` のスライス一覧（ID／ゴール／依存／issue／状態）に1行追記。

## 報告フォーマット

- 指示書パス／6項目の要約（各1行）／issue URL／一覧の追記行。
