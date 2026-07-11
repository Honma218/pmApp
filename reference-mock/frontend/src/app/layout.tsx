import "./globals.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "業務報告・スキルシート生成システム",
  description: "客先常駐スタッフの業務報告・要約・職務経歴自動生成基盤",
};

// スタッフ入力はモバイルファースト前提のため viewport を明示する。
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <header className="app-bar">
          <span className="app-title">業務報告システム</span>
        </header>
        {children}
      </body>
    </html>
  );
}
