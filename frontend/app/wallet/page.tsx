"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type LedgerItem, type Page, type WalletBrief } from "@/lib/api";
import { formatDate, signed } from "@/lib/format";
import { RequireLogin } from "@/components/RequireLogin";
import { Card, ErrorBox } from "@/components/ui";

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
  if (!wallet || !ledger) return <p className="py-10 text-center text-muted">불러오는 중…</p>;

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">토큰 지갑</h1>
      <div className="grid grid-cols-2 gap-3">
        <Card className="space-y-1">
          <p className="text-sm text-muted">사용 가능</p>
          <p className="text-3xl font-extrabold text-brand">🪙 {wallet.available.toLocaleString("ko-KR")}</p>
        </Card>
        <Card className="space-y-1">
          <p className="text-sm text-muted">보류 중</p>
          <p className="text-3xl font-extrabold text-muted">{wallet.escrow.toLocaleString("ko-KR")}</p>
          <p className="text-xs text-muted">진행 중인 거래에 묶인 토큰</p>
        </Card>
      </div>

      <section className="space-y-2">
        <h2 className="font-bold">거래 내역</h2>
        {ledger.items.length === 0 ? (
          <p className="text-muted">아직 내역이 없어요.</p>
        ) : (
          <ul className="divide-y divide-border rounded-2xl border border-border bg-card">
            {ledger.items.map((i) => {
              const main = i.available_delta !== 0 ? i.available_delta : i.escrow_delta;
              const escrowOnly = i.available_delta === 0;
              return (
                <li key={i.id} className="flex items-center justify-between gap-3 px-4 py-3">
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
                    <p className={`font-bold ${escrowOnly ? "text-muted" : main > 0 ? "text-green-700" : "text-danger"}`}>
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
