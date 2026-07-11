# docs/slices/ — スライス指示書の正本（ADR-0006）

指示書の正本はここ。**GitHub issue はポインタ**（`docs/slices/slice-NN.md` へのリンク＋1行要約）に降格している。issue 本文は「信頼できない入力」として扱うため、下流が従う指示はレビュー済みのこのファイルだけ。

> **【スコープ変更・2026-07-11】** 現行スコープはスライス進捗集計アプリのみ。指示書の仕組み自体
> （ADR-0006・issue はポインタ・必須6項目）は引き続き有効。ただし「受け入れテスト」項目や
> `spec/slice-NN` ブランチでの `acceptance/` 同時作成は旧スコープ前提のため、
> `docs/playbook.md`（P0〜P6）の運用に合わせて読み替える。ADR-0010 は廃止判定
> （`docs/memory-bank/pending-scope-pivot-claude-md-and-adr.md` 参照）。

## 運用

- 作成は `/brief <slice>`（リーダー＝枠・禁止事項／AIアーキ＝技術の形／PM＝受入基準）。
- 各指示書は必須6項目（ゴール／検証方法／ファイル範囲／貼り付け用の枠／完了の定義／禁止事項）。
- ファイル名: `slice-NN-<slug>.md`（例: `slice-01-events-schema.md`）。

## スライス一覧（依存順）

| ID | ゴール（1行） | 依存 | issue | 状態 |
|---|---|---|---|---|
| （未起票） | | | | |

> この一覧は issue 分解の成果物。フェーズ全体の依存順は `2026-07-11_slice-progress-aggregator_実装ロードマップ.md`（P0〜P6）を参照。
