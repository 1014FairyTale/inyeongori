"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const TABS = [
  { href: "/", label: "홈" },
  { href: "/market", label: "마켓" },
  { href: "/match", label: "찾기" },
  { href: "/exchanges", label: "거래" },
  { href: "/wallet", label: "지갑" },
];

const UNREAD_POLL_MS = 15000;

/** 로그인 상태면 안 읽은 채팅 수를 15초마다 확인해서 '거래' 탭에 표시해요. */
function useUnreadTotal(): number {
  const { me } = useAuth();
  const [total, setTotal] = useState(0);
  useEffect(() => {
    if (!me) return;
    let cancelled = false;
    const check = () =>
      api<{ total: number }>("/exchanges/unread")
        .then((r) => !cancelled && setTotal(r.total))
        .catch(() => undefined);
    void check();
    const t = setInterval(() => document.visibilityState === "visible" && void check(), UNREAD_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [me]);
  return me ? total : 0;
}

export function BottomNav() {
  const pathname = usePathname();
  const unread = useUnreadTotal();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-foreground bg-background" aria-label="주요 메뉴">
      <ul className="mx-auto flex max-w-2xl">
        {TABS.map((t) => {
          const active = t.href === "/" ? pathname === "/" : pathname.startsWith(t.href);
          const badge = t.href === "/exchanges" && unread > 0;
          return (
            <li key={t.href} className="flex-1">
              <Link
                href={t.href}
                aria-current={active ? "page" : undefined}
                className={`flex h-14 items-center justify-center gap-1 border-t-2 text-sm ${
                  active ? "border-brand font-bold text-foreground" : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                {t.label}
                {badge && (
                  <span className="text-xs font-bold text-brand tabular-nums">
                    {unread > 99 ? "99+" : unread}
                    <span className="sr-only">개의 안 읽은 메시지</span>
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
