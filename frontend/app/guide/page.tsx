"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type ReactNode } from "react";
import { api, type Me } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { safeNext } from "@/lib/nav";
import { Button } from "@/components/ui";
import { PageLoading } from "@/components/Logo";

interface Slide {
  title: string;
  body: ReactNode;
  demo: ReactNode; // 실제 화면을 닮은 작은 예시 (가는 선으로만 구획)
}

/** 예시 영역: 박스 대신 위아래 가는 선 */
const Specimen = ({ children }: { children: ReactNode }) => (
  <div className="space-y-1.5 border-y border-line py-3 text-left text-sm">{children}</div>
);
const Label = ({ children }: { children: ReactNode }) => <p className="text-xs font-bold text-brand">{children}</p>;

const SLIDES: Slide[] = [
  {
    title: "인연고리에 오신 걸 환영해요",
    body: (
      <>
        인연고리는 누구나 서로 <b>재능을 주고받는</b> 곳이에요. 현금 대신 <b>토큰</b>으로 거래하고, 가입 선물로{" "}
        <b>100토큰</b>을 드렸어요.
      </>
    ),
    demo: (
      <Specimen>
        <p className="text-3xl font-black tabular-nums">
          100 <span className="text-base font-medium text-muted">토큰</span>
        </p>
        <p className="text-muted">도움을 받을 때 쓰고, 도움을 줄 때 벌어요</p>
      </Specimen>
    ),
  },
  {
    title: "AI가 숨은 재능을 찾아 줘요",
    body: (
      <>
        모임 총무, 과외, 행사 준비처럼 <b>평소 경험</b>을 적으면 AI가 재능 후보를 <b>근거와 함께</b> 찾아 줘요. 맞는 것만{" "}
        <b>맞아요</b>로 확정하고, 마켓에 올리면 토큰을 벌 수 있어요.
      </>
    ),
    demo: (
      <Specimen>
        <Label>AI 제안</Label>
        <p className="font-bold">엑셀 회비 정산</p>
        <p className="text-muted">총무 업무에는 보통 회비 정산이 포함돼요</p>
        <p className="flex gap-4 pt-1 text-xs font-bold">
          <span className="text-brand underline underline-offset-4">맞아요</span>
          <span className="text-muted">아니에요</span>
          <span className="text-muted">수정</span>
        </p>
      </Specimen>
    ),
  },
  {
    title: "도움이 필요할 땐 이렇게 찾아요",
    body: (
      <>
        <b>마켓</b>에서 둘러보거나, <b>찾기</b>에 필요한 도움을 적으면 AI가 맞는 사람을 추천해요. 뭘 부탁할지 막막하면{" "}
        <b>부탁 쪼개기</b>로 큰 목표를 작은 부탁으로 나눠 보세요.
      </>
    ),
    demo: (
      <Specimen>
        <p className="text-muted">&ldquo;다음 주 발표 PPT 구성을 봐 줄 사람&rdquo;</p>
        <p className="flex items-baseline justify-between">
          <span>
            <b>발표장인서연</b> · 발표 리허설 피드백
          </span>
          <span className="text-xs font-bold text-brand">87% 일치</span>
        </p>
      </Specimen>
    ),
  },
  {
    title: "요청할 땐 조건부터 맞춰요",
    body: (
      <>
        &ldquo;PPT 봐주세요&rdquo;처럼 적으면 AI가 <b>분량·범위·수정 횟수·시간</b>으로 정리해 줘요. 두 사람이 합의서에 동의하면 토큰이{" "}
        <b>안전하게 보류</b>돼요. 아직 상대에게 넘어가지 않아요.
      </>
    ),
    demo: (
      <Specimen>
        <Label>AI가 정리한 조건</Label>
        <p className="font-bold">10장, 구성 피드백, 수정 1회, 30분</p>
        <p className="text-muted">나 동의 · 상대 동의 → 30토큰 보류</p>
      </Specimen>
    ),
  },
  {
    title: "수락되면 채팅으로 진행해요",
    body: (
      <>
        요청이 수락되면 <b>채팅</b>으로 일정, 장소, 온라인 도구 같은 진행 방식을 정해요. 도움이 끝나면 두 사람 모두{" "}
        <b>완료 확인</b>을 눌러요. 그때 보류된 토큰이 지급돼요.
      </>
    ),
    demo: (
      <Specimen>
        <p className="ml-auto w-fit bg-foreground px-3 py-1.5 text-background">토요일 2시에 줌 괜찮을까요?</p>
        <p className="w-fit border border-line px-3 py-1.5">좋아요, 링크 보내 드릴게요</p>
      </Specimen>
    ),
  },
  {
    title: "끝나면 7일 안에 후기를 남겨요",
    body: (
      <>
        <b>성의 있는 후기</b>를 7일 안에 쓰면 거래 토큰의 <b>10%를 돌려받아요</b>. 정성껏 도운 사람은 AI 판단으로 <b>보너스</b>를 받아요.{" "}
        <span className="font-semibold text-danger">7일이 지나도록 후기를 안 쓰면, 쓸 때까지 이용이 잠시 막혀요.</span>
      </>
    ),
    demo: (
      <Specimen>
        <p className="text-lg tracking-widest text-brand" aria-label="별점 5점">
          ★★★★★
        </p>
        <p className="text-muted">후기 작성자 10% 환급 · 제공자 보너스</p>
      </Specimen>
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
      <div className="flex items-baseline justify-between border-b border-foreground pb-2 text-sm">
        <span className="font-bold">
          이용 가이드 <span className="font-normal text-muted tabular-nums">{i + 1} / {SLIDES.length}</span>
        </span>
        {!last && (
          <button onClick={() => finish(next)} disabled={leaving} className="text-muted underline underline-offset-4 hover:text-foreground">
            건너뛰기
          </button>
        )}
      </div>

      <section key={i} className="flex flex-1 flex-col justify-center gap-5 py-10" aria-live="polite">
        <p className="text-6xl font-black text-brand tabular-nums">{String(i + 1).padStart(2, "0")}</p>
        <h1 className="text-3xl font-black leading-tight">{slide.title}</h1>
        <p className="leading-relaxed text-muted">{slide.body}</p>
        <div className="max-w-sm">{slide.demo}</div>
      </section>

      {/* 진행 표시: 단계 수만큼 나눈 가는 선 (누르면 그 단계로) */}
      <div className="flex gap-1 pb-5" role="tablist" aria-label="가이드 단계">
        {SLIDES.map((s, j) => (
          <button
            key={s.title}
            role="tab"
            aria-selected={j === i}
            aria-label={`${j + 1}번째: ${s.title}`}
            onClick={() => setI(j)}
            className="flex-1 py-2"
          >
            <span className={`block h-0.5 ${j <= i ? "bg-foreground" : "bg-line"}`} />
          </button>
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
            {next === "/onboarding" ? "내 재능 찾기" : "시작하기"}
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
    <Suspense fallback={<PageLoading />}>
      <Guide />
    </Suspense>
  );
}
