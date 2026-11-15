import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { Header } from "@/components/Header";
import { BottomNav } from "@/components/BottomNav";
import { ReviewGate } from "@/components/ReviewGate";

export const metadata: Metadata = {
  title: "인연고리 — AI가 찾아 주는 나의 숨은 재능",
  description: "AI가 숨은 재능을 찾아 주고, 토큰으로 서로의 재능을 나누는 재능 교류 플랫폼",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="h-full antialiased">
      <head>
        {/* 한글 본문 글꼴: Pretendard (쓰는 글자만 나눠 받는 버전) */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="flex min-h-full flex-col">
        <AuthProvider>
          <Header />
          <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-10 pt-8">
            {/* 후기 마감 배너·이용 제한 (usePathname 때문에 Suspense 필요) */}
            <Suspense fallback={children}>
              <ReviewGate>{children}</ReviewGate>
            </Suspense>
          </main>
          <footer className="mx-auto w-full max-w-2xl px-4 pb-24 pt-6 text-xs text-muted">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-t border-line pt-4">
              <span>인연고리 · 재능 교류 플랫폼</span>
              <span>We:Write · TEAM 14</span>
            </div>
          </footer>
          <Suspense fallback={null}>
            <BottomNav />
          </Suspense>
        </AuthProvider>
      </body>
    </html>
  );
}
