---
name: slice
description: 1スライスを最初から最後まで1コマンドで通す幸福経路のオーケストレータ。pickup → explore → implement → verify → submit を順に直列実行する。下流メンバーが通常使うのはこれ1本。Use when the user runs /slice with an issue number.
disable-model-invocation: true
---

# /slice <issue番号>

## これは幸福経路

個別コマンド（`/pickup` `/explore` `/implement` `/verify` `/submit`）は**復旧経路**。
途中で失敗したら `/slice` をやり直さず、失敗した工程から個別コマンドで叩き直す。

## 禁止事項（全工程を通して有効）

- main への commit / push / DBマイグレーション禁止（統合役のみ。作業ブランチのcommit/pushは可）
- `docs/metrics/events/**`・`docs/metrics/index/`・`docs/status/` の手書き禁止（bot / 日次cronのみが書く）
- `CLAUDE.md`・`docs/adr/**` 変更禁止
- 範囲外ファイル変更禁止
- `main` 上で作業しない
- 緑になったら停止して報告（人の出番へ渡す）

## 実行順（直列。並列にしない）

制御は**常にこのメインセッションが握る**。サブエージェントは呼ばれて結論を返すだけで、
次工程を自分では起動しない（ハブ＆スポーク。リレーではない）。

1. `/pickup <issue>` — issue 取得・ブランチ・6項目要約
   - 指示書に欠けがあれば**ここで停止**してリーダーへ差し戻す。
2. `/explore` — Explore(Haiku, read-only) が地図を返す
   - 「範囲が広すぎる」と報告されたら**ここで停止**。
3. `/implement` — 緑になるまでループ（自動停止トリガーに従う）
4. `/verify` — 3判定を○×表示
   - ✗ があれば 3 に戻る。3回ループしても✗なら停止して報告。
5. `/submit` — PR 作成 ＋ Audit 推奨判定 ＋ KPI 記録

## 停止条件（AFK ループを抜けて人を呼ぶ）

| 条件 | 対応 |
|---|---|
| 同一エラー2回 | 停止 → 5 Whys を報告 |
| 5ファイル / Edit 5回超 | 停止 → 影響範囲を報告 |
| 同じテスト3回リトライで赤 | ハーネスのバグとして報告 |
| diff がコンテキストに収まらない | スライス設計のバグとして報告 |
| セッション再作成が2回超 | **スライスが大きすぎる** → Flywheel の観察項目へ |

コンテキストが膨れたら `/compact` せず、**セッションを捨てて `/pickup` から再開**する。

## 終点

`/submit` の完了で AFK 区間は終わり。ここから先は人（統合役 → 層境ゲート）の仕事。
**テスト緑を完遂と見なさない。** 緑 ≠ 仕様充足。
