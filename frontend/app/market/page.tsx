"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, ApiError, type Listing, type Page } from "@/lib/api";
import { ListingCard } from "@/components/ListingCard";
import { Button, ErrorBox } from "@/components/ui";

export default function MarketPage() {
  return (
    <Suspense fallback={<p className="py-10 text-center text-muted">불러오는 중…</p>}>
      <Market />
    </Suspense>
  );
}

function Market() {
  const initialQ = useSearchParams().get("q") ?? ""; // 부탁 쪼개기에서 '마켓에서 찾기'로 넘어올 때
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState<string | null>(null);
  const [q, setQ] = useState(initialQ);
  const [query, setQuery] = useState(initialQ);
  const [data, setData] = useState<Page<Listing> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    api<string[]>("/listings/categories").then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({ size: "50" });
    if (query) params.set("q", query);
    if (category) params.set("category", category);
    api<Page<Listing>>(`/listings?${params}`)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : "목록을 불러오지 못했어요"));
    return () => {
      cancelled = true;
    };
  }, [query, category, reloadKey]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">재능 마켓</h1>
        <Link href="/market/new" className="rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white">
          + 재능 등록
        </Link>
      </div>
      <Link href="/plans" className="block rounded-xl bg-ai-soft px-4 py-3 text-sm text-ai">
        ✂️ 뭘 부탁해야 할지 막막하다면? <b>큰 목표를 작은 부탁으로 쪼개 보세요 →</b>
      </Link>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(q.trim());
        }}
        className="flex gap-2"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="어떤 도움이 필요하세요? 예: PPT, 엑셀"
          className="min-w-0 flex-1 rounded-xl border border-border bg-card px-3.5 py-2.5 outline-none focus:border-brand"
          maxLength={50}
        />
        <button className="rounded-xl bg-foreground px-4 text-sm font-semibold text-white">검색</button>
      </form>

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {[null, ...categories].map((c) => (
          <button
            key={c ?? "all"}
            onClick={() => setCategory(c)}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-sm ${
              category === c ? "border-brand bg-brand text-white" : "border-border bg-card text-muted"
            }`}
          >
            {c ?? "전체"}
          </button>
        ))}
      </div>

      {error ? (
        <div className="space-y-3">
          <ErrorBox message={error} />
          <Button variant="ghost" onClick={() => setReloadKey((k) => k + 1)}>
            다시 시도
          </Button>
        </div>
      ) : !data ? (
        <p className="py-10 text-center text-muted">불러오는 중…</p>
      ) : data.items.length === 0 ? (
        <p className="py-10 text-center text-muted">
          {query || category ? "조건에 맞는 재능이 아직 없어요." : "아직 등록된 재능이 없어요. 첫 재능을 올려 보세요!"}
        </p>
      ) : (
        <div className="space-y-3">
          {data.items.map((l) => (
            <ListingCard key={l.id} listing={l} />
          ))}
        </div>
      )}
    </div>
  );
}
