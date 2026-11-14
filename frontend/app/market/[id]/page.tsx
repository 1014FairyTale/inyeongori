"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, ApiError, type AgreementTerms, type Exchange, type Listing } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TermsForm } from "@/components/TermsForm";
import { TokenAmount } from "@/components/TokenAmount";
import { Button, Card, ErrorBox } from "@/components/ui";

function ListingDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me, refresh } = useAuth();
  const [listing, setListing] = useState<Listing | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [requesting, setRequesting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Listing>(`/listings/${id}`)
      .then(setListing)
      .catch((e) => setLoadError(e instanceof ApiError ? e.message : "불러오지 못했어요"));
  }, [id]);

  if (loadError) return <ErrorBox message={loadError} />;
  if (!listing) return <p className="py-10 text-center text-muted">불러오는 중…</p>;

  const isMine = me?.user.id === listing.provider.id;
  const lacking = me ? me.wallet.available < listing.price_tokens : false;

  async function sendRequest(terms: AgreementTerms) {
    setSubmitting(true);
    setError(null);
    try {
      const ex = await api<Exchange>("/exchanges", { method: "POST", json: { listing_id: listing!.id, terms } });
      router.push(`/exchanges/${ex.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "요청하지 못했어요. 다시 시도해 주세요");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleStatus() {
    try {
      const next = await api<Listing>(`/listings/${listing!.id}`, {
        method: "PATCH",
        json: { status: listing!.status === "active" ? "paused" : "active" },
      });
      setListing(next);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "바꾸지 못했어요");
    }
  }

  return (
    <div className="space-y-5">
      <Link href="/market" className="text-sm text-muted">
        ← 마켓으로
      </Link>
      <Card className="space-y-3">
        <p className="text-sm font-medium text-brand">{listing.category}</p>
        <h1 className="text-2xl font-bold">{listing.title}</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
          <TokenAmount amount={listing.price_tokens} className="text-base" />
          {listing.est_minutes && <span>예상 {listing.est_minutes}분</span>}
          {listing.completed_count > 0 && <span>· 완료 {listing.completed_count}회</span>}
        </div>
        <p className="whitespace-pre-wrap leading-relaxed">{listing.description}</p>
        <p className="text-sm text-muted">
          제공자 <b className="text-foreground">{listing.provider.nickname}</b>
          {listing.provider.school && ` · ${listing.provider.school}`}
          {listing.provider.major && ` ${listing.provider.major}`}
        </p>
      </Card>

      {error && <ErrorBox message={error} />}

      {isMine ? (
        <Card className="space-y-3">
          <p className="text-sm text-muted">
            내가 올린 재능이에요. {listing.status === "paused" ? "지금은 요청을 받지 않아요." : "요청을 받고 있어요."}
          </p>
          <Button variant="ghost" onClick={toggleStatus}>
            {listing.status === "active" ? "요청 그만 받기" : "다시 요청 받기"}
          </Button>
        </Card>
      ) : !me ? (
        <Link
          href={`/login?next=${encodeURIComponent(`/market/${listing.id}`)}`}
          className="block rounded-xl bg-brand px-4 py-3 text-center font-semibold text-white"
        >
          로그인하고 요청하기
        </Link>
      ) : listing.status === "paused" ? (
        <Card className="text-center text-muted">지금은 요청을 받지 않는 재능이에요.</Card>
      ) : requesting ? (
        <Card className="space-y-3">
          <h2 className="text-lg font-bold">요청서 쓰기</h2>
          <p className="text-sm text-muted">
            보내면 내가 합의서에 먼저 동의한 상태가 돼요. 제공자가 동의하면 <b>{listing.price_tokens}토큰이 보류</b>되고,
            양쪽이 완료를 확인하면 제공자에게 지급돼요.
          </p>
          <TermsForm submitLabel="요청 보내기" submitting={submitting} onSubmit={sendRequest} onCancel={() => setRequesting(false)} />
        </Card>
      ) : (
        <div className="space-y-2">
          <Button onClick={() => setRequesting(true)} disabled={lacking}>
            {listing.price_tokens}토큰으로 요청하기
          </Button>
          {lacking && (
            <p className="text-center text-sm text-danger">
              토큰이 부족해요 (보유 {me.wallet.available}토큰)
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ListingDetailPage() {
  return (
    <Suspense fallback={<p className="py-10 text-center text-muted">불러오는 중…</p>}>
      <ListingDetail />
    </Suspense>
  );
}
