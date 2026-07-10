---
name: spec
description: PM の仕様表（docs/spec/slice-NN.md）を acceptance/ の実行可能テストへ翻訳し、参照モックで緑→golden 撮影→backend で赤の反転を確認して PR を作る上流コマンド。実行者は AIアーキ。Use when the user runs /spec with a slice ID on a spec/* branch.
disable-model-invocation: true
---

# /spec <slice>

## 禁止事項（最初に読む）

- **`spec/slice-NN` ブランチ以外では実行しない。** `feature/*`・main 上なら即停止して報告（ADR-0009。hook も止める）。
- **`backend/` `frontend/` を変更しない**（CLAUDE.md §1-4。実装が仕様ブランチに紛れ込む）。
- **仕様表（`docs/spec/slice-NN.md`）が無ければ停止。** AI が仕様を推測で書かない——仕様表の正本は PM（ADR-0006 と同じ信頼境界）。
- **golden は実装より先に撮る**（ADR-0008。後から撮ると実装が仕様を定義してしまう）。
- `reference-mock/` は読み取り専用。テストが緑にならないとき answer key を直さない。

## 手順（順序固定）

1. **ブランチ確認**: `git rev-parse --abbrev-ref HEAD` の生出力を確認。`spec/slice-NN` でなければ、
   main 最新から `spec/slice-NN` を切る（既存なら続きから）。
2. **仕様表を読む**: `docs/spec/slice-NN.md`。無ければ**停止して PM に依頼**。
3. **翻訳**: 仕様表の Given/When/Then を `acceptance/<feature>/*.spec.ts` へ実装する。
   - ブラックボックスのみ（実 HTTP＋Playwright。ADR-0001）。in-process・unit は書かない。
   - 接続先は `ACCEPTANCE_BASE_URL` で切替可能にする（ADR-0005）。
   - 最新 API は Context7 に聞く。
4. **参照モックで緑**: runner（`harness_start`）で `reference-mock/`（:8000）を起動 → ready 待ち →
   `ACCEPTANCE_BASE_URL=http://localhost:8000` でスイート実行 → **緑を生ログで提示**（翻訳が正しい証明）。
   赤なら翻訳のバグとして直す（answer key は直さない）。
5. **golden 撮影**: 参照モックの画面を `toHaveScreenshot()` で撮り `acceptance/golden/` へ（ADR-0008）。
6. **backend で赤**: runner で `backend/`（:3000）を起動 →
   `ACCEPTANCE_BASE_URL=http://localhost:3000` でスイート実行 → **赤を生ログで提示**（下流に渡せる証明）。
   ここで緑になったら「テストが何も検証していない」疑い——停止して報告。
7. **PR 作成**: commit（spec ブランチは許可）→ push → GitHub MCP で PR。
   本文に「モック緑・backend 赤」の生ログ要約を添付。**PM の重量ゲート**（acceptance/ に触るので常に重量。ADR-0007）へ。

## 停止トリガー

- 参照モックが起動しない／同一エラー2回 → 5 Whys を書いて停止（CLAUDE.md §3）。
- 仕様表に曖昧さがあり翻訳を決められない → 推測せず PM への質問として出す。

## 報告フォーマット（証拠ベース）

- 翻訳したテストファイル一覧／モック実行の生ログ（緑）／golden ファイル一覧／backend 実行の生ログ（赤）／PR URL。
