# `.claude/` — M-team のハーネス（箱）

構築・所有は **AIアーキテクト**。ただし「文言」の正本は分担される（計画書 §2 ファイル所有マップ）。
`.claude/` 全体を git 管理し、変更は **PR レビュー対象**にする。箱の変更もチームの目を通す。

| 対象 | 構築（箱） | 中身（文言） |
|---|---|---|
| `agents/*.md` | AIアーキ | AIアーキ |
| `skills/*/SKILL.md` | AIアーキ | 骨組み＝AIアーキ／枠・禁止事項＝**リーダー** |
| `settings.json`・`hooks/` | AIアーキ | AIアーキ |
| `../CLAUDE.md`（repoルート） | AIアーキ（体裁） | **PM**（上流全体で合意） |
| `../.mcp.json`（repoルート） | AIアーキ | AIアーキ |

> `CLAUDE.md` と `.mcp.json` は `.claude/` の**中ではなく repo ルート**にある。

## 中身

```
.claude/
├── agents/
│   ├── explore.md              Haiku・read-only。地図を返す
│   └── audit.md                Opus・read-only（Bashなし）・memory: project。推奨判定を返す
├── skills/                     下流が叩くのはスラッシュだけ（全て disable-model-invocation）
│   ├── slice/                  ★幸福経路。下の5本を直列実行する
│   ├── pickup/ explore/ implement/ verify/ submit/   復旧経路（途中から叩き直せる）
│   ├── flywheel/               上流（Harness-Keeper）用。書き戻し草案
│   └── express-review-rules/    user-invocable: false。Audit が読む監査型ルール集
├── hooks/                      決定論的ゲート（exit 2 でブロック）
│   ├── lib.sh                  共通・JSONログ（logs/hooks/*.jsonl ＝ Harness-Keeper の監査証跡）
│   ├── pre-tool-use-bash.sh    危険コマンド deny-list
│   ├── protect-paths.sh        acceptance/・.env・CLAUDE.md・docs/adr/ の書込ブロック
│   ├── post-tool-use-check.sh  prettier + tsc + eslint の非ブロッキング feedback
│   ├── stop-gate.sh            受け入れテスト未通過なら完了扱いにしない（上限付きゲート）
│   └── post-compact-reinject.sh compaction 後に禁止事項を再注入
└── settings.json               hooks 配線・permissions deny・env
```

## 設計原則

1. **三層モデル**: 宣言（CLAUDE.md/skills）→ 実行時強制（hooks/permissions/tools）→ 事後検証（CI/ブランチ保護）。
   宣言単体の遵守率は低い。**同じルールを宣言と機械的強制のペアで張る。**
2. **ブロックは不可逆・高コスト操作に集中投下**する。過剰ブロックは人間をクリック係にする（アンチパターン）。
   それ以外は `PostToolUse` の非ブロッキング feedback で返す。
3. **exit code**: `exit 2` = ブロック（stderr がモデルに返る）／`exit 1` は**非ブロッキング**。
   ポリシー強制のつもりで exit 1 を使うのは典型的バグ。
4. **ブロック時の stderr には修正指示を書く**（良性のプロンプトインジェクション）。
5. **繰り返し破られるルールは hook 昇格の合図。** エージェントの struggle はハーネスの欠陥シグナル。
6. **SKILL.md は禁止事項を冒頭に置く**（compaction 時は先頭 ~5,000 トークンだけが再添付される）。
7. **モデル配分は frontmatter で固定**し、人の判断に委ねない（Explore=Haiku / Implementer=Sonnet / Audit=Opus）。

## 前提となる外部 skills（別途インストール）

- [mattpocock/skills](https://github.com/mattpocock/skills): `tdd`・`diagnose`（下流）、`grill-with-docs`・`to-issues`（上流）、
  `git-guardrails`・`setup-pre-commit`（安全レール）
  - `tdd` は導入時に「`acceptance/` は変更禁止・red-green の対象はユニット/統合テストのみ」の1行を追記して使う。
  - `git-guardrails` のスクリプトは「`acceptance/` への Edit/Write もブロック」に改造する（本 repo の hook と二重化）。
- spec-kit は**丸ごと導入しない**。テンプレ3点（constitution / Review & Acceptance Checklist / clarify 質問カタログ）のみ抜粋。

## 未実装（TODO）

- `acceptance/` の初期テスト（PM の仕様表 → AIアーキがコード翻訳 → 参照モックで先行検証）
- `backend/`（Express。`router → service → repository` の3層。バリデーション失敗は **422** を明示的に返す）・`frontend/`（Next.js）
- `reference-mock/`（参照モックの vendor。read-only）／`acceptance/golden/`（golden スクリーンショット）
- GitHub ブランチ保護（main の PR 必須・force-push 禁止・マージは統合役のみ）＝**main 防御の正本**
