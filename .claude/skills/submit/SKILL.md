---
name: submit
description: git diff を取得して PR を作成し、Audit サブエージェント（Opus・read-only）に diff を注入して深刻度つき推奨判定を得て PR に添付する。プロセスKPIはイベント自動記録に任せる。main には触らない。Use when the user runs /submit after /verify passes.
disable-model-invocation: true
---

# /submit

> 旧称 `/handoff`。mattpocock の同名スキル（会話引き継ぎ圧縮）と衝突するため改名済み。

## 前提

`/verify` が**全て○**であること。✗ が残っていたら実行せず `/implement` に戻す。

## 禁止事項

- **main への commit / push / merge をしない。** PR 作成は行うが、マージは統合役の専権。
  （`gh pr create` でのPR作成・作業ブランチへの push は許可されている。main への push は hook がブロックする。）
- Audit に Bash を持たせない。diff は**このコマンドが取得して入力に注入**する。
- **`docs/metrics/slices.md` に手で追記しない。** 廃止済み（slice-01完了時点で events 自動記録に置き換え済み）。
  `submitted`・`completed` イベントは PR の open/merge から `emit-slice-pr-events.yml` が自動記録する。
  KPI記録のための手作業はここには無い。

## 手順

1. **diff を取得する**
   - `git diff origin/main...HEAD` と `git log --oneline origin/main..HEAD` を取得する（read-only）。
     **`origin/main` を使う**（ローカル `main` が古いと Audit が古い diff を読む）。先に `git fetch origin` する。
   - **diff がコンテキストに収まらない場合は、PR を作らずに停止**し「スライス設計のバグ」として報告する。

2. **ブランチを push・PR を作成する**
   - `feature/slice-<slice_id>` を push する（作業ブランチの push は許可されている）。
   - GitHub MCP（または `gh pr create --base main`）で PR を作成する。**`--base main` を明示する**
     （default branch 設定に依存すると誤ったベースになる事故が過去に発生している）。
   - 本文には `/verify` の判定結果と、`/implement` の証拠（pytest 生出力）を貼る。

3. **Audit を起動する**（フレッシュコンテキストの原則）
   - `audit` サブエージェントへ渡すのは次の2つ**だけ**:
     1. 取得した diff
     2. スライス指示書（6項目）
   - **実装の経緯・試行錯誤・言い訳を渡さない。**
   - 返ってきた「推奨判定＋深刻度別指摘」を PR にコメントとして添付する。

## 出力

```
## PR: #<番号> <URL>
## Audit 推奨判定: GO / GO-WITH-FIXES / NO-GO
Critical <n> / Major <n> / Minor <n>

## 次のアクション（人の出番）
1. 統合役: 当該スライスの再検証＋シークレット＋差分確認
2. PM: 層境ゲート GO/NO-GO（`/gate GO --slice <N>` 等のコメントで記録）
3. 統合役: マージ（`gh pr merge --merge`。`completed` イベントが自動記録される）
```

**あなたの仕事はここまで。** マージも push もしない。緑は AFK 出力、verdict は HITL 判断。
