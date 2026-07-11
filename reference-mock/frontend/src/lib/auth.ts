import { cookies } from "next/headers";

import { BACKEND_ORIGIN } from "./config";

// バックエンドの /auth/me が返すユーザー表現（UserOut に対応）。
export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  role: string;
};

/**
 * 現在のログインユーザーをサーバー側で解決する。
 *
 * 受信リクエストの Cookie（httpOnly のセッション含む）をバックエンド /auth/me に
 * 転送して検証する。未ログイン・検証失敗時は null を返す。
 * 認可の最終強制はバックエンド側で行うため、ここでの判定は画面ガード用途。
 */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  const cookieHeader = cookies().toString();
  if (!cookieHeader) {
    return null;
  }
  try {
    const res = await fetch(`${BACKEND_ORIGIN}/auth/me`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as CurrentUser;
  } catch {
    // バックエンド未起動・接続不可などは未ログイン扱いにフォールバック。
    return null;
  }
}
