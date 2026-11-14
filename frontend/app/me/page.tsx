"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Listing, type Page, type Talent } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AiBadge } from "@/components/AiBadge";
import { ListingCard } from "@/components/ListingCard";
import { RequireLogin } from "@/components/RequireLogin";
import { Button, Card, ErrorBox, Field } from "@/components/ui";

function Profile() {
  const { me } = useAuth();
  const [talents, setTalents] = useState<Talent[] | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", category: "", description: "" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api<Talent[]>("/users/me/talents").then(setTalents).catch(() => setTalents([]));
    api<Page<Listing>>(`/listings?provider_id=${me.user.id}&include_paused=true`)
      .then((p) => setListings(p.items))
      .catch(() => setListings([]));
    api<string[]>("/listings/categories").then(setCategories).catch(() => setCategories([]));
  }, [me]);

  if (!me) return null;

  async function add(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const t = await api<Talent>("/users/me/talents", {
        method: "POST",
        json: { name: form.name, category: form.category, description: form.description || null },
      });
      setTalents((ts) => [...(ts ?? []), t]);
      setForm({ name: "", category: "", description: "" });
      setAdding(false);
    } catch (err) {
      setError(err instanceof ApiError && err.code !== "VALIDATION_ERROR" ? err.message : "이름(2자 이상)과 카테고리를 확인해 주세요");
    }
  }

  async function remove(id: number) {
    if (!window.confirm("이 재능을 프로필에서 뺄까요?")) return;
    try {
      await api<void>(`/users/me/talents/${id}`, { method: "DELETE" });
      setTalents((ts) => (ts ?? []).filter((t) => t.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "빼지 못했어요");
    }
  }

  return (
    <div className="space-y-6">
      <Card className="space-y-1">
        <h1 className="text-2xl font-bold">{me.user.nickname}</h1>
        <p className="text-sm text-muted">
          {[me.user.school, me.user.major].filter(Boolean).join(" · ") || "학교·전공 미입력"}
        </p>
        {me.user.bio && <p className="pt-2 text-sm">{me.user.bio}</p>}
      </Card>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">내 재능</h2>
          <Link href="/onboarding" className="text-sm font-medium text-ai">
            ✨ AI로 더 찾기
          </Link>
        </div>
        {talents === null ? (
          <p className="text-muted">불러오는 중…</p>
        ) : talents.length === 0 ? (
          <Card className="space-y-3 text-center">
            <p className="text-muted">아직 확정한 재능이 없어요.</p>
            <Link href="/onboarding" className="font-semibold text-brand">
              AI로 내 재능 찾기
            </Link>
          </Card>
        ) : (
          <ul className="space-y-2">
            {talents.map((t) => (
              <li key={t.id} className="flex items-start justify-between gap-3 rounded-2xl border border-border bg-card p-4">
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold">{t.name}</p>
                    {t.source === "ai_confirmed" && <AiBadge label="AI가 찾음" />}
                  </div>
                  <p className="text-xs text-brand">{t.category}</p>
                  {t.description && <p className="text-sm text-muted">{t.description}</p>}
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2 text-sm">
                  <Link
                    href={`/market/new?${new URLSearchParams({ title: t.name, category: t.category, description: t.description ?? "" })}`}
                    className="font-medium text-brand"
                  >
                    마켓에 올리기
                  </Link>
                  <button onClick={() => remove(t.id)} className="text-muted">
                    빼기
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {adding ? (
          <Card>
            <form onSubmit={add} className="space-y-3" noValidate>
              <Field label="재능 이름" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={40} />
              <label className="block space-y-1.5">
                <span className="text-sm font-medium">카테고리</span>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="w-full rounded-xl border border-border bg-card px-3.5 py-3"
                >
                  <option value="">골라 주세요</option>
                  {categories.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              <Field
                label="해 줄 수 있는 도움 (선택)"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                maxLength={200}
              />
              {error && <ErrorBox message={error} />}
              <div className="flex gap-2">
                <Button type="button" variant="ghost" onClick={() => setAdding(false)}>
                  취소
                </Button>
                <Button type="submit">추가</Button>
              </div>
            </form>
          </Card>
        ) : (
          <Button variant="ghost" onClick={() => setAdding(true)}>
            + 직접 추가
          </Button>
        )}
        {!adding && error && <ErrorBox message={error} />}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-bold">내가 올린 재능 상품</h2>
        {listings.length === 0 ? (
          <p className="text-sm text-muted">아직 올린 상품이 없어요.</p>
        ) : (
          listings.map((l) => <ListingCard key={l.id} listing={l} />)
        )}
      </section>
    </div>
  );
}

export default function MePage() {
  return (
    <RequireLogin>
      <Profile />
    </RequireLogin>
  );
}
