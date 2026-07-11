# backend/ — Express ＋ 構造規約（ADR-0011）

TypeScript / Express。**構造は Spring と 1:1**（ADR-0002 の核心を維持し、強制の担い手をフレームワークからハーネスへ移した）。

## 構造規約

```
backend/src/<feature>/
├── <feature>.router.ts       ← Spring: @RestController
├── <feature>.service.ts      ← Spring: @Service
├── <feature>.repository.ts   ← Spring: @Repository
└── <feature>.schema.ts       ← Spring: DTO + Bean Validation（Zod）
```

- 依存の向きは **router → service → repository の一方向のみ**。逆流・飛び越しは**カスタム lint が CI で fail**（ADR-0011 の前提。nice-to-have ではない）。
- `src/app.ts` が**唯一の合成ルート**。async ハンドラの throw を `next()` へ渡すラッパをここで1回だけ入れる（未処理 rejection 対策）。
- バリデーションエラーは**明示的に 422** を返す（FastAPI answer key との差を実装側で吸収。計画書 付録A注）。
- AI（要約）は Summarizer 抽象化層経由で呼ぶ（ADR-0003）。

## 実装の入り方

scaffolding（package.json / tsconfig / app.ts）は最初のスライスの `spec/*` 工程または slice-01 で作る。下流はスライス指示書「3. ファイル範囲」の feature ディレクトリだけを触る。`test-harness.runtime.json` の bootCommand・ポートは scaffolding 時に実値へ直す。
