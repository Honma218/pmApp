// サーバー側（SSR / RSC）から FastAPI バックエンドへ直接接続する先。
// ブラウザ向けの導線は next.config.mjs の rewrites プロキシを使う。
export const BACKEND_ORIGIN =
  process.env.BACKEND_ORIGIN || "http://localhost:8000";
