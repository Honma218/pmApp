---
name: verify
description: 下流が担う判定（テスト緑・シークレット/PII 未混入）を機械的に○×表示する。知識ゼロで判定できることだけを確認する。Use when the user runs /verify after /implement.
disable-model-invocation: true
---

# /verify

初級者が担う判定は**この2つだけ**（CLAUDE.md §2）。正しさの担保は機械が、最終判断は層境ゲートが持つ。
v0（スライス進捗集計アプリ）は UI を持たないため、旧スコープにあった「画面が参照モック通り」判定は無い。

## 判定1: pytest が緑

- `python -m pytest tools/slice-aggregator/tests/ -v` を実行する。
- `docs/metrics/events/**` に触れる変更なら `python tools/slice-aggregator/scripts/validate_events.py` も実行する。
- **生出力を貼る。** 「passed」の要約行だけでなく、失敗数を含むサマリを提示する。
- 1件でも失敗 → ✗。

## 判定2: シークレット・PII が混ざっていない

`git diff` に対して以下を検査する。1件でもヒットしたら ✗。

- シークレット: `API_KEY` / `SECRET` / `TOKEN` / `PASSWORD` / `-----BEGIN .* PRIVATE KEY-----` / `sk-[A-Za-z0-9]{20,}`
- PII: メールアドレス / 電話番号（`0\d{1,4}-\d{1,4}-\d{4}`）/ マイナンバー形式（12桁連番）
- 実データの痕跡: `*.sql` ダンプ / `fixtures/real*`

## 出力

```
## /verify 結果
- [○/✗] pytest が緑          … <passed n / failed m>
- [○/✗] シークレット・PII なし … <検出 0件 / 検出内容>

判定: 全て○ → /submit へ進んでよい
      1つでも✗ → /implement に戻る（✗のまま /submit しない）
```

**✗ のまま `/submit` を実行しない。** 判定を人の目視だけに委ねない。
