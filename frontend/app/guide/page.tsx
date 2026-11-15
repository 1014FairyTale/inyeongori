"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type ReactNode } from "react";
import { api, type Me } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { safeNext } from "@/lib/nav";
import { Button } from "@/components/ui";

interface Slide {
  emoji: string;
  title: string;
  body: ReactNode;
  demo: ReactNode; // 실제 화면을 닮은 작은 예시
}

const Chip = ({ children, className = "" }: { children: ReactNode; className?: string }) => (
  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${className}`}>{children}</span>
);

const SLIDES: Slide[] = [
  {
    emoji: "🤝",
    title: "인연고리에 오신 걸 환영해요!",
    body: (
      <>
        인연고리는 대학생끼리 <b>재능을 주고받는</b> 곳이에요.
        <br />
        현금 대신 <b>토큰</b>으로 거래해요. 가입 선물로 <b>100토큰</b>을 드렸어요.
      </>
    ),
    demo: (
      <div className="flex items-center justify-center gap-3">
        <Chip className="bg-brand-soft text-base text-brand">🪙 100</Chip>
        <span className="text-sm text-muted">→ 도움 받기에 쓰고, 도움 주기로 벌어요</span>
      </div>
    ),
  },
  {
    emoji: "✨",
    title: "AI가 숨은 재능을 찾아 줘요",
    body: (
      <>
        동아리 총무, 과외, 행사 준비처럼 <b>평소 경험</b>을 편하게 적으면 AI가 재능 후보를 <b>근거와 함께</b> 찾아 줘요.
        <br />
        맞는 것만 <b>맞아요</b>로 확정하고, 마켓에 올리면 토큰을 벌 수 있어요.
      </>
    ),
    demo: (
      <div className="space-y-2 rounded-xl border border-border bg-card p-3 text-left text-xs">
        <Chip className="bg-ai-soft text-ai">✨ AI 제안</Chip>
        <p className="text-sm font-bold">엑셀 회비 정산</p>
        <p className="text-muted">총무 업무에는 보통 회비 정산이 포함돼요</p>
        <div className="flex gap-1.5">
          <Chip className="bg-brand text-white">맞아요</Chip>
          <Chip className="border border-border">아니에요</Chip>
          <Chip className="border border-border">수정</Chip>
        </div>
      </div>
    ),
  },
  {
    emoji: "🔎",
    title: "도움이 필요할 땐 이렇게 찾아요",
    body: (
      <>
        <b>🛍️ 마켓</b>에서 둘러보거나, <b>🔎 찾기</b>에 필요한 도움을 적으면 AI가 맞는 학생을 추천해요.
        <br />
        뭘 부탁할지 막막하면 <b>✂️ 부탁 쪼개기</b>로 큰 목표를 작은 부탁으로 나눠 보세요.
      </>
    ),
    demo: (
      <div className="space-y-1.5 rounded-xl border border-border bg-card p-3 text-left text-xs">
        <p className="text-muted">&ldquo;다음 주 발표 PPT 구성을 봐 줄 사람&rdquo;</p>
        <div className="flex items-center justify-between rounded-lg bg-background px-2.5 py-2">
          <span>
            <b>발표장인서연</b> · 발표 리허설 피드백
          </span>
          <Chip className="bg-ai-soft text-ai">87% 일치</Chip>
        </div>
      </div>
    ),
  },
  {
    emoji: "📝",
    title: "요청할 땐 조건부터 맞춰요",
    body: (
      <>
        &ldquo;PPT 봐주세요&rdquo;처럼 적으면 AI가 <b>분량·범위·수정 횟수·시간</b>으로 정리해 줘요.
        <br />
        두 사람이 합의서에 동의하면 토큰이 <b>안전하게 보류</b>돼요. 아직 상대에게 넘어가지 않아요.
      </>
    ),
    demo: (
      <div className="space-y-1.5 rounded-xl border border-border bg-card p-3 text-left text-xs">
        <p className="text-muted">AI가 정리한 조건</p>
        <p className="text-sm font-semibold">10장, 구성 피드백, 수정 1회, 30분</p>
        <p>
          ✅ 나 &nbsp; ✅ 상대 → <Chip className="bg-brand-soft text-brand">🪙 30 보류</Chip>
        </p>
      </div>
    ),
  },
  {
    emoji: "💬",
    title: "수락되면 채팅으로 진행해요",
    body: (
      <>
        요청이 수락되면 <b>채팅</b>으로 일정, 장소, 온라인 도구 같은 진행 방식을 정해요.
        <br />
        도움이 끝나면 두 사람 모두 <b>완료 확인</b>을 눌러요. 그때 보류된 토큰이 지급돼요.
      </>
    ),
    demo: (
      <div className="space-y-1.5 rounded-xl border border-border bg-background p-3 text-left text-xs">
        <p className="ml-auto w-fit rounded-2xl rounded-br-sm bg-brand px-3 py-1.5 text-white">토요일 2시에 줌 괜찮을까요?</p>
        <p className="w-fit rounded-2xl rounded-bl-sm border border-border bg-card px-3 py-1.5">좋아요! 링크 보내 드릴게요</p>
      </div>
    ),
  },
  {
    emoji: "✍️",
    title: "끝나면 7일 안에 후기를 남겨요",
    body: (
      <>
        <b>성의 있는 후기</b>를 7일 안에 쓰면 거래 토큰의 <b>10%를 돌려받아요</b>. 정성껏 도운 사람은 AI 판단으로 <b>보너스</b>를 받아요.
        <br />
        <span className="text-danger">7일이 지나도록 후기를 안 쓰면, 쓸 때까지 이용이 잠시 막혀요.</span>
      </>
    ),
    demo: (
      <div className="flex flex-wrap items-center justify-center gap-2">
        <span className="text-xl text-amber-400">★★★★★</span>
        <Chip className="bg-green-50 text-green-700">📝 10% 환급</Chip>
        <Chip className="bg-brand-soft text-brand">🎁 제공자 보너스</Chip>
      </div>
    ),
  },
];

function Guide() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"), "/onboarding");
  const { me, refresh } = useAuth();
  const [i, setI] = useState(0);
  const [leaving, setLeaving] = useState(false);
  const slide = SLIDES[i];
  const last = i === SLIDES.length - 1;

  async function finish(to: string) {
    setLeaving(true);
    if (me && !me.getting_started.tutorial_seen) {
      try {
        await api<Me>("/auth/me/tutorial", { method: "POST" });
        await refresh();
      } catch {
        // 기록에 실패해도 가이드는 넘어가요
      }
    }
    router.push(to);
  }

  return (
    <div className="flex min-h-[70vh] flex-col">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted">
          이용 가이드 {i + 1} / {SLIDES.length}
        </span>
        {!last && (
          <button onClick={() => finish(next)} disabled={leaving} className="text-muted underline-offset-2 hover:underline">
            건너뛰기
          </button>
        )}
      </div>

      <section key={i} className="flex flex-1 flex-col items-center justify-center gap-5 py-6 text-center" aria-live="polite">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-soft text-4xl" aria-hidden>
          {slide.emoji}
        </div>
        <h1 className="text-2xl font-extrabold leading-snug">{slide.title}</h1>
        <p className="leading-relaxed text-muted">{slide.body}</p>
        <div className="w-full max-w-sm">{slide.demo}</div>
      </section>

      <div className="flex justify-center gap-1.5 pb-4" role="tablist" aria-label="가이드 단계">
        {SLIDES.map((s, j) => (
          <button
            key={s.title}
            role="tab"
            aria-selected={j === i}
            aria-label={`${j + 1}번째: ${s.title}`}
            onClick={() => setI(j)}
            className={`h-2 rounded-full transition-all ${j === i ? "w-6 bg-brand" : "w-2 bg-border"}`}
          />
        ))}
      </div>

      <div className="flex gap-2">
        {i > 0 && (
          <Button variant="ghost" onClick={() => setI(i - 1)} className="w-1/3">
            이전
          </Button>
        )}
        {last ? (
          <Button disabled={leaving} onClick={() => finish(next)}>
            {next === "/onboarding" ? "✨ 내 재능 찾기" : "시작하기"}
          </Button>
        ) : (
          <Button onClick={() => setI(i + 1)}>다음</Button>
        )}
      </div>
    </div>
  );
}

export default function GuidePage() {
  return (
    <Suspense fallback={<p className="py-10 text-center text-muted">불러오는 중…</p>}>
      <Guide />
    </Suspense>
  );
}
