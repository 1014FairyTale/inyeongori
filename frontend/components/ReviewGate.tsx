"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { dueLabel, formatDate } from "@/lib/format";

/**
 * 후기 기한 안내와 이용 제한.
 * - 써야 할 후기가 있으면 위에 마감 배너를 보여 줘요 (기한 안에 쓰면 10% 환급).
 * - 기한을 넘긴 후기가 있으면 거래 상세(후기 쓰기) 화면 말고는 막아요. 서버도 같은 규칙으로 막아요.
 */
export function ReviewGate({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  const pathname = usePathname();
  const status = me?.review_status;
  if (!status || status.due.length === 0) return <>{children}</>;

  const overdue = status.due.filter((d) => d.overdue);
  const onReviewPage = status.due.some((d) => pathname === `/exchanges/${d.exchange_id}`);

  if (status.blocked && !onReviewPage) {
    return (
      <div className="space-y-5 py-6">
        <div className="space-y-2 text-center">
          <p className="text-4xl">✍️</p>
          <h1 className="text-xl font-bold">후기를 남겨야 다시 이용할 수 있어요</h1>
          <p className="text-sm text-muted">
            거래가 끝나고 7일이 지나도록 후기를 남기지 않은 거래가 있어요.
            <br />
            후기를 쓰면 바로 다시 이용할 수 있어요.
          </p>
        </div>
        <ul className="space-y-2">
          {overdue.map((d) => (
            <li key={d.exchange_id}>
              <Link
                href={`/exchanges/${d.exchange_id}`}
                className="flex items-center justify-between rounded-2xl border border-danger/40 bg-card p-4"
              >
                <span className="min-w-0">
                  <span className="block truncate font-semibold">{d.listing_title ?? "재능 교환"}</span>
                  <span className="text-xs text-muted">
                    {d.provider_nickname}님 · 마감 {formatDate(d.due_at)}
                  </span>
                </span>
                <span className="shrink-0 rounded-full bg-brand px-3 py-1.5 text-sm font-semibold text-white">후기 쓰기</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="text-center text-xs text-muted">기한이 지난 후기는 10% 환급 대상이 아니에요.</p>
      </div>
    );
  }

  const next = status.due.find((d) => !d.overdue);
  return (
    <>
      {next && !onReviewPage && (
        <Link
          href={`/exchanges/${next.exchange_id}`}
          className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-brand/30 bg-brand-soft px-4 py-3 text-sm"
        >
          <span className="min-w-0">
            ✍️ <b className="truncate">&lsquo;{next.listing_title ?? "재능 교환"}&rsquo;</b> 후기를 남겨 주세요
            <span className="block text-xs text-muted">기한 안에 성의 있게 쓰면 거래 토큰의 10%를 돌려받아요</span>
          </span>
          <span className="shrink-0 rounded-full bg-brand px-2.5 py-1 text-xs font-bold text-white">{dueLabel(next.due_at)}</span>
        </Link>
      )}
      {children}
    </>
  );
}
