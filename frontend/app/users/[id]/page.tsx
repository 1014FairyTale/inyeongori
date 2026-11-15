"use client";

import { useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, ApiError, type Listing, type Page, type PublicProfile, type PublicReview } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { AiBadge } from "@/components/AiBadge";
import { ListingCard } from "@/components/ListingCard";
import { Card, ErrorBox } from "@/components/ui";
import { PageLoading } from "@/components/Logo";

function Profile() {
  const { id } = useParams<{ id: string }>();
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [reviews, setReviews] = useState<PublicReview[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<PublicProfile>(`/users/${id}`)
      .then(setProfile)
      .catch((e) => setError(e instanceof ApiError ? e.message : "불러오지 못했어요"));
    api<Page<Listing>>(`/listings?provider_id=${id}`)
      .then((p) => setListings(p.items))
      .catch(() => setListings([]));
    api<PublicReview[]>(`/users/${id}/reviews`)
      .then(setReviews)
      .catch(() => setReviews([]));
  }, [id]);

  if (error) return <ErrorBox message={error} />;
  if (!profile) return <PageLoading />;

  return (
    <div className="space-y-6">
      <Card className="space-y-1">
        <h1 className="text-3xl font-black">{profile.user.nickname}</h1>
        <p className="text-sm text-muted">
          {[profile.user.school, profile.user.major].filter(Boolean).join(" · ") || "학교·전공 미입력"}
          {` · 완료 ${profile.completed_count}회`}
          {profile.rating_avg != null && profile.rating_count > 0 && ` · ${profile.rating_avg.toFixed(1)} (${profile.rating_count})`}
        </p>
        {profile.bio && <p className="pt-2 text-sm">{profile.bio}</p>}
      </Card>

      <section className="space-y-2">
        <h2 className="text-lg font-bold">재능</h2>
        {profile.talents.length === 0 ? (
          <p className="text-sm text-muted">아직 확정한 재능이 없어요.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {profile.talents.map((t) => (
              <li key={t.id} className="flex items-center gap-1.5 border border-line px-3 py-1.5 text-sm">
                {t.name}
                {t.source === "ai_confirmed" && <AiBadge label="AI가 찾음" />}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-bold">재능 상품</h2>
        {listings.length === 0 ? (
          <p className="text-sm text-muted">아직 올린 상품이 없어요.</p>
        ) : (
          listings.map((l) => <ListingCard key={l.id} listing={l} />)
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-bold">받은 후기 {reviews.length > 0 && <span className="text-muted">{reviews.length}</span>}</h2>
        {reviews.length === 0 ? (
          <p className="text-sm text-muted">아직 받은 후기가 없어요.</p>
        ) : (
          <ul className="space-y-2">
            {reviews.map((r) => (
              <li key={r.id} className="space-y-1 border-b border-line py-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-brand">{"★".repeat(r.rating)}<span className="text-line">{"★".repeat(5 - r.rating)}</span></span>
                  <span className="text-xs text-muted">{formatDate(r.created_at)}</span>
                </div>
                <p>{r.good_text}</p>
                {r.bad_text && <p className="text-muted">아쉬운 점: {r.bad_text}</p>}
                <p className="text-xs text-muted">
                  {r.reviewer_nickname}
                  {r.listing_title && ` · ${r.listing_title}`}
                  {r.bonus > 0 && <span className="font-semibold text-brand"> · AI 보너스 +{r.bonus}</span>}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function UserPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Profile />
    </Suspense>
  );
}
