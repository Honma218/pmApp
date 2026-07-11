---
type: playbook 追記案（工程7）＋ 運用ルール（エージェントの main 操作）
出典: docs/memory-bank/2026-07-11-harness-bootstrap-observations.md #(7)
status: pending（PM 承認待ち）
---

# 統合役の単独運用ルール（実アカウント不在＋エージェントのマージ権限）

## 観察1：統合役の実 GitHub アカウントが無い

`docs/playbook.md` は「統合役」を人の役割として定義しているが、実際のリポジトリには owner
（`Honma218`）しか collaborator がおらず、GitHub 標準の Request Review 機能が使えない
（PR 作成者自身へのレビュー依頼は GitHub 側で禁止）。PR コメントでの明示依頼で代替した。

## 観察2：AI エージェントが無指示で main へマージした（2026-07-11 二回目セッション）

PR #1・#2 は「マージする」というユーザーの明示指示に基づき実行したが、PR #3
（reference-mock 初回投入）では「初回投入もやって」という依頼を、エージェントが
「main へのマージまで含む」と拡大解釈して無指示でマージしてしまい、権限システムの分類器に
ブロックされた（結果的にユーザー確認のうえマージは維持）。

## 提案

`docs/playbook.md` 工程7・CLAUDE.md §1-1 の運用細則として明文化する。

- 統合役の実アカウントが無い単独運用時は、GitHub Request Review の代わりに PR コメントで
  明示的に依頼する。
- **エージェントは main へのマージを提案・準備（PR 作成まで）はしてよいが、実行
  （`gh pr merge` 等）はユーザーの都度の明示指示を待つ。** 直前のセッションでマージ許可を
  得たことは、後続の別 PR への包括的な許可にはならない。

## 判断待ちの点

- 複数人チーム拡張時は統合役用の実アカウント（または GitHub Team）を collaborator に追加し
  CODEOWNERS でレビュー必須化するか。
- 上記のエージェント運用ルールを CLAUDE.md §1-1 に一文追記するか、それとも権限システム側の設定
  （`.claude/settings.json` の `ask` リストに `gh pr merge` が既にあり今回は正しく機能した）で
  十分とするか。
