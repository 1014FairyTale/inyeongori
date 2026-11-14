"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Listing } from "@/lib/api";
import { RequireLogin } from "@/components/RequireLogin";
import { Button, Card, ErrorBox, Field, TextArea } from "@/components/ui";

function NewListingForm() {
  const router = useRouter();
  const params = useSearchParams(); // 내 재능에서 넘어오면 제목·카테고리·설명을 미리 채워요
  const [categories, setCategories] = useState<string[]>([]);
  const [form, setForm] = useState({
    title: params.get("title") ?? "",
    description: params.get("description") ?? "",
    category: params.get("category") ?? "",
    price_tokens: "",
    est_minutes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api<string[]>("/listings/categories").then(setCategories).catch(() => setCategories([]));
  }, []);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.category) return setError("카테고리를 골라 주세요");
    setError(null);
    setSubmitting(true);
    try {
      const listing = await api<Listing>("/listings", {
        method: "POST",
        json: {
          title: form.title,
          description: form.description,
          category: form.category,
          price_tokens: Number(form.price_tokens),
          est_minutes: form.est_minutes ? Number(form.est_minutes) : null,
        },
      });
      router.push(`/market/${listing.id}`);
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "VALIDATION_ERROR"
          ? "제목(2자 이상), 설명(5자 이상), 가격(1~500토큰)을 확인해 주세요"
          : err instanceof ApiError
            ? err.message
            : "등록하지 못했어요. 다시 시도해 주세요",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">재능 등록</h1>
      <Card>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <Field label="제목" placeholder="예: 테트리스 기초 알려 드려요" value={form.title} onChange={set("title")} maxLength={80} />
          <TextArea
            label="설명"
            placeholder="어떤 도움을 줄 수 있는지, 어떻게 진행하는지 적어 주세요"
            value={form.description}
            onChange={set("description")}
            maxLength={2000}
          />
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">카테고리</span>
            <select
              value={form.category}
              onChange={set("category")}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-3 text-base outline-none focus:border-brand"
            >
              <option value="">골라 주세요</option>
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="가격 (토큰)"
              type="number"
              min={1}
              max={500}
              placeholder="예: 50"
              value={form.price_tokens}
              onChange={set("price_tokens")}
              hint="직접 정해요"
            />
            <Field
              label="예상 소요 시간(분)"
              type="number"
              min={5}
              max={600}
              placeholder="선택"
              value={form.est_minutes}
              onChange={set("est_minutes")}
              hint="참고용이에요"
            />
          </div>
          {error && <ErrorBox message={error} />}
          <Button type="submit" disabled={submitting}>
            {submitting ? "등록하는 중…" : "등록하기"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

export default function NewListingPage() {
  return (
    <RequireLogin>
      <Suspense fallback={<p className="py-10 text-center text-muted">불러오는 중…</p>}>
        <NewListingForm />
      </Suspense>
    </RequireLogin>
  );
}
