"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { PageLoading } from "@/components/Logo";

function LoginLink() {
  const pathname = usePathname();
  return (
    <Link href={`/login?next=${encodeURIComponent(pathname)}`} className="font-bold text-brand underline underline-offset-4">
      로그인하러 가기
    </Link>
  );
}

/** 로그인한 사용자에게만 children을 보여 줘요. */
export function RequireLogin({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <PageLoading />;
  if (!me) {
    return (
      <div className="space-y-3 border-t border-foreground py-10 text-center">
        <p className="text-lg font-bold">로그인이 필요해요</p>
        <Suspense
          fallback={
            <Link href="/login" className="font-bold text-brand underline underline-offset-4">
              로그인하러 가기
            </Link>
          }
        >
          <LoginLink />
        </Suspense>
      </div>
    );
  }
  return <>{children}</>;
}
