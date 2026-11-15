"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type LedgerItem, type Page, type WalletBrief } from "@/lib/api";
import { formatDate, signed } from "@/lib/format";
import { RequireLogin } from "@/components/RequireLogin";
import { ErrorBox } from "@/components/ui";
import { PageLoading } from "@/components/Logo";

function Wallet() {
  const [wallet, setWallet] = useState<WalletBrief | null>(null);
  const [ledger, setLedger] = useState<Page<LedgerItem> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<WalletBrief>("/wallet"), api<Page<LedgerItem>>("/wallet/ledger?size=50")])
      .then(([w, l]) => {
        setWallet(w);
        setLedger(l);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "불러오지 못했어요"));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!wallet || !ledger) return <PageLoading />;

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-black">토큰 지갑</h1>
      <section className="border-t border-foreground pt-4">
        <p className="text-sm text-muted">사용 가능</p>
        <p className="text-6xl font-black tracking-tight text-brand">
          {wallet.available.toLocaleString("ko-KR")}
          <span className="ml-2 text-lg font-bold text-foreground">토큰</span>
        </p>
        <p className="mt-3 border-t border-line pt-3 text-sm">
          <span className="text-muted">보류 중 </span>
          <b>{wallet.escrow.toLocaleString("ko-KR")} 토큰</b>
          <span className="text-muted"> · 진행 중인 거래에 묶인 토큰이에요</span>
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="border-b border-foreground pb-2 font-bold">거래 내역</h2>
        {ledger.items.length === 0 ? (
          <p className="text-muted">아직 내역이 없어요.</p>
        ) : (
          <ul className="divide-y divide-line border-b border-line">
            {ledger.items.map((i) => {
              const main = i.available_delta !== 0 ? i.available_delta : i.escrow_delta;
              const escrowOnly = i.available_delta === 0;
              return (
                <li key={i.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="font-medium">{i.label}</p>
                    <p className="truncate text-xs text-muted">
                      {formatDate(i.created_at)}
                      {i.listing_title && (
                        <>
                          {" · "}
                          {i.exchange_id ? <Link href={`/exchanges/${i.exchange_id}`}>{i.listing_title}</Link> : i.listing_title}
                        </>
                      )}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className={`font-bold ${escrowOnly ? "text-muted" : main > 0 ? "text-success" : "text-danger"}`}>
                      {signed(main)}
                    </p>
                    {escrowOnly && <p className="text-xs text-muted">보류에서</p>}
                    {!escrowOnly && i.escrow_delta !== 0 && (
                      <p className="text-xs text-muted">보류 {signed(i.escrow_delta)}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function WalletPage() {
  return (
    <RequireLogin>
      <Wallet />
    </RequireLogin>
  );
}
