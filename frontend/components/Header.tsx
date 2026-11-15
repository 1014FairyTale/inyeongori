"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Logo } from "@/components/Logo";
import { TokenAmount } from "@/components/TokenAmount";

export function Header() {
  const { me, loading, logout } = useAuth();

  return (
    <header className="sticky top-0 z-10 border-b border-foreground bg-background">
      <div className="mx-auto flex h-14 max-w-2xl items-center justify-between gap-3 px-4">
        <Link href="/" aria-label="인연고리 홈">
          <Logo size={22} />
        </Link>
        {loading ? null : me ? (
          <nav className="flex items-center gap-3 text-sm" aria-label="내 계정">
            <Link href="/wallet" aria-label={`내 토큰 ${me.wallet.available}개`}>
              <TokenAmount amount={me.wallet.available} />
            </Link>
            <Link href="/guide?next=/" className="text-muted hover:text-foreground">
              가이드
            </Link>
            <Link href="/me" className="hidden text-muted hover:text-foreground sm:inline">
              {me.user.nickname}
            </Link>
            <button onClick={logout} className="text-muted hover:text-foreground">
              로그아웃
            </button>
          </nav>
        ) : (
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/guide?next=/" className="text-muted hover:text-foreground">
              가이드
            </Link>
            <Link href="/login" className="text-muted hover:text-foreground">
              로그인
            </Link>
            <Link href="/signup" className="bg-brand px-3 py-1.5 font-bold text-white hover:bg-foreground">
              가입하기
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
