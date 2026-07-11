# acceptance/ — 受け入れテスト（仕様＝read-only）

**ブラックボックス専用**の受け入れテスト置き場（ADR-0001）。起動済みサーバーへの実 HTTP＋Playwright E2E のみ。in-process / unit テストは置かない。**言語非依存の不変資産**であり、Java/Spring 移行時の完全仕様になる。

## 所有と書込権

- 正本は **PM の仕様表（Given/When/Then、`docs/spec/`）**。コード翻訳は AIアーキが `/spec <slice>` で行う。
- 書込は **`spec/*` ブランチのみ**（ADR-0004。ブランチ名で判定）。`feature/*` からの変更は宣言（CLAUDE.md）・hook（protect-paths）・CI（guard-acceptance.yml）の**三層でブロック**される。
- 下流（実装メンバー）にとってここは**読み取り専用**。テストを書き換えて緑にするのは不正。

## 対象の切替（ADR-0005）

テストは `ACCEPTANCE_BASE_URL` で対象を切り替える:

| 対象 | 用途 |
|---|---|
| `reference-mock/`（FastAPI answer key） | 翻訳直後に**緑**を確認（テスト自体の検証） |
| `backend/`（Express） | 下流に渡す前に**赤**を確認 → 実装で緑化 |

## 構成

```
acceptance/
├── <feature>/*.spec.ts   ← 例: reports/create.spec.ts
└── golden/               ← golden スクリーンショット（ADR-0008）
```

`golden/` は `spec/*` 工程で**実装より先に**参照モックから撮り、`toHaveScreenshot()` で「画面がモック通り」を機械判定する。撮り直しも `acceptance/` と同じ保護に服する。
