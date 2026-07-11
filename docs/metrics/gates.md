# 層境ゲート判定ログ（ADR-0007 / 改訂 2026-07-11）

> **status: 生成物（slice-02・2026-07-11）。手動編集しないこと。**
> `docs/metrics/events/**` の `gate` イベントから日次cronが再生成する
> （`docs/metrics/index/slice-map.json` と同じ扱い）。判定は `/gate GO` 等のコメント
> コマンドで記録する（`tools/slice-aggregator/README.md` 参照）。

全 PR に層境ゲートが掛かる（ADR-0007）。**判定者は PM**（代理はリーダー1名。`GATE_KEEPERS` で強制）。
**NO-GO のときは種別（`rework`/`redecompose`）が必須**——`/gate` コマンド自体が入力を強制する
（ADR-0007 改訂の実体）。

## 記録ルール

- `rework` … 修正で足りる。**同一 slice_id を継続**。→ 差し戻し率の分子。
- `redecompose` … 分解し直し。**子スライスを新規 slice_id で起票**。→ 肥大率側（分解の失敗）。
- 種別を分けるのは、両者の原因が異なる（実装の雑さ vs 分解の雑さ）ため。混ぜると CLAUDE.md §3 の2分類原則が働かない。

## 判定ログ（`gate` イベントから生成。手動編集しないこと）

| slice_id | 日付 | 判定 | NO-GO種別 | PM/代理 |
|---|---|---|---|---|
| | | | | |
