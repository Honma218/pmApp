---
name: implement
description: 貼り付け用の枠に沿って実装し、pytest が緑になるまでループする。テストFW（pytest）で採点し、赤なら生ログを読んで直す。Use when the user runs /implement after /explore.
disable-model-invocation: true
---

# /implement

## 禁止事項（これが最優先。他のすべてに優先する）

1. **commit / push / DBマイグレーションを main 上で実行しない。** main への反映は統合役ただ1人。
   作業ブランチ（`feature/slice-<slice_id>`）での commit/push は許可されている。
2. **`docs/metrics/events/**` を手で書かない。** 書き込みは bot（`/rescue`・`/gate` 等）経由のみ（ADR-0012）。
3. **`docs/metrics/index/`・`docs/status/` を手で編集しない。** 日次cronが唯一の書き手。
4. **`CLAUDE.md`・`docs/adr/**` を変更しない。** hookでブロックされる。
5. **スライス指示書「3. 触ってよいファイル範囲」の外を変更しない。**
6. **`main` 上で作業しない。**
7. **実データを持ち込まない。** フィクスチャは合成データのみ。
8. **緑になったら停止して報告する。** 次のスライスに進まない。PR も作らない（`/submit` の仕事）。

## 自動停止トリガー（数値で止まる）

- **同一エラーが2回** → 停止。5 Whys を書いて報告する。
- **5ファイル以上を変更、または Edit 5回以上** → 停止して影響範囲を報告する。
- **同じテストを3回リトライして緑にならない** → ハーネスのバグとして報告する。押し切らない。
- 不明点は推測で埋めず、**リーダーへの質問として出して停止**する（`/rescue` で記録される）。

## 手順

1. **枠を読む。** スライス指示書「4. 貼り付け用の枠」の指示に従う。枠に無いことをしない。
2. **赤を確認する。** 変更対象について `python -m pytest tools/slice-aggregator/tests/ -v` を実行し、
   **失敗している（または対象テストがまだ無い）状態を先に確認**する。
3. **規律は `/tdd`。** red → green → refactor。`tools/slice-aggregator/tests/` にテストを追加してよい。
4. **詰まったら `/diagnose`。** 推測でコードを変えない。
5. **最新 API は Context7 に聞く。** 存在しない API を思い出しで書かない。
6. **赤なら** pytest の生ログ（トレースバック）を読んでから直す。読まずに直さない。
7. **events/schema に触れる変更なら** `python tools/slice-aggregator/scripts/validate_events.py` も通す。
8. **緑になったら停止・報告。**

## 報告フォーマット（証拠ベース。「できました」は禁止）

```
## 結果: 緑 / 赤

## 実行したコマンドと生出力
$ <command>
<出力の該当部分>

## 変更したファイル（<n>件）
- <path> — <何をしたか1行>

## 検証方法（指示書「2」）
- [x] <基準1>  … <どのテストが緑か>
- [ ] <基準2>  … <未達なら理由>

## 残課題・気づき
- <あれば>
```

次は `/verify`。
