"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui";

function LoginLink() {
  const pathname = usePathname();
  return (
    <Link href={`/login?next=${encodeURIComponent(pathname)}`} className="font-semibold text-brand">
      로그인하러 가기
    </Link>
  );
}

/** 로그인한 사용자에게만 children을 보여 줘요. */
export function RequireLogin({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <p className="py-10 text-center text-muted">불러오는 중…</p>;
  if (!me) {
    return (
      <Card className="space-y-3 text-center">
        <p>로그인이 필요해요.</p>
        <Suspense
          fallback={
            <Link href="/login" className="font-semibold text-brand">
              로그인하러 가기
            </Link>
          }
        >
          <LoginLink />
        </Suspense>
      </Card>
    );
  }
  return <>{children}</>;
}
