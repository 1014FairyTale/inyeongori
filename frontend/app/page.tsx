"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Eyebrow } from "@/components/ui";
import { LogoMark } from "@/components/Logo";
import { GettingStarted } from "@/components/GettingStarted";

const HOW = [
  { title: "경험을 편하게 적어요", body: "동아리 총무, 과외, 행사 준비처럼 사소해 보이는 경험도 괜찮아요." },
  { title: "AI가 숨은 재능을 찾아 줘요", body: "근거와 확인 질문을 함께 보여 드려요. 맞는 것만 골라 확정해요." },
  { title: "토큰으로 재능을 나눠요", body: "현금 없이, 가입하면 받는 100토큰으로 바로 도움을 주고받아요." },
];

const MORE = [
  { href: "/match", title: "도와줄 사람 찾기", body: "필요한 도움을 적으면 AI가 재능이 맞는 학생을 추천해요" },
  { href: "/plans", title: "큰 목표를 작은 부탁으로", body: "공모전 준비처럼 큰 목표를 20~30분짜리 도움으로 나눠요" },
  { href: "/market", title: "재능 마켓 둘러보기", body: "다른 학생들이 올린 재능을 카테고리별로 살펴봐요" },
];

export default function Home() {
  const { me } = useAuth();
  const cta = me ? "/onboarding" : "/signup?next=/onboarding";
  const gated = (href: string) => (me || href === "/market" ? href : `/signup?next=${href}`);

  return (
    <div className="space-y-14">
      <GettingStarted />

      <section className="space-y-6">
        <Eyebrow>재능 교류 플랫폼</Eyebrow>
        <h1 className="flex items-center gap-4">
          <LogoMark size={56} />
          <span className="text-6xl font-black tracking-tight text-brand sm:text-7xl">인연고리</span>
        </h1>
        <p className="text-xl font-bold leading-snug">
          AI가 찾아 주는 나의 숨은 재능,
          <br />
          토큰으로 친구들과 나눠요
        </p>
        <p className="border-l-0 text-muted">
          &ldquo;저는 재능이 없어요&rdquo;라고 생각했다면, 지금까지 해 온 일을 적어 보세요. 거기에 다른 학생이 필요로 하는 재능이 있어요.
        </p>
        <div className="space-y-3 pt-2">
          <Link href={cta} className="block bg-brand px-6 py-4 text-center text-lg font-bold text-white hover:bg-foreground">
            AI가 내 재능 찾아 주기
          </Link>
          {!me && (
            <p className="text-sm text-muted">
              이미 계정이 있나요?{" "}
              <Link href="/login" className="font-semibold text-foreground underline underline-offset-4">
                로그인
              </Link>
            </p>
          )}
        </div>
      </section>

      <section>
        <h2 className="border-b border-foreground pb-2 text-sm font-bold">이렇게 이용해요</h2>
        <ol>
          {HOW.map((s, i) => (
            <li key={s.title} className="grid grid-cols-[3rem_1fr] gap-x-3 border-b border-line py-5">
              <span className="text-2xl font-black text-brand tabular-nums">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <p className="text-lg font-bold">{s.title}</p>
                <p className="text-sm text-muted">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2 className="border-b border-foreground pb-2 text-sm font-bold">더 해 볼 수 있어요</h2>
        <ul>
          {MORE.map((m) => (
            <li key={m.href}>
              <Link href={gated(m.href)} className="group flex items-baseline justify-between gap-4 border-b border-line py-4">
                <span>
                  <span className="block font-bold group-hover:underline group-hover:underline-offset-4">{m.title}</span>
                  <span className="block text-sm text-muted">{m.body}</span>
                </span>
                <span className="shrink-0 text-sm font-semibold text-brand">바로 가기</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
