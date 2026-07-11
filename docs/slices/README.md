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
- **frontmatter に `slice_id`（必須）を持つ。** スライス進捗集計アプリの主キー（確定ログ #A・
  不変・再利用禁止・単調増加）。`issue`（GitHub issue番号）は任意。例：

  ```yaml
  ---
  slice_id: 1
  issue: 42   # 任意
  ---
  ```

  この PR が `main` にマージされると、`emit-issued-event` workflow が frontmatter を読み取り
  `docs/metrics/events/slice-0001.jsonl` に `issued` イベントを追記する（P1・`tools/slice-aggregator/`）。
  **`slice_id` を持たない指示書は起票イベントが記録されない**（=集計対象外になる）。

## スライス一覧（依存順）

| ID | ゴール（1行） | 依存 | issue | 状態 |
|---|---|---|---|---|
| 1 | `abandoned` イベントの自動記録（`/abandon` コメントコマンド） | P1〜P6準備完了 | [#18](https://github.com/Honma218/pmApp/issues/18) | 完了（PR #19） |
| 2 | `gates.md` を events 由来の生成物に変える（手動編集の二重管理を廃止） | slice-1完了 | （main マージ後に起票） | 指示書作成済み |

> この一覧は issue 分解の成果物。フェーズ全体の依存順は `2026-07-11_slice-progress-aggregator_実装ロードマップ.md`（P0〜P6）を参照。
