---
name: submit
description: git diff を取得して PR を作成し、Audit サブエージェント（Opus・read-only）に diff を注入して深刻度つき推奨判定を得て PR に添付する。プロセスKPIも1行記録する。main には触らない。Use when the user runs /submit after /verify passes.
disable-model-invocation: true
---

# /submit

> 旧称 `/handoff`。mattpocock の同名スキル（会話引き継ぎ圧縮）と衝突するため改名済み。

## 前提

`/verify` が**全て○**であること。✗ が残っていたら実行せず `/implement` に戻す。

## 禁止事項

- **commit / push しない。** PR 作成は GitHub MCP 経由で行い、ローカルの main には一切触らない。
  （ブランチの push が必要な場合も**自分では行わず**、統合役に渡す。）
- Audit に Bash を持たせない。diff は**このコマンドが取得して入力に注入**する。

## 手順

1. **diff を取得する**
   - `git diff main...HEAD` と `git log --oneline main..HEAD` を取得する（read-only）。
   - **diff がコンテキストに収まらない場合は、PR を作らずに停止**し「スライス設計のバグ」として報告する。

2. **PR を作成する**
   - GitHub MCP（toolsets: issues, pull_requests）で `feature/slice-<issue>` → `main` の PR を作成する。
   - 本文には `/verify` の3判定結果と、`/implement` の証拠（テスト生出力・スクリーンショットパス）を貼る。

3. **Audit を起動する**（フレッシュコンテキストの原則）
   - `audit` サブエージェントへ渡すのは次の3つ**だけ**:
     1. 取得した diff
     2. スライス指示書（6項目）
     3. `.claude/skills/express-review-rules/SKILL.md` への参照
   - **実装の経緯・試行錯誤・言い訳を渡さない。**
   - 返ってきた「推奨判定＋深刻度別指摘」を PR にコメントとして添付する。

4. **プロセスKPIを1行記録する**
   `docs/metrics/slices.md` に追記する（フォーマットは同ディレクトリの README を参照）。

   ```
   | slice-<issue> | <YYYY-MM-DD> | <未記入> | <n> | <'/cost' の値> | <なし or 理由> | <メンバー名> |
   ```
   （カラム: slice_id / 日付 / 救援有無 / 再作成回数 / 枠消費 / 差し戻し理由 / メンバー）

   - **救援有無はリーダーが記録する。** 下流の自己申告に頼らない（過少申告を防ぐ）。
     ここでは「未記入」として置き、リーダーが後から埋める。

## 出力

```
## PR: #<番号> <URL>
## Audit 推奨判定: GO / GO-WITH-FIXES / NO-GO
Critical <n> / Major <n> / Minor <n>

## 次のアクション（人の出番）
1. 統合役: runner 再実行＋シークレット＋差分確認
2. 上流リーダー: 層境ゲート GO/NO-GO
3. 統合役: commit / push / マイグレーション
```

**あなたの仕事はここまで。** マージも push もしない。緑は AFK 出力、verdict は HITL 判断。
