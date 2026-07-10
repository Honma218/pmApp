# frontend/ — Next.js / TypeScript

Next.js（App Router）。**Java/Spring 移行の対象外**——バックエンドを差し替えても画面と golden スクリーンショット（`acceptance/golden/`）は不変の資産として維持される（ADR-0008）。

## ルール

- 下流が触るのはスライス指示書「3. ファイル範囲」の `frontend/app/<feature>/**` のみ。
- 「画面がモック通り」の判定は目視ではなく `toHaveScreenshot()` の機械判定（ADR-0008）。golden とズレたら実装側を直す（golden の撮り直しは `spec/*` 工程のみ）。
- API 呼び出し先は `NEXT_PUBLIC_API_BASE`（既定 `http://localhost:3000`）。

## 実装の入り方

scaffolding（`create-next-app` 相当）は最初のスライスの工程で作る。`test-harness.runtime.json` の bootCommand・ポートは scaffolding 時に実値へ直す。
