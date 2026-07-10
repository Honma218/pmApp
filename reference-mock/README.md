# reference-mock/ — 参照モック（answer key）の vendor 予定地

既存 `staff-report-system`（FastAPI / Python）を **git subtree でここに vendor** する（ADR-0005、playbook Step 0）。runner が repo 外を refuse するため、answer key 検証をリポジトリ内で完結させるための配置。

## 取り込み手順（AIアーキ・Step 0）

```bash
git subtree add --prefix reference-mock <staff-report-system の remote> <branch> --squash
```

取り込み後にこの README を残したままソース一式が展開される。`test-harness.runtime.json` の bootCommand・ポートを実際の値に直すこと。

## ルール

- **read-only**。answer key を書き換えて緑にする経路を塞ぐため、`acceptance/` と同じ強制力で保護する（ADR-0005）。※protect-paths への追加は**未実装**（playbook「ハーネス未実装 #5」）。vendor 前に hook へ追加すること。
- 用途は2つだけ: ① `/spec` がテスト翻訳の正しさを検証する対象（緑確認）② golden スクリーンショットの撮影元（ADR-0008）。
- **シードは合成データに限定**（計画書 §6 機密データ L2/L1 規則）。本番データを持ち込まない。
