/** @type {import('next').NextConfig} */

// バックエンド(FastAPI)の接続先。ブラウザからは下記 rewrites 経由で同一オリジンに
// 見せ、httpOnly セッション Cookie をファーストパーティで扱う（CORS 不要）。
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // 認証導線（/auth/login → Google, /auth/callback, /auth/logout, /auth/me）
      { source: "/auth/:path*", destination: `${BACKEND_ORIGIN}/auth/:path*` },
      // 業務 API（後続ステップで /api/* を使用）
      { source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` },
    ];
  },
};

export default nextConfig;
