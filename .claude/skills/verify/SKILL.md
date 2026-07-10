---
name: verify
description: 下流が担う3判定（テスト緑・画面がモック通り・シークレット/PII 未混入）を機械的に○×表示する。知識ゼロで判定できることだけを確認する。Use when the user runs /verify after /implement.
disable-model-invocation: true
---

# /verify

初級者が担う判定は**この3つだけ**。正しさの担保は機械が、最終判断は層境ゲートが持つ。

## 判定1: テストが緑

- `harness_start` → ready → 受け入れテスト実行。
- **生出力を貼る。** 「passed」の要約行だけでなく、失敗数を含むサマリを提示する。
- 1件でも失敗 → ✗。

## 判定2: 画面が参照モック通り

- 画面要件のあるスライスのみ。Playwright のスクリーンショットを取得し、参照モックの該当画面と比較する。
- 画面要件が無いスライスは「該当なし」と書く（○にしない）。

## 判定3: シークレット・PII が混ざっていない

`git diff` と直近のテスト出力に対して以下を検査する。1件でもヒットしたら ✗。

- シークレット: `API_KEY` / `SECRET` / `TOKEN` / `PASSWORD` / `-----BEGIN .* PRIVATE KEY-----` / `sk-[A-Za-z0-9]{20,}`
- PII: メールアドレス / 電話番号（`0\d{1,4}-\d{1,4}-\d{4}`）/ マイナンバー形式（12桁連番）
- 実データの痕跡: `*.sql` ダンプ / `fixtures/real*`

## 出力

```
## /verify 結果
- [○/✗] テストが緑        … <passed n / failed m>
- [○/✗/該当なし] 画面がモック通り … <screenshot path>
- [○/✗] シークレット・PII なし  … <検出 0件 / 検出内容>

判定: 全て○ → /submit へ進んでよい
      1つでも✗ → /implement に戻る（✗のまま /submit しない）
```

**✗ のまま `/submit` を実行しない。** 判定を人の目視だけに委ねない。
