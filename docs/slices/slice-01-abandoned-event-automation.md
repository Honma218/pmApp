---
slice_id: 1
---

# slice-01: `abandoned` イベントの自動記録

## 1. ゴール

現在、8種のイベント型のうち `abandoned`（破棄）だけが自動記録の経路を持たない
（`issued`・`rescued`/`rescue_revoked`・`submitted`/`completed`・`gate`/`rejected` は実装済み）。
`/gate`・`/reject`（`.github/workflows/gate.yml`）と同じ信頼モデルで、
`/abandon --reason split|descoped|failed` コメントコマンドから `abandoned` イベントを
記録できるようにする。これで P6 ドッグフーディングに必要な8種すべての記録経路が揃う。

## 2. 検証方法

- `tools/slice-aggregator/scripts/handle_gate_comment.py` に `/abandon` の解析を追加し、
  `tools/slice-aggregator/tests/test_handle_gate_comment.py`（または新規テストファイル）で
  以下を pytest で検証する：
  - `reason` が `split`／`descoped`／`failed` のいずれかであることの検証（それ以外はエラーで記録しない）。
  - `--reason` 省略時はエラーで記録しない（誤記録より記録漏れを許容・確定ログ #B の踏襲）。
  - slice_id 解決（`--slice` 明示 > PRヘッドブランチ > issue本文）は `/gate`・`/reject` と同じ優先順位。
  - 冪等性（同一 `COMMENT_ID` の再実行で二重記録しない）。
- `.github/workflows/gate.yml` の job `if:` に `/abandon` の prefix 判定を追加する
  （既存の allowlist・👀→✅/❌ 応答・bot直コミットの仕組みをそのまま流用）。
- 生成したイベントが `tools/slice-aggregator/scripts/validate_events.py` を通ることをローカルで確認する。
- 既存の pytest（P1〜P6準備で積み上げた72件）が全緑のまま壊れていないことを確認する。

## 3. 触ってよいファイル範囲

- `tools/slice-aggregator/scripts/handle_gate_comment.py`（`/abandon` 解析の追加）
- `tools/slice-aggregator/tests/**`（テスト追加・拡張）
- `.github/workflows/gate.yml`（job `if:` へ `/abandon` を追加）
- `tools/slice-aggregator/README.md`（使い方の追記）
- **触らない**：`CLAUDE.md`・`docs/adr/**`（AI編集不可・PM専用）、`docs/spec/**`（対象外）、
  `docs/slices/**`（本ファイル以外は触らない）

## 4. 貼り付け用の枠

```
/pickup 1
```

## 5. 完了の定義

- pytest 全緑（生ログを提示する）。
- `validate_events.py` が生成イベントに対して緑。
- シークレット・PII が差分に無い。
- 緑 ≠ 仕様充足。層境ゲート（PM の GO/NO-GO）で最終判定する。

## 6. 禁止事項

- `main` を進める操作（commit / push / merge）をしない。作業ブランチでの commit/push のみ許可。
- `CLAUDE.md`・`docs/adr/**` を変更しない（hookでブロックされる。変更提案があれば
  `docs/memory-bank/pending-*.md` に草案として隔離する）。
- 本番/実データを持ち込まない。合成データのみ。
- シークレット・PII を出力や差分に混入させない。
- 「触ってよいファイル範囲」の外を変更しない。
