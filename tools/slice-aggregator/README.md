# slice-aggregator（スライス進捗集計アプリ v0）

M-team のプロセスKPI（AFK完走率ほか）を **Git への投影（projection / read model）** として集計する
Harness-Keeper の道具。**読むだけ。** 唯一の書き込みは `/rescue`（bot 経由）と自身が生成する派生物のみ。

- 設計：`../../2026-07-11_slice-progress-aggregator_確定ログ.md`
- 着手計画：`../../2026-07-11_slice-progress-aggregator_実装ロードマップ.md`
- 承認ゲート：`../../2026-07-11_P0-承認パッケージ.md`（**P0 は8件すべてGO・2026-07-11 PM承認済み**）

## 現在の実装状況（P1：基盤スキーマ）

| 成果物 | 場所 | 役割 |
|---|---|---|
| イベントスキーマ | `schemas/slice-event.schema.json` | 1イベント=1行の NDJSON を検証（draft 2020-12） |
| バリデータ | `scripts/validate_events.py` | スキーマ＋event_id冪等＋append-only（時刻/slice_id整合） |
| CI | `../../.github/workflows/validate-events.yml` | PR 時に events を検証（事後検証層） |
| ゲートログ | `../../docs/metrics/gates.md` | NO-GO種別つき（ADR-0007 改訂の実体・本運用中） |
| テストデータ | `testdata/valid`・`testdata/invalid` | 正常=緑・異常=赤の回帰用 |
| `issued`イベント発火 | `scripts/emit_issued_event.py` ＋ `../../.github/workflows/emit-issued-event.yml` | `docs/slices/slice-NN.md` の merge を検知し起票イベントを記録 |

未実装（次フェーズ）：P2 `fold` 純関数＋再現テスト／P3 `/rescue` Actions／P4 `/pickup` 重複警告／P5 三層集約。

## ローカル実行

```bash
pip install "jsonschema>=4.20"
# 既定 glob（docs/metrics/events/**/*.jsonl）を検証
python tools/slice-aggregator/scripts/validate_events.py
# 個別ファイル
python tools/slice-aggregator/scripts/validate_events.py tools/slice-aggregator/testdata/valid/slice-0007.jsonl
```

終了コード：0=全緑 / 1=検証失敗 / 2=前提エラー（依存欠落・スキーマ不在）。

## イベント型（確定ログ §7）

`issued` `submitted` `rescued` `rescue_revoked` `rejected` `gate` `abandoned` `completed`。
共通必須は `event_id / type / slice_id / at`。型別の必須は schema の `allOf`（if/then）で強制。
`gate` は `verdict=NO-GO` のときのみ `kind`（`rework`/`redecompose`）必須。
