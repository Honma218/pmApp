# M-team：AI駆動開発（pmApp）

Repo Base（staff-report-system）を参照仕様（answer key）に、AI駆動チーム開発の「型」を確立しながら
TypeScript(Express) + Next.js で再実装するリポジトリ。読む順: `CLAUDE.md`（憲法・目次）→ `docs/playbook.md`（手順の正本）→ `docs/adr/`（決定の正本）。
リモート: https://github.com/homma-ryoji-3311-hash/pmApp.git

```
repo-root/
├── CLAUDE.md          ← 憲法（目次型・122行）。中身の正本は PM
├── CONTEXT.md         ← 共有言語（ユビキタス言語）
├── .mcp.json          ← MCP 3点（runner / Context7 / GitHub）
├── .gitignore
├── .claude/           ← agents・skills・hooks・settings.json
├── .github/workflows/ ← guard-acceptance.yml（ADR-0001 の CI path ガード）ほか
├── acceptance/        ← 受け入れテスト（ブラックボックス・read-only。ADR-0001/0004/0005）
│   └── golden/        ← golden スクリーンショット（ADR-0008）
├── reference-mock/    ← FastAPI answer key の vendor 予定地（ADR-0005）
├── backend/           ← Express＋構造規約（router→service→repository。ADR-0011）
├── frontend/          ← Next.js / TS（移行対象外・golden は不変資産）
├── tools/
│   ├── teamdev-test-runner-mcp/   ← runner（MCP）。uv プロジェクト。pytest 23件が緑
│   └── slice-aggregator/          ← KPI イベント集計（ADR-0012）
├── logs/              ← hooks の JSON ログ（gitignore・hooks が自動生成）
└── docs/
    ├── playbook.md               ← 手順の正本（誰がいつ何をするか）
    ├── adr/                      ← 個別決定の正本（本書と食い違ったら ADR が正）
    ├── spec/                     ← PM 仕様表（Given/When/Then）の正本
    ├── slices/                   ← スライス指示書の正本（ADR-0006）
    ├── design/                   ← 概要設計（overview.md ほか）
    ├── metrics/slices.md         ← /submit が KPI を1行追記する先
    └── memory-bank/README.md     ← CLAUDE.md 昇格候補の隔離置き場
```

## セットアップ（初回）

1. `chmod +x .claude/hooks/*.sh`（Windows から持ち込むと実行ビットが落ちる）
2. `cd tools/teamdev-test-runner-mcp && uv sync && uv run pytest`（**`uv.lock` をコミットしてバージョンを pin**）
3. ~~`examples/*.test-harness.runtime.json` を `backend/` `frontend/` 直下にコピー~~（✅済 2026-07-11。
   雛形配置済み。scaffolding 時に実際の起動コマンド・ポートへ直す）
4. GitHub ブランチ保護を設定する（**main 防御の正本。MCP 権限ではない**）
   PR 必須 / force-push 禁止 / マージは統合役のみ
5. mattpocock/skills を導入（`tdd` `diagnose` `git-guardrails` `setup-pre-commit` ほか）
   - `tdd` に「`acceptance/` は変更禁止・red-green の対象はユニット/統合テストのみ」を追記
   - `git-guardrails` を「`acceptance/` への Edit/Write もブロック」に改造
6. `acceptance/` の初期テスト（PM の仕様表 → コード翻訳 → 参照モックで先行検証）

## 注意

- hooks は 2026-07-11 に**ブランチ判定へ改修**（playbook 未実装 #1・#2・#5 解消）:
  `feature/*`・`spec/*` での commit/push は許可、ブロックは「main を進める操作」（main上の commit・force push・main宛 push）のみ。
  `acceptance/`・`docs/spec/` は `spec/*` でのみ書込可、`reference-mock/` は全ブランチ read-only。
- git 未初期化のうちは hook のブランチ判定が unknown ＝ fail-closed（commit/push・acceptance 書込はブロック側に倒れる）。
  `git init` → ブランチ保護の設定を先に行うこと。
