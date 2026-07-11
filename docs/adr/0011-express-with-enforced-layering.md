---
status: accepted（ADR-0002 を supersede する）
---

# TS バックエンドは Express ＋ 構造規約を採用する（NestJS から変更）

初級者に NestJS のデコレータと DI を同時に教える負荷が高く、AI が生成するボイラープレートを人が読めないと目的C（成功体験）が損なわれる。よって Express を採用する。

ただし **ADR-0002 の本質は「NestJS が好き」ではなく「構造が Spring と 1:1 であること」**だった。その構造は Express でも規約と lint で作れる。したがって本 ADR は ADR-0002 の判断を捨てるのではなく、**構造強制の担い手をフレームワークからハーネスへ移す**ものである。宣言 → 実行時強制 → 事後検証という本プロジェクトの思想とは、むしろこちらの方が整合する。

## 強制する構造（Spring への構文翻訳を保つ）

```
backend/src/<feature>/
├── <feature>.router.ts       ← Spring: @RestController
├── <feature>.service.ts      ← Spring: @Service
├── <feature>.repository.ts   ← Spring: @Repository
└── <feature>.schema.ts       ← Spring: DTO + Bean Validation
```

- **依存の向きは router → service → repository の一方向のみ。** 逆流と飛び越し（router が repository を直接触る）を禁止する。
- **依存は関数引数かファクトリで注入する。** service / repository を `new` で直接生成しない（DI コンテナが無いぶん、規約で代替する）。
- `app.ts` が合成ルート（composition root）。ここだけが具象を組み立てる。

## 機械的強制（宣言だけでは守られない）

| 層 | 実体 |
|---|---|
| 宣言 | `CLAUDE.md` §5、スライス指示書の「触ってよいファイル範囲」 |
| 実行時強制 | Audit の `express-review-rules`（監査型スキル） |
| 事後検証 | **カスタム lint（`eslint-plugin-boundaries` 等）で依存の向きを CI が fail させる** |

**カスタム lint のエラーメッセージには修正手順を書く**（良性のプロンプトインジェクション）。フレームワークが暗黙に守っていた境界を、明示的なエラーとして返すのが本 ADR の要諦。

## 帰結

- **`ValidationPipe` の 422 問題は消える**が、代わりに **Zod / express-validator のエラーハンドラで明示的に 422 を返す**必要がある。参照モック（FastAPI）が 422 を返す以上、ここは受け入れテストの前提。
- Express の非同期エラーは自動で next() に渡らない。**未処理 rejection が 500 にすらならず落ちる。** `express-async-errors` か明示的な try/catch ラッパを合成ルートで1回だけ入れる。
- 受け入れテストはブラックボックス（ADR-0001）なので、**テスト資産・golden はフレームワーク変更の影響を受けない。** ここが ADR-0001 の配当。
- Audit の監査型スキルは `nestjs-review-rules` → **`express-review-rules`** に差し替える（DI / Module 前提のルールは空振りする）。
