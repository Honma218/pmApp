"use client";

// ログアウトは /auth/logout(POST) をプロキシ経由で呼び、その後ログイン画面へ遷移する。
export function LogoutButton() {
  async function handleLogout() {
    await fetch("/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  return (
    <button type="button" className="link-button" onClick={handleLogout}>
      ログアウト
    </button>
  );
}
