---
type: 実装パターン（hook のブランチ判定）
出典: docs/memory-bank/2026-07-11-harness-bootstrap-observations.md #(1)(2)
status: pending（PM／AIアーキ承認待ち）
---

# hook のブランチ名判定は `symbolic-ref` を優先する

## 提案

hook 内で現在ブランチを判定するコードを書く際は、次の順で解決する。

1. `git symbolic-ref -q --short HEAD`（unborn HEAD＝commit 0件の新規ブランチでも成功する）
2. 失敗時のみ `git rev-parse --abbrev-ref HEAD` にフォールバック
3. さらに失敗したら `unknown` として fail-closed

## 根拠

`git rev-parse --abbrev-ref HEAD` は unborn HEAD で失敗し、`pre-tool-use-bash.sh`（修正前）と
`stop-gate.sh` の両方で同じ誤検知を起こした（2箇所で同一クラスの欠陥＝型としては2回目）。
`4e4d9fa` で両 hook に適用済み。

## 適用範囲

今後 `.claude/hooks/*.sh` に新しくブランチ判定を書く場合はこのパターンを既定にする。

## 判断待ちの点

CLAUDE.md 本体（または `.claude/hooks/lib.sh` のような共有ヘルパー関数）に昇格するか。
現状は各 hook ファイルに同じロジックが重複しているため、`lib.sh` への関数化が妥当か PM／AIアーキ判断。
