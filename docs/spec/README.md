# docs/spec/ — PM 仕様表の正本

**PM が書く仕様表（Given/When/Then）の置き場**。ここが仕様の正本であり、`acceptance/` のテストコードはこの仕様表からの翻訳（`/spec <slice>` で AIアーキが実行）。spec-kit は丸ごと導入せず、テンプレ3点（constitution 書式・Review & Acceptance Checklist・clarify 質問カタログ）のみ抜粋して使う（計画書 §5）。

## ルール

- 書込は **`spec/*` ブランチのみ**（ADR-0004。`acceptance/` と同じ判定）。
- 1スライス＝1仕様表を基本とし、受入基準は **≤3〜5** に収める（超えたら分解のバグ）。
- ファイル名は対応するスライスに揃える: `slice-NN-<slug>.md`。
- セルフレビューには spec-kit 抜粋の「Review & Acceptance Checklist」を使う。
- 合成フィクスチャ（テストデータ）も PM 所有。フィールドのデータ階層（L0/L1/L2）は仕様表作成時に確定する（計画書 §6）。
