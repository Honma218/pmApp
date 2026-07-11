# M-team：AI駆動開発（pmApp）

**スライス進捗集計アプリ**（M-team 自身の「AI駆動チーム開発」の型を回すための、Harness-Keeper 向け
KPI・進捗集計ツール）を開発するリポジトリ。Git への投影（projection / read model）専用で、
書き込みは `/rescue`（bot 経由の救援記録）と集計器自身が生成する派生物のみ。

読む順: `CLAUDE.md`（憲法・目次）→ `docs/playbook.md`（手順の正本）→ `docs/adr/`（決定の正本）→
`2026-07-11_slice-progress-aggregator_実装ロードマップ.md`（実装フェーズ P0〜P6）。

> **移行中の注記（2026-07-11）**：本プロジェクトは以前「業務報告・スキルシート生成システム」の
> 再実装を目的としていたが、**スライス進捗集計アプリの開発のみ**にスコープを変更した。
> `CLAUDE.md` と `docs/adr/` の一部（旧スコープの受け入れテスト・参照モック関連の決定）は
> まだ新スコープに合わせて改訂されていない（PM 承認待ち。`docs/memory-bank/` 参照）。

```
repo-root/
├── CLAUDE.md          ← 憲法（目次型）。中身の正本は PM。旧スコープ記述の改訂は PM 承認待ち
├── CONTEXT.md         ← 共有言語（ユビキタス言語）
├── .mcp.json          ← MCP 3点（runner / Context7 / GitHub）
├── .gitignore
├── .claude/           ← agents・skills・hooks・settings.json
├── .github/workflows/ ← CI（path ガード・イベントスキーマ検証ほか）
├── tools/
│   └── slice-aggregator/          ← 本体。KPI イベント集計（ADR-0012）
├── logs/              ← hooks の JSON ログ（gitignore・hooks が自動生成）
└── docs/
    ├── playbook.md               ← 手順の正本（誰がいつ何をするか。旧スコープ部分は改訂待ち）
    ├── adr/                      ← 個別決定の正本（本書と食い違ったら ADR が正）
    ├── slices/                   ← スライス指示書の正本（ADR-0006）
    ├── metrics/                  ← events（NDJSON・append-only）／index／daily・weekly 集計
    └── memory-bank/README.md     ← CLAUDE.md 昇格候補の隔離置き場
```

## セットアップ（初回）

1. `chmod +x .claude/hooks/*.sh`（Windows から持ち込むと実行ビットが落ちる）
2. GitHub ブランチ保護を設定する（**main 防御の正本。MCP 権限ではない**）
   PR 必須 / force-push 禁止 / マージは統合役のみ
3. mattpocock/skills を導入（`tdd` `diagnose` `git-guardrails` `setup-pre-commit` ほか）
4. 実装は `2026-07-11_slice-progress-aggregator_実装ロードマップ.md` の P0（PM承認ゲート）から着手する

## 注意

- hooks は 2026-07-11 に**ブランチ判定へ改修**済み:
  `feature/*`・`spec/*` での commit/push は許可、ブロックは「main を進める操作」（main上の commit・force push・main宛 push）のみ。
- git 未初期化のうちは hook のブランチ判定が unknown ＝ fail-closed（commit/push はブロック側に倒れる）。
  `git init` → ブランチ保護の設定を先に行うこと。
