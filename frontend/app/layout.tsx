import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "인연고리 — AI가 찾아 주는 나의 숨은 재능",
  description: "AI가 숨은 재능을 찾아 주고, 토큰으로 서로의 재능을 나누는 대학생 재능 교류 플랫폼",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <AuthProvider>
          <Header />
          <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-16 pt-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
