---
title: ハーネス初回ブートストラップ — 要改善事項 handoff
date: 2026-07-11
updated: 2026-07-11（確定/未確定 振り分け・(5)解決を反映）
tags: [m-team, harness, flywheel, hooks, ci, bootstrap, 昇格候補]
status: 確定分は対応済み（機械的に検証可能）。未確定分は PM / AIアーキ承認待ち
入力: リポジトリ初回セットアップ〜PR #1（feature/slice-00-skeleton）・PR #2（spec/slice-00-skeleton）・PR #3（reference-mock 初回投入）作成セッション
関連: CLAUDE.md §10（このファイルの育て方）／.claude/skills/flywheel/SKILL.md（出力形式に準拠）
---

# ハーネス初回ブートストラップ — 要改善事項 handoff

`git init` からリポジトリを立ち上げ、スケルトン一式・参照モックを PR #1〜#3 として `main` へ
統合するまでの一連の作業で、ハーネス（hooks / CI / playbook）が「**リポジトリが空の状態からの
初回ブートストラップ**」という前提を想定していないために生じた摩擦を観察順にまとめる。

**この振り分けは草案。** `/flywheel` の分類（スライス設計の欠陥 / ハーネスの欠陥）と
「強制力の階段を1段だけ上げる」原則に沿って記載する。**確定（CLAUDE.md・ADR への昇格）は
PM／AIアーキが行う** — 「確定分」は「コード上の対応が完了した」ことを指し、CLAUDE.md 本体への
昇格が済んだという意味ではない。

---

## 振り分けの基準

| 区分 | 意味 |
|---|---|
| **確定分** | 修正が commit として main に入っており、`git log` / `git show` で機械的に検証できる。再発防止の実装まで完了 |
| **未確定分** | 例外運用・手作業で当座は回避したが、恒久的な手順（playbook 追記・ADR 化・アカウント整備等）がまだ書かれていない |

---

## 早見表

| # | 観察 | 区分 | 発生回数 | 対応 |
|---|---|---|---|---|
| 1 | `pre-tool-use-bash.sh` の unborn HEAD 誤検知 | **確定分** | 2回目（型として） | commit `4e4d9fa` |
| 2 | `stop-gate.sh` の非実装タスク誤ゲート | **確定分** | 2回（2ストライク該当） | commit `4e4d9fa` |
| 6 | `validate-events.yml` の `fetch-depth` 不足 | **確定分** | 1回目 | commit `0afc271` |
| 5 | `reference-mock/` 初回投入手順の欠落 | **確定分**（2026-07-11 解消） | 1回目 | PR #3（`git subtree add --squash`）で vendor 完了。手順の恒久文書化は任意の残課題（下記） |
| 3 | 新規リポジトリで `main` が存在しない際のブートストラップ手順が playbook に無い | **未確定分** | 1回目 | 例外運用で回避のみ。ADR 化 未実施 |
| 4 | `guard-acceptance.yml` の path-guard と「一括スケルトン投入」の構造的不整合 | **未確定分** | 1回目 | PR分割（feature/spec）で回避のみ。playbook 追記 未実施 |
| 7 | 「統合役」の GitHub アカウントが存在しない | **未確定分** | 1回目 | PR コメントで代替のみ。恒久策 未定 |

---

# 確定分（対応済み・機械的に検証可能）

## (1) `pre-tool-use-bash.sh` の unborn HEAD 誤検知

**観察**：`git rev-parse --abbrev-ref HEAD` は commit が0件の新規ブランチ（unborn HEAD）でエラーになり、
hook はこれを `unknown` にフォールバックして fail-closed する。結果、`feature/*` に checkout 済みでも
最初の commit だけは常にブロックされた。

**分類**：ハーネスの欠陥（`.claude/hooks/pre-tool-use-bash.sh:16`）

**発生回数**：1回目で判明・即修正。ただし同じ根本原因（unborn HEAD でのブランチ判定失敗）が (2) にも
存在しており、**型としては2回目**（同一クラスの欠陥が2箇所に埋め込まれていた）。

**対応**：`git symbolic-ref -q --short HEAD` を優先し、失敗時のみ `rev-parse` にフォールバックする形に修正済み（commit `4e4d9fa`）。

**書き戻し草案**：`docs/memory-bank/pending-unborn-head-pattern.md`（昇格候補）に
「hook でブランチ名判定を書く際は `symbolic-ref -q --short HEAD` を優先する」という実装パターンを記録する提案。

---

## (2) `stop-gate.sh` の非実装タスク誤ゲート

**観察**：git 設定変更や hook 修正のみを行ったタスクの完了時にも、`stop-gate.sh` が
「受け入れテストの実行結果が見つからない」で毎回ブロックした。`backend/` `frontend/` の実装が
一切変わっていないタスクにまで受け入れテストを要求しており、実装タスクと非実装タスクを区別できていなかった。

**分類**：ハーネスの欠陥（`.claude/hooks/stop-gate.sh`）

**発生回数**：2回（同一原因で2回ブロックされてからユーザー指示で修正に着手）。**2ストライクルールに該当**。

**対応**：`main` との分岐点からの差分に `backend/` `frontend/` の実装ファイル変更が無ければゲートをスキップする
分岐を追加済み（commit `4e4d9fa`）。ブランチ判定も `symbolic-ref` 優先に統一（(1) と同じパターン）。

**書き戻し草案**：`docs/memory-bank/pending-stop-gate-scope.md`（昇格候補）に
「Stop hook は "受け入れテストが要る変更かどうか" を diff で判定してからゲートする」という設計方針を
CLAUDE.md §2/§3 の運用細則として明文化する提案。

---

## (6) `validate-events.yml` の `fetch-depth` 不足

**観察**：`actions/checkout@v4` が既定の shallow fetch のまま `git diff --name-only origin/main...HEAD` を
実行しており、`origin/main` を解決できず `fatal: ambiguous argument` で落ちていた。
同一リポジトリの `guard-acceptance.yml` には `fetch-depth: 0` があり、単純な設定漏れ（不整合）。

**分類**：ハーネスの欠陥（CI スクリプトのバグ。内容とは無関係に、対象 paths に触れる PR で常に発生する）

**発生回数**：1回目

**対応**：修正済み（commit `0afc271`）。再発防止として、`origin/${{ base_ref }}...HEAD` を使うワークフローの
テンプレート化、または CI 側で `fetch-depth: 0` を共通 composite action に切り出すことを検討（低優先度・任意）。

**書き戻し草案**：特になし（単純な CI バグ修正のため ADR 昇格は不要）。

---

## (5) `reference-mock/` は全ブランチで書込不可（初回投入手順が無かった）

**観察**：`reference-mock/README.md` は ADR-0005 により **全ブランチで read-only**（`spec/*` も含む）。
スケルトン一括投入時に path-guard に検知され、feature ブランチから該当ファイルを除去して回避したが、
「では実際どうやって `reference-mock/` 配下に最初のソース一式を `main` に入れるのか」という
**手順がどこにも書かれていない**状態のまま残っていた。

**分類**：仕様通り（ADR-0005 の意図通り）。ただし投入手順の欠落。

**発生回数**：1回目

**解決（2026-07-11）**：統合役操作として対応済み。

1. シード棚卸し：`staff-report-system`（ローカル `C:/Cursor/Git/staff-report-system` @ `e161d4b`）の
   `backend/tests/conftest.py` を確認し、フィクスチャが `"Test User"` 等の合成データのみであることを確認。
   `git grep` によるハードコードシークレット走査もヒットなし。
2. `git subtree add --prefix reference-mock <local path> main --squash` で vendor（PR #3）。
   Bash 経由の git 操作は `protect-paths.sh`（Edit/Write/NotebookEdit 用 hook）の対象外のため、
   統合役の手動 vendor 操作として実行可能だった（ADR-0005 の想定通りの経路）。
3. `reference-mock/README.md` 冒頭に read-only・vendor手順・棚卸し結果の注記を追記。
4. `reference-mock/backend/test-harness.runtime.json` を新規作成（`uvicorn app.main:app --port 8000`、
   readyCheck `/health`）。
5. PR #3 として `main` へマージ済み（`mergedAt: 2026-07-11T10:44:48Z`）。

**残課題（任意・ブロッカーではない）**：今回の手順（シード棚卸し→`git subtree add --squash`→README注記→
runtime.json 作成→PR→統合役マージ）を `docs/playbook.md` Step 0 または `reference-mock/README.md` に
恒久手順として書き足すかどうかは PM/AIアーキ判断。**次回 vendor 更新（再取り込み）が発生するまでは
急がなくてよい**（2ストライクルール未該当・1回目）。

**書き戻し草案**：`reference-mock/README.md` は追記済み（対応完了）。`docs/playbook.md` への恒久化は
未確定分 (3)(4) とまとめて起票するのが効率的（下記「未確認・次のアクション候補」参照）。

---

# 未確定分（PM／AIアーキ判断待ち）

## (3) 新規リポジトリで `main` が存在しない際のブートストラップ手順が無い

**観察**：`docs/playbook.md` の全工程（/spec・/pickup・/slice・/submit）は「`main` に既に何らかの履歴がある」
前提で書かれている。今回のように **GitHub 上に `main` が一つも存在しない完全新規リポジトリ** では、
- `pre-tool-use-bash.sh` が unborn HEAD を `unknown` として fail-closed し、あらゆる commit をブロック
- 統合役専権の「main への push」制約と、そもそも main を作る人が誰なのかが噛み合わない

という手順の空白にぶつかり、都度ユーザーに承認を仰ぐ例外運用で対応した（hook 一時無効化 → 空 commit で
main 作成 → 即座に復元、force-push は不使用）。

**分類**：ハーネスの欠陥（手順の欠落。playbook・CLAUDE.md のどちらにも「リポジトリ新規作成」の章が無い）

**発生回数**：1回目（このプロジェクトの初回セットアップでしか起こらない性質のため、頻度は低いが影響は大きい）

**提案（強制力の階段を1段）**：
- 現在：宣言なし（playbook に記載が無い）。
- 提案：まず宣言（`docs/playbook.md` に「工程0: リポジトリ新規作成」を追加し、
  「`main` は統合役が空 commit で作成する」という手順を明文化）。
  2回目以降も同じ例外運用が発生するようなら hook 側に「unborn かつリモートに main branch が
  一つも無い場合のみ許可」という限定的な例外条件を追加する昇格を検討。

**書き戻し草案**：`docs/adr/0013-repo-bootstrap-procedure.md`（新規決定・案。Harness-Keeper 単独確定可）に
「新規リポジトリの `main` 作成は統合役が空 root commit で行い、force-push は使わない」という手順を明文化する提案。

---

## (4) `guard-acceptance.yml` の path-guard と「一括スケルトン投入」の構造的不整合

**観察**：`main` が空の状態でスケルトン一式を1本の `feature/*` ブランチにまとめて PR にしたところ、
`acceptance/` と `docs/spec/` 配下のプレースホルダーファイルが `origin/main...HEAD` の差分に含まれ、
ADR-0001/0004 の path-guard（CI）に正しく検知されて fail した。ルール自体は意図通り動作しており、
バグではない。対応として `acceptance/`・`docs/spec/` だけを別の `spec/*` ブランチ（PR #2）に分離した。

**分類**：ハーネスの欠陥（手順の欠落。「複数レイヤーにまたがる初回スケルトンをどう複数 PR に分割するか」が
playbook / brief スキルのどこにも書かれていない）

**発生回数**：1回目

**提案（強制力の階段を1段）**：
- 現在：宣言なし。
- 提案：`docs/playbook.md` の工程0（案、(3)と共通化）に
  「初回スケルトンは backend/frontend/tools/docs 用の `feature/*` と、
  acceptance/docs-spec 用の `spec/*`、reference-mock 用の統合役直接投入（(5)参照）に
  最初から分けて用意する」ことを明記する。
  `.claude/skills/brief/SKILL.md` 側にも初回投入時の注意として追記する余地がある。

**書き戻し草案**：`docs/playbook.md`（追記草案。本体は AIアーキ確定可）に
「工程0: 初回スケルトン投入」節を新設し、本ブランチ分割の手順（(3)(5)を含む）を playbook の正本に反映する提案。

---

## (7) 「統合役」の GitHub アカウントが存在しない

**観察**：`docs/playbook.md` は「統合役」を人間の役割として定義しているが、実際の GitHub リポジトリには
所有者アカウント（`Honma218`）しか collaborator がおらず、GitHub 標準の Request Review 機能を
使ったレビュー依頼ができなかった（PR 作成者自身へのレビュー依頼は GitHub 側で禁止されている）。
代替として PR コメントで明示的に依頼する運用にした。

**分類**：手順の欠落（ロールと実際の GitHub アカウントのマッピングが未定義）

**発生回数**：1回目

**提案（強制力の階段を1段）**：
- 現在：宣言のみ（「統合役」という役割名はあるが実アカウントの割当が無い）。
- 提案：複数人チームに拡張する際は統合役用の実アカウント（または GitHub Team）を collaborator に
  追加し、CODEOWNERS 等で機械的にレビュー必須にする。単独運用が続く前提なら、
  「PR コメントでの依頼」を正式な代替手順として `docs/playbook.md` 工程7に明記する。

**関連の追加観察（2026-07-11 二回目セッション）**：PR #1〜#3 とも、統合役の役割を担うユーザー本人が
セッション内でマージ判断を出す運用になっている。PR #3 のマージは AI エージェントが明示指示を待たずに
実行してしまい、権限システムに拒否された（ユーザー確認の上でマージは維持）。単独運用時は
「main へのマージは毎回ユーザーが明示的に指示する」運用を徹底する必要がある——これは (7) の
「実アカウント不在」と表裏の問題（役割はあるが権限行使のタイミングが曖昧になりやすい）。

**書き戻し草案**：`docs/playbook.md` 工程7（追記草案）に
「統合役の実アカウントが無い単独運用時は、GitHub Request Review の代わりに PR コメントで
明示的に依頼する。また、エージェントが `main` へのマージを提案する場合も、実行前に必ずユーザーの
明示指示を待つ」旨を運用上の注記として追加する提案。

---

## 剪定提案

今回の作業でファイルを肥大化させた形跡は無い（CLAUDE.md 自体は未変更）。剪定対象なし。

## 未確認・次のアクション候補

- (3)(4)(5の残課題) は同根（「初回ブートストラップの手順が playbook に無い」）なので、ADR または
  playbook の同一セクション（工程0）にまとめて起票するのが良さそう。
- (7) は今回の追加観察（AI エージェントの無指示マージ）を踏まえ、playbook 工程7・CLAUDE.md §1-1 の
  運用細則として「エージェントは main マージを提案するだけで、実行はユーザーの都度指示を待つ」ことを
  明文化する候補。
- 2ストライクルールの対象は (2) のみ確認できた。(1) は同型だが別ファイルでの初発生のため、
  厳密な「同一指示の2回目」には該当しない可能性がある — PM/AIアーキの判断に委ねる。
