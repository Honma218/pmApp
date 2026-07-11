---
slice_id: 2
---

# slice-02: `gates.md` を events 由来の生成物に変える

## 1. ゴール

`docs/metrics/gates.md` は現在「PM が手で1行記録する任意ログ」と「KPI計算が読む
`docs/metrics/events/**` の `gate` イベント」の**二重管理**になっている
（`docs/memory-bank/pending-gate-before-merge-procedure.md` で発見）。
`docs/metrics/index/slice-map.json` と同じ「events から生成する派生物」に変え、
手動編集を廃止することで二重管理・食い違いのリスクを構造的に無くす。

## 2. 検証方法

- `tools/slice-aggregator/scripts/generate_daily_snapshot.py`（または新規スクリプト）に、
  `gate` イベントから `docs/metrics/gates.md` の判定ログ表を再生成する処理を追加する。
- 生成ロジックは `fold.py` と同様の純関数として実装し、`tools/slice-aggregator/tests/` に
  単体テストを追加する：
  - `gate` イベント（GO・NO-GO×kind別）から正しい行が生成されること。
  - `gate` イベントが1件も無ければ、見出し・記録ルール説明は残しつつ判定ログ表は空になること
    （現状の空テーブルと同じ見た目を維持）。
  - 決定性（同一イベント列から常に同じ出力）。
- 既存の pytest（80件）が壊れていないことを確認する。
- ローカルで `generate_daily_snapshot.py`（等）を実行し、`gates.md` が正しく再生成されることを
  目視確認する（生成物は確認後に削除するか、実データがあればそのままコミット対象にする）。

## 3. 触ってよいファイル範囲

- `tools/slice-aggregator/scripts/**`（生成ロジックの追加）
- `tools/slice-aggregator/tests/**`
- `.github/workflows/daily-status-cron.yml`（生成ステップの追加のみ）
- `docs/metrics/gates.md`（生成物に置き換え。手動記入の案内文は「編集しないこと」に書き換える）
- `tools/slice-aggregator/README.md`（使い方の更新）
- **触らない**：`CLAUDE.md`・`docs/adr/**`（AI編集不可）、`docs/spec/**`、他の `docs/slices/*.md`

## 4. 貼り付け用の枠

```
/pickup 2
```

## 5. 完了の定義

- pytest 全緑（生ログを提示する）。
- `validate_events.py` が既存イベントに対して緑のまま（events の形式は変更しない）。
- シークレット・PII が差分に無い。
- 緑 ≠ 仕様充足。層境ゲート（PM の GO/NO-GO）で最終判定する。

## 6. 禁止事項

- `main` を進める操作（commit / push / merge）をしない。作業ブランチでの commit/push のみ許可。
- `CLAUDE.md`・`docs/adr/**` を変更しない。
- `docs/metrics/events/**` のイベント形式（スキーマ）自体は変更しない
  （読み取り専用として扱い、`gate` イベントに新フィールドを追加しない。
  「代理」「備考」列が events に無い場合は、生成後の表からその列を削るか空欄固定にしてよい）。
- 本番/実データを持ち込まない。合成データのみ。
- 「触ってよいファイル範囲」の外を変更しない。
