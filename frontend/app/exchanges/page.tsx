"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type ExchangeSummary } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { RequireLogin } from "@/components/RequireLogin";
import { StatusBadge } from "@/components/StatusBadge";
import { TokenAmount } from "@/components/TokenAmount";
import { ErrorBox } from "@/components/ui";

const TABS = [
  { key: "all", label: "전체" },
  { key: "sent", label: "보낸 요청" },
  { key: "received", label: "받은 요청" },
] as const;

function ExchangeList() {
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("all");
  const [items, setItems] = useState<ExchangeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<ExchangeSummary[]>(`/exchanges?role=${tab}`)
      .then((d) => !cancelled && setItems(d))
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : "불러오지 못했어요"));
    return () => {
      cancelled = true;
    };
  }, [tab]);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">내 거래</h1>
      <div className="flex gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-full border px-3 py-1.5 text-sm ${
              tab === t.key ? "border-brand bg-brand text-white" : "border-border bg-card text-muted"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {error ? (
        <ErrorBox message={error} />
      ) : !items ? (
        <p className="py-10 text-center text-muted">불러오는 중…</p>
      ) : items.length === 0 ? (
        <p className="py-10 text-center text-muted">
          아직 거래가 없어요.{" "}
          <Link href="/market" className="font-medium text-brand">
            마켓 둘러보기
          </Link>
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((x) => (
            <li key={x.id}>
              <Link href={`/exchanges/${x.id}`} className="block rounded-2xl border border-border bg-card p-4 hover:border-brand">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={x.status} />
                    {x.needs_my_action && (
                      <span className="rounded-full bg-brand px-2 py-0.5 text-xs font-bold text-white">내 차례</span>
                    )}
                    {x.unread_count > 0 && (
                      <span className="rounded-full bg-ai px-2 py-0.5 text-xs font-bold text-white">💬 {x.unread_count}</span>
                    )}
                  </div>
                  <TokenAmount amount={x.price_tokens} />
                </div>
                <p className="mt-2 truncate font-semibold">{x.listing_title ?? "재능 교환"}</p>
                <p className="text-sm text-muted">
                  {x.my_role === "requester" ? "보낸 요청" : "받은 요청"} · {x.counterpart.nickname} · {formatDate(x.created_at)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ExchangesPage() {
  return (
    <RequireLogin>
      <ExchangeList />
    </RequireLogin>
  );
}
