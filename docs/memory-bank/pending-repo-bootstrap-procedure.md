---
type: ADR 案（docs/adr/0013-repo-bootstrap-procedure.md 相当）
出典: docs/memory-bank/2026-07-11-harness-bootstrap-observations.md #(3)
status: pending（Harness-Keeper 単独確定可・内容の是非は PM／AIアーキ判断）
---

# 新規リポジトリの `main` 作成手順（ADR 案）

## 提案

「新規リポジトリの `main` 作成は統合役が空 root commit で行い、force-push は使わない」手順を
`docs/playbook.md` に「工程0: リポジトリ新規作成」として追加し、恒久化が妥当なら
`docs/adr/0013-repo-bootstrap-procedure.md` として決定化する。

## 根拠

`docs/playbook.md` の全工程は「main に既に履歴がある」前提で書かれている。GitHub 上に main が
一つも存在しない完全新規リポジトリでは、`pre-tool-use-bash.sh` が unborn HEAD を `unknown` として
fail-closed し、あらゆる commit をブロックする。統合役専権の「main への push」制約と
「そもそも main を作る人が誰なのか」が噛み合わない。今回は例外運用（hook 一時無効化 → 空 commit で
main 作成 → 即座に復元、force-push は不使用）で回避した。

## 発生回数

1回目（リポジトリ初回セットアップでのみ起こる性質。頻度は低いが影響は大きい）

## 判断待ちの点

- Harness-Keeper 単独確定可（ADR）だが、内容の是非は PM／AIアーキ判断。
- 2回目以降も同型の例外運用が発生するようなら、hook 側に「unborn かつリモートに main branch が
  一つも無い場合のみ許可」という限定例外を追加する昇格を検討。
