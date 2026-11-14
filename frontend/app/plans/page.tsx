"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Plan, type PlanSummary } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { AiLoading } from "@/components/AiLoading";
import { RequireLogin } from "@/components/RequireLogin";
import { Button, Card, ErrorBox, TextArea } from "@/components/ui";

const EXAMPLES = ["앱 개발을 배우고 싶어요", "토익 스피킹 레벨 6 받고 싶어요", "동아리 홍보 포스터를 직접 만들고 싶어요"];

const LOADING = ["목표를 살펴보고 있어요…", "20~30분짜리 활동으로 나누고 있어요…", "마켓 시세로 적정 토큰을 계산하고 있어요…"];

function Plans() {
  const router = useRouter();
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
      const plan = await api<Plan>("/plans", { method: "POST", json: { goal: goal.trim() } });
      router.push(`/plans/${plan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI가 응답하지 않았어요");
      setRunning(false);
    }
  }

  if (running) return <AiLoading messages={LOADING} />;

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">부탁 쪼개기 ✂️</h1>
        <p className="text-muted">큰 목표를 20~30분짜리 작은 부탁으로 나눠 드려요. 하나씩 부탁하면 부담이 훨씬 적어요.</p>
      </div>
      <Card>
        <form onSubmit={run} className="space-y-3" noValidate>
          <TextArea
            label="이루고 싶은 목표"
            placeholder="예: 앱 개발을 배우고 싶어요"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            maxLength={300}
            className="min-h-16"
          />
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
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
          <Button type="submit">{error ? "다시 시도" : "✨ AI로 쪼개기"}</Button>
        </form>
      </Card>

      {plans.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-bold">지난 계획</h2>
          <ul className="space-y-2">
            {plans.map((p) => (
              <li key={p.id}>
                <Link href={`/plans/${p.id}`} className="block rounded-2xl border border-border bg-card p-4 hover:border-brand">
                  <p className="font-semibold">{p.goal}</p>
                  <p className="text-sm text-muted">
                    활동 {p.item_count}개 · 예상 {p.total_tokens}토큰 · {formatDate(p.created_at)}
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
