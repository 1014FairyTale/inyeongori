"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Plan, type PlanSummary } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { AiLoading } from "@/components/AiLoading";
import { RequireLogin } from "@/components/RequireLogin";
import { Button, Card, ErrorBox, TextArea } from "@/components/ui";

type Kind = "breakdown" | "path";

const MODES: Record<Kind, { label: string; title: string; desc: string; examples: string[]; loading: string[]; cta: string }> = {
  breakdown: {
    label: "✂️ 부탁 쪼개기",
    title: "큰 목표를 작은 부탁으로",
    desc: "큰 목표를 20~30분짜리 작은 부탁으로 나눠 드려요. 하나씩 부탁하면 부담이 훨씬 적어요.",
    examples: ["앱 개발을 배우고 싶어요", "토익 스피킹 레벨 6 받고 싶어요", "동아리 홍보 포스터를 직접 만들고 싶어요"],
    loading: ["목표를 살펴보고 있어요…", "20~30분짜리 활동으로 나누고 있어요…", "마켓 시세로 적정 토큰을 계산하고 있어요…"],
    cta: "✨ AI로 쪼개기",
  },
  path: {
    label: "🧭 목표 경로",
    title: "목표까지 가는 교환 경로",
    desc: "목표를 이루려면 어떤 도움을 어떤 순서로 받으면 좋을지 설계하고, 단계마다 맞는 사람을 연결해 드려요.",
    examples: ["공모전에 나가고 싶어요", "첫 인턴 지원서를 내고 싶어요", "학교 축제 부스를 운영하고 싶어요"],
    loading: ["목표를 살펴보고 있어요…", "필요한 도움을 순서대로 설계하고 있어요…", "단계마다 맞는 재능을 찾고 있어요…"],
    cta: "✨ AI로 경로 설계하기",
  },
};

function Plans() {
  const router = useRouter();
  const [kind, setKind] = useState<Kind>("breakdown");
  const mode = MODES[kind];
  const [goal, setGoal] = useState("");
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<PlanSummary[]>("/plans").then(setPlans).catch(() => setPlans([]));
  }, []);

  async function run(e?: FormEvent) {
    e?.preventDefault();
    if (goal.trim().length < 2) return setError("이루고 싶은 목표를 적어 주세요");
    setError(null);
    setRunning(true);
    try {
      const plan = await api<Plan>("/plans", { method: "POST", json: { goal: goal.trim(), kind } });
      router.push(`/plans/${plan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI가 응답하지 않았어요");
      setRunning(false);
    }
  }

  if (running) return <AiLoading messages={mode.loading} />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-2 rounded-2xl bg-card p-1">
        {(Object.keys(MODES) as Kind[]).map((k) => (
          <button
            key={k}
            onClick={() => setKind(k)}
            className={`rounded-xl py-2.5 text-sm font-semibold ${kind === k ? "bg-brand text-white" : "text-muted"}`}
          >
            {MODES[k].label}
          </button>
        ))}
      </div>
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">{mode.title}</h1>
        <p className="text-muted">{mode.desc}</p>
      </div>
      <Card>
        <form onSubmit={run} className="space-y-3" noValidate>
          <TextArea
            label="이루고 싶은 목표"
            placeholder={`예: ${mode.examples[0]}`}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            maxLength={300}
            className="min-h-16"
          />
          <div className="flex flex-wrap gap-2">
            {mode.examples.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setGoal(ex)}
                className="rounded-full border border-border bg-background px-3 py-1 text-xs text-muted"
              >
                {ex}
              </button>
            ))}
          </div>
          {error && <ErrorBox message={error} />}
          <Button type="submit">{error ? "다시 시도" : mode.cta}</Button>
        </form>
      </Card>

      {plans.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-bold">지난 계획</h2>
          <ul className="space-y-2">
            {plans.map((p) => (
              <li key={p.id}>
                <Link href={`/plans/${p.id}`} className="block rounded-2xl border border-border bg-card p-4 hover:border-brand">
                  <p className="font-semibold">
                    {p.kind === "path" ? "🧭 " : "✂️ "}
                    {p.goal}
                  </p>
                  <p className="text-sm text-muted">
                    {p.kind === "path" ? "단계" : "활동"} {p.item_count}개 · 예상 {p.total_tokens}토큰 · {formatDate(p.created_at)}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export default function PlansPage() {
  return (
    <RequireLogin>
      <Plans />
    </RequireLogin>
  );
}
