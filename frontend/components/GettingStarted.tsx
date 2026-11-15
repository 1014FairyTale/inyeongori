"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { StepKey } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STEPS: Record<StepKey, { title: string; desc: string; href: string; cta: string }> = {
  discover: { title: "AI로 내 재능 찾기", desc: "경험을 적으면 AI가 재능 후보를 찾아 줘요", href: "/onboarding", cta: "찾기" },
  list: { title: "내 재능을 마켓에 올리기", desc: "가격은 직접 정해요. 요청을 받으면 토큰을 벌어요", href: "/market/new", cta: "올리기" },
  request: { title: "필요한 도움 요청하기", desc: "🔎 찾기에서 맞는 학생을 추천받아요", href: "/match", cta: "찾아보기" },
  chat: { title: "수락된 거래에서 대화하기", desc: "채팅으로 일정과 진행 방식을 정해요", href: "/exchanges", cta: "거래 보기" },
  review: { title: "완료 후 후기 남기기", desc: "7일 안에 성의 있게 쓰면 10%를 돌려받아요", href: "/exchanges", cta: "거래 보기" },
};

const hideKey = (userId: number) => `inyeongori.getting-started.hidden.${userId}`;

/** 홈의 '첫 걸음' 체크리스트. 실제로 해 본 단계는 서버 데이터를 보고 자동으로 체크돼요. */
export function GettingStarted() {
  const { me } = useAuth();
  const [hidden, setHidden] = useState(true);

  useEffect(() => {
    if (!me) return;
    let value = false;
    try {
      value = window.localStorage.getItem(hideKey(me.user.id)) === "1";
    } catch {
      // 저장소를 못 쓰면 항상 보여 줘요
    }
    const t = setTimeout(() => setHidden(value), 0);
    return () => clearTimeout(t);
  }, [me]);

  if (!me || hidden) return null;
  const steps = me.getting_started.steps;
  const done = steps.filter((s) => s.done).length;
  if (steps.length === 0 || done === steps.length) return null;
  const nextKey = steps.find((s) => !s.done)?.key;

  function hide() {
    try {
      window.localStorage.setItem(hideKey(me!.user.id), "1");
    } catch {
      // 무시
    }
    setHidden(true);
  }

  return (
    <section className="space-y-3 rounded-2xl border border-brand/30 bg-card p-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-bold">🚀 첫 걸음</h2>
          <p className="text-xs text-muted">
            {done}/{steps.length} 완료 ·{" "}
            <Link href="/guide?next=/" className="underline underline-offset-2">
              이용 가이드 다시 보기
            </Link>
          </p>
        </div>
        <button onClick={hide} className="text-xs text-muted" aria-label="첫 걸음 체크리스트 숨기기">
          숨기기
        </button>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-border">
        <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${(done / steps.length) * 100}%` }} />
      </div>
      <ol className="space-y-1.5">
        {steps.map((s, idx) => {
          const info = STEPS[s.key];
          const isNext = s.key === nextKey;
          return (
            <li
              key={s.key}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 ${isNext ? "bg-brand-soft" : ""}`}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  s.done ? "bg-green-600 text-white" : isNext ? "bg-brand text-white" : "bg-border text-muted"
                }`}
                aria-hidden
              >
                {s.done ? "✓" : idx + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className={`block text-sm font-semibold ${s.done ? "text-muted line-through" : ""}`}>{info.title}</span>
                {!s.done && <span className="block text-xs text-muted">{info.desc}</span>}
              </span>
              {!s.done && (
                <Link
                  href={info.href}
                  className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                    isNext ? "bg-brand text-white" : "border border-border text-muted"
                  }`}
                >
                  {info.cta}
                </Link>
              )}
              <span className="sr-only">{s.done ? "완료" : "아직 안 함"}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
