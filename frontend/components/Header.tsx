"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { TokenAmount } from "@/components/TokenAmount";

function GuideLink() {
  return (
    <Link
      href="/guide?next=/"
      aria-label="이용 가이드"
      title="이용 가이드"
      className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-xs font-bold text-muted hover:border-brand hover:text-brand"
    >
      ?
    </Link>
  );
}

export function Header() {
  const { me, loading, logout } = useAuth();

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-2xl items-center justify-between px-4">
        <Link href="/" className="text-lg font-bold text-brand">
          인연고리
        </Link>
        {loading ? null : me ? (
          <div className="flex items-center gap-3 text-sm">
            <GuideLink />
            <TokenAmount amount={me.wallet.available} />
            <Link href="/me" className="text-muted">
              {me.user.nickname}님
            </Link>
            <button onClick={logout} className="text-muted underline-offset-2 hover:underline">
              로그아웃
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3 text-sm">
            <GuideLink />
            <Link href="/login" className="text-muted">
              로그인
            </Link>
            <Link href="/signup" className="rounded-full bg-brand px-3 py-1.5 font-semibold text-white">
              가입하기
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
