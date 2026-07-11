---
status: superseded（スコープ変更・2026-07-11）
---

> **2026-07-11 追記：本 ADR はスコープ変更（業務アプリ再実装 → スライス進捗集計アプリのみの開発）
> により対象が消滅した。** `acceptance/`・参照モック（answer key）・Java移行の完全仕様という
> 前提が現行スコープに存在しない。詳細・改訂判断は
> `docs/memory-bank/pending-scope-pivot-claude-md-and-adr.md` を参照。以下は当時の記録。

# 受け入れテストはブラックボックス専用（HTTP＋Playwright E2E）に限定する

受け入れテストは「言語非依存の不変資産＝Java 移行の完全仕様」と位置づけるため、起動済みサーバーへの実 HTTP と Playwright E2E のみで書き、実装言語の in-process テスト（supertest 等）を含めない。置き場所は実装から独立したトップレベル `acceptance/` とし、teamdev-test-runner がどのバックエンド（FastAPI モック / TS / Java）でも起動して同一スイートを流せるようにする。これにより、既存 FastAPI モック（answer key）に対して先にスイートを流してテスト自体の正しさを検証でき、モック→TS→Java の2回の移行を同じ緑で担保できる。実装内部の unit テストは各言語で書き捨てとし、不変資産に含めない。

## 役割分担

PM は Given/When/Then の仕様表を正本として書き、実行可能コードへの翻訳は AIアーキ（＋AI）が行う。「上流はコードを書かない」原則はこの翻訳作業を例外としない — 翻訳は"箱"側（AIアーキ）の仕事であり、"文言"の正本は PM に留まる。
