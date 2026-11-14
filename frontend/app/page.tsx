"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui";

const STEPS = [
  { emoji: "💬", title: "경험을 편하게 적어요", body: "동아리 총무, 과외, 행사 준비… 사소해 보여도 괜찮아요." },
  { emoji: "✨", title: "AI가 숨은 재능을 찾아 줘요", body: "근거와 함께 보여 드리고, 맞는 것만 골라 확정해요." },
  { emoji: "🪙", title: "토큰으로 재능을 나눠요", body: "현금 없이, 가입하면 받는 100토큰으로 바로 시작해요." },
];

export default function Home() {
  const { me } = useAuth();
  const cta = me ? "/onboarding" : "/signup?next=/onboarding";

  return (
    <div className="space-y-10">
      <section className="space-y-5 pt-6 text-center">
        <p className="text-sm font-semibold text-brand">대학생 재능 교류 플랫폼</p>
        <h1 className="text-3xl font-extrabold leading-snug sm:text-4xl">
          &ldquo;저는 재능이 없어요&rdquo;
          <br />
          정말 그럴까요?
        </h1>
        <p className="text-muted">
          AI가 내 경험 속 숨은 재능을 찾아 드려요.
          <br />
          찾은 재능은 토큰으로 친구들과 나눌 수 있어요.
        </p>
        <Link
          href={cta}
          className="mx-auto flex w-full max-w-sm items-center justify-center gap-2 rounded-2xl bg-brand px-6 py-4 text-lg font-bold text-white shadow-lg shadow-orange-200 transition hover:brightness-95"
        >
          ✨ AI가 내 재능 찾아 주기
        </Link>
        {!me && (
          <p className="text-sm text-muted">
            이미 계정이 있나요?{" "}
            <Link href="/login" className="font-medium text-brand underline-offset-2 hover:underline">
              로그인
            </Link>
          </p>
        )}
      </section>

      <Link
        href={me ? "/plans" : "/signup?next=/plans"}
        className="flex items-center justify-between rounded-2xl border border-ai/30 bg-ai-soft px-5 py-4 text-ai"
      >
        <span>
          <b>✂️ 큰 목표, 작은 부탁으로 쪼개기</b>
          <br />
          <span className="text-sm">&ldquo;공모전 나가고 싶어요&rdquo; → 필요한 도움을 순서대로</span>
        </span>
        <span aria-hidden>→</span>
      </Link>
      <Link
        href={me ? "/match" : "/signup?next=/match"}
        className="flex items-center justify-between rounded-2xl border border-border bg-card px-5 py-4"
      >
        <span>
          <b>🔎 도와줄 사람 찾기</b>
          <br />
          <span className="text-sm text-muted">필요한 도움을 적으면 AI가 맞는 학생을 추천해요</span>
        </span>
        <span aria-hidden>→</span>
      </Link>

      <section className="space-y-3">
        {STEPS.map((s, i) => (
          <Card key={s.title} className="flex gap-4">
            <div className="text-2xl" aria-hidden>
              {s.emoji}
            </div>
            <div>
              <p className="font-semibold">
                {i + 1}. {s.title}
              </p>
              <p className="text-sm text-muted">{s.body}</p>
            </div>
          </Card>
        ))}
      </section>
    </div>
  );
}
