---
name: explore
description: Explore サブエージェント（read-only・Haiku）を起動し、触ってよいファイル範囲の地図を取得する。実装前に必ず通す工程。Use when the user runs /explore after /pickup.
disable-model-invocation: true
---

# /explore

## 手順

1. `explore` サブエージェント（`.claude/agents/explore.md`）を **1回だけ**起動する。
   - 渡す入力は次の3つのみ:
     - スライス指示書の「1. ゴール」
     - 「3. 触ってよいファイル範囲」
     - 「2. 受け入れテスト」の一覧（テストファイルのパス）
   - **実装方針や自分の推測を渡さない。** 探索結果にバイアスをかけない。

2. 返ってきた地図をそのまま提示する。
   - **ファイルの中身をここで読み直さない。** 地図だけでコンテキストを済ませるのが本工程の目的。

3. Explore が「要約10行を超える」「範囲が広すぎる」と報告した場合、
   **スライスが大きすぎる**として `/implement` に進まず、リーダーへ報告する。

## やってはいけないこと

- Explore に Bash / MCP / Edit を持たせない（定義ファイルの tools を変更しない）。
- Explore を並列に複数起動しない（Pro 枠を食う。既定は直列）。
- Explore に次工程を起動させない。制御はこのメインセッションが握る。

次は `/implement`。
