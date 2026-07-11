import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/LogoutButton";
import { getCurrentUser } from "@/lib/auth";

// 保護ルートのサーバーサイドガード。
// 未ログイン（/auth/me が 401 等）の場合はレンダリング前に /login へリダイレクトする。
export default async function ProtectedLayout({
  children,
}: {
  children: ReactNode;
}) {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <>
      <div className="user-bar">
        <nav className="nav-links">
          <Link href="/report">入力</Link>
          <Link href="/reports">過去の報告</Link>
        </nav>
        <span>
          {user.name}（{user.role}）
        </span>
        <LogoutButton />
      </div>
      {children}
    </>
  );
}
