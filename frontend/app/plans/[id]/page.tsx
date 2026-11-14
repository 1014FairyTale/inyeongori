"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, ApiError, type Plan, type PlanItem } from "@/lib/api";
import { AiBadge } from "@/components/AiBadge";
import { RequireLogin } from "@/components/RequireLogin";
import { TokenAmount } from "@/components/TokenAmount";
import { Button, Card, ErrorBox } from "@/components/ui";

interface Draft {
  id: number | null;
  title: string;
  description: string;
  minutes: number;
  category: string;
  tokens: number | null; // 새로 추가한 활동은 비워 두면 서버가 시세로 채워요
  source: PlanItem | null;
}

function toDraft(it: PlanItem): Draft {
  return {
    id: it.id,
    title: it.title,
    description: it.description ?? "",
    minutes: it.minutes,
    category: it.category,
    tokens: it.suggested_tokens,
    source: it,
  };
}

function basisLabel(it: PlanItem): string {
  if (it.price_basis === "market") return `비슷한 재능 ${it.similar_count}개 시세 기준`;
  if (it.price_basis === "user") return "직접 정한 금액";
  return "AI 추정 (비슷한 재능이 아직 적어요)";
}

function PlanEditor() {
  const { id } = useParams<{ id: string }>();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Plan>(`/plans/${id}`)
      .then((p) => {
        setPlan(p);
        setDrafts(p.items.map(toDraft));
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "불러오지 못했어요"));
    api<string[]>("/listings/categories").then(setCategories).catch(() => setCategories([]));
  }, [id]);

  if (!plan) return error ? <ErrorBox message={error} /> : <p className="py-10 text-center text-muted">불러오는 중…</p>;

  const update = (i: number, patch: Partial<Draft>) => setDrafts((ds) => ds.map((d, j) => (j === i ? { ...d, ...patch } : d)));
  const move = (i: number, dir: -1 | 1) =>
    setDrafts((ds) => {
      const next = [...ds];
      const j = i + dir;
      if (j < 0 || j >= next.length) return ds;
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });

  async function save() {
    if (drafts.some((d) => d.title.trim().length < 2)) return setError("활동 이름을 2자 이상 적어 주세요");
    if (drafts.length === 0) return setError("활동이 하나 이상 있어야 해요");
    setSaving(true);
    setError(null);
    try {
      const p = await api<Plan>(`/plans/${id}/items`, {
        method: "PUT",
        json: {
          items: drafts.map((d) => ({
            id: d.id,
            title: d.title.trim(),
            description: d.description.trim() || null,
            minutes: d.minutes,
            category: d.category,
            suggested_tokens: d.tokens,
          })),
        },
      });
      setPlan(p);
      setDrafts(p.items.map(toDraft));
      setEditing(false);
    } catch (e) {
      setError(e instanceof ApiError && e.code !== "VALIDATION_ERROR" ? e.message : "시간(5~120분), 토큰(1~500)을 확인해 주세요");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <Link href="/plans" className="text-sm text-muted">
        ← {plan.kind === "path" ? "목표 경로" : "부탁 쪼개기"}
      </Link>
      <Card className="space-y-2">
        <div className="flex items-center justify-between">
          <AiBadge />
          <TokenAmount amount={plan.total_tokens} />
        </div>
        <h1 className="text-xl font-bold">{plan.goal}</h1>
        {plan.summary && <p className="text-sm text-muted">{plan.summary}</p>}
      </Card>

      {editing ? (
        <div className="space-y-3">
          {drafts.map((d, i) => (
            <Card key={d.id ?? `new-${i}`} className="space-y-2">
              <div className="flex items-center justify-between text-sm text-muted">
                <span>{i + 1}단계</span>
                <div className="flex gap-3">
                  <button onClick={() => move(i, -1)} aria-label="위로">
                    ▲
                  </button>
                  <button onClick={() => move(i, 1)} aria-label="아래로">
                    ▼
                  </button>
                  <button onClick={() => setDrafts((ds) => ds.filter((_, j) => j !== i))} className="text-danger">
                    삭제
                  </button>
                </div>
              </div>
              <input
                value={d.title}
                onChange={(e) => update(i, { title: e.target.value })}
                maxLength={60}
                placeholder="활동 이름"
                className="w-full rounded-lg border border-border px-3 py-2 font-semibold"
              />
              <input
                value={d.description}
                onChange={(e) => update(i, { description: e.target.value })}
                maxLength={200}
                placeholder="무엇을 하는지 (선택)"
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
              <div className="grid grid-cols-3 gap-2 text-sm">
                <label className="space-y-1">
                  <span className="text-muted">시간(분)</span>
                  <input
                    type="number"
                    min={5}
                    max={120}
                    value={d.minutes}
                    onChange={(e) => update(i, { minutes: Number(e.target.value) })}
                    className="w-full rounded-lg border border-border px-2 py-2"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-muted">토큰</span>
                  <input
                    type="number"
                    min={1}
                    max={500}
                    value={d.tokens ?? ""}
                    placeholder="자동"
                    onChange={(e) => update(i, { tokens: e.target.value === "" ? null : Number(e.target.value) })}
                    className="w-full rounded-lg border border-border px-2 py-2"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-muted">카테고리</span>
                  <select
                    value={d.category}
                    onChange={(e) => update(i, { category: e.target.value })}
                    className="w-full rounded-lg border border-border px-1 py-2"
                  >
                    {categories.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
              </div>
            </Card>
          ))}
          <Button
            variant="ghost"
            onClick={() =>
              setDrafts((ds) => [
                ...ds,
                {
                  id: null,
                  title: "",
                  description: "",
                  minutes: 30,
                  // 바로 앞 활동과 같은 카테고리로 시작해요 (대부분 같은 분야라서)
                  category: ds[ds.length - 1]?.category ?? categories[0] ?? "생활·기타",
                  tokens: null,
                  source: null,
                },
              ])
            }
          >
            + 활동 추가 (토큰을 비우면 시세로 채워요)
          </Button>
          {error && <ErrorBox message={error} />}
          <div className="flex gap-2">
            <Button
              variant="ghost"
              disabled={saving}
              onClick={() => {
                setDrafts(plan.items.map(toDraft));
                setEditing(false);
                setError(null);
              }}
            >
              취소
            </Button>
            <Button disabled={saving} onClick={save}>
              {saving ? "저장하는 중…" : "저장"}
            </Button>
          </div>
        </div>
      ) : (
        <>
          <ol className="space-y-3">
            {plan.items.map((it, i) => (
              <li key={it.id} className="space-y-2 rounded-2xl border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs text-muted">
                      {plan.kind === "path" && i > 0 ? "→ " : ""}
                      {i + 1}단계 · {it.category} · 약 {it.minutes}분 {it.edited && "· ✏️ 수정함"}
                    </p>
                    <p className="font-semibold">{it.title}</p>
                    {it.description && <p className="text-sm text-muted">{it.description}</p>}
                  </div>
                  <TokenAmount amount={it.suggested_tokens} className="shrink-0" />
                </div>
                {it.why && <p className="rounded-lg bg-ai-soft px-3 py-2 text-sm text-ai">🧭 왜 필요해요? {it.why}</p>}
                <p className="text-xs text-muted">💡 {basisLabel(it)}</p>
                <div className="flex flex-wrap gap-2 text-sm">
                  {it.linked_listing ? (
                    <Link href={`/market/${it.linked_listing.id}`} className="rounded-full bg-brand px-3 py-1.5 font-semibold text-white">
                      {it.linked_listing.provider_nickname}님에게 요청 ({it.linked_listing.price_tokens}토큰)
                    </Link>
                  ) : null}
                  <Link
                    href={`/match?q=${encodeURIComponent(`${it.title}: ${it.description ?? ""}`.slice(0, 300))}`}
                    className="rounded-full border border-ai/40 px-3 py-1.5 font-medium text-ai"
                  >
                    🔎 맞는 사람 찾기
                  </Link>
                </div>
              </li>
            ))}
          </ol>
          <Button variant="ghost" onClick={() => setEditing(true)}>
            활동 수정·삭제·추가
          </Button>
        </>
      )}
    </div>
  );
}

export default function PlanPage() {
  return (
    <RequireLogin>
      <Suspense fallback={<p className="py-10 text-center text-muted">불러오는 중…</p>}>
        <PlanEditor />
      </Suspense>
    </RequireLogin>
  );
}
