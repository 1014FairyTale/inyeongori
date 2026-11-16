"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { StepKey } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STEPS: Record<StepKey, { title: string; desc: string; href: string; cta: string }> = {
  discover: { title: "AI로 내 재능 찾기", desc: "경험을 적으면 AI가 재능 후보를 찾아 줘요", href: "/onboarding", cta: "찾기" },
  list: { title: "내 재능을 마켓에 올리기", desc: "가격은 직접 정해요. 요청을 받으면 토큰을 벌어요", href: "/market/new", cta: "올리기" },
  request: { title: "필요한 도움 요청하기", desc: "찾기에서 맞는 사람을 추천받아요", href: "/match", cta: "찾아보기" },
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
    <section aria-labelledby="first-steps">
      <div className="flex items-baseline justify-between border-b border-foreground pb-2">
        <h2 id="first-steps" className="text-sm font-bold">
          첫 걸음 <span className="font-normal text-muted tabular-nums">{done}/{steps.length}</span>
        </h2>
        <span className="flex gap-3 text-xs text-muted">
          <Link href="/guide?next=/" className="underline underline-offset-4 hover:text-foreground">
            이용 가이드
          </Link>
          <button onClick={hide} className="hover:text-foreground" aria-label="첫 걸음 목록 숨기기">
            숨기기
          </button>
        </span>
      </div>
      {/* 진행도: 단계 수만큼 나눈 가는 선 */}
      <div className="flex gap-1 pt-2" aria-hidden>
        {steps.map((s) => (
          <span key={s.key} className={`h-0.5 flex-1 ${s.done ?"bg-foreground":"bg-line"}`} />
        ))}
      </div>
      <ol>
        {steps.map((s, idx) => {
          const info = STEPS[s.key];
          const isNext = s.key === nextKey;
          return (
            <li key={s.key} className="grid grid-cols-[2rem_1fr_auto] items-baseline gap-x-2 border-b border-line py-3">
              <span className={`text-sm font-black tabular-nums ${isNext ?"text-brand":"text-muted"}`}>
                {String(idx + 1).padStart(2, "0")}
              </span>
              <span className="min-w-0">
                <span className={`block font-semibold ${s.done ?"text-muted line-through":""}`}>{info.title}</span>
                {!s.done && <span className="block text-xs text-muted">{info.desc}</span>}
              </span>
              {s.done ? (
                <span className="text-xs font-semibold text-success">완료</span>
              ) : (
                <Link
                  href={info.href}
                  className={`text-sm font-bold underline-offset-4 hover:underline ${isNext ?"text-brand":"text-muted"}`}
                >
                  {info.cta}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
