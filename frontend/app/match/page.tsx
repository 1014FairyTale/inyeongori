"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError, type MatchCandidate, type MatchResult } from "@/lib/api";
import { AiBadge } from "@/components/AiBadge";
import { AiLoading } from "@/components/AiLoading";
import { RequireLogin } from "@/components/RequireLogin";
import { TokenAmount } from "@/components/TokenAmount";
import { Button, Card, ErrorBox, TextArea } from "@/components/ui";
import { PageLoading } from "@/components/Logo";

const EXAMPLES = ["다음 주 발표 PPT 구성을 봐 줄 사람", "동아리 회비 정산을 엑셀로 하고 싶어요", "노트북이 느려졌는데 봐 줄 수 있는 분"];
const LOADING = ["요청을 이해하고 있어요…", "비슷한 재능을 가진 사람을 찾고 있어요…", "추천 이유를 정리하고 있어요…"];

function CandidateCard({ c, rank }: { c: MatchCandidate; rank: number }) {
  return (
    <article className="space-y-3 border-b border-line py-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-muted">{String(rank).padStart(2, "0")}</p>
          <Link href={`/users/${c.user.id}`} className="text-xl font-black hover:text-brand">
            {c.user.nickname}
          </Link>
          <p className="text-xs text-muted">
            {[c.user.school, c.user.major].filter(Boolean).join(" · ")}
            {c.completed_count > 0 && ` · 완료 ${c.completed_count}회`}
            {c.rating_avg != null && c.rating_count > 0 && ` · ${c.rating_avg.toFixed(1)}`}
          </p>
        </div>
        <span className="shrink-0 text-sm font-bold text-brand">
          {Math.round(c.similarity * 100)}% 일치
        </span>
      </div>

      <div className="space-y-1 text-sm">
        <div className="flex items-center gap-2">
          {c.reason_source === "ai" ? <AiBadge label="AI 추천 이유" /> : <span className="text-xs font-medium text-muted">추천 이유</span>}
        </div>
        <p>{c.reason}</p>
      </div>

      {c.matched_talent && <p className="text-sm text-muted">맞는 재능: {c.matched_talent}</p>}

      <div className="flex flex-wrap items-center gap-4 text-sm">
        {c.listing ? (
          <Link href={`/market/${c.listing.id}`} className="inline-flex items-center gap-2 bg-brand px-3 py-2 font-bold text-white hover:bg-foreground">
            {c.listing.title} 요청하기 <TokenAmount amount={c.listing.price_tokens} className="text-white" />
          </Link>
        ) : (
          <span className="text-muted">아직 올린 재능 상품이 없어요</span>
        )}
        <Link href={`/users/${c.user.id}`} className="text-muted underline underline-offset-4 hover:text-foreground">
          프로필 보기
        </Link>
      </div>
    </article>
  );
}

function Match() {
  const initial = useSearchParams().get("q") ?? "";
  const [query, setQuery] = useState(initial);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ranInitial = useRef(false);

  const run = useCallback(async (q: string) => {
    if (q.trim().length < 2) return setError("어떤 도움이 필요한지 적어 주세요");
    setError(null);
    setRunning(true);
    try {
      setResult(await api<MatchResult>("/match", { method: "POST", json: { query: q.trim(), limit: 5 } }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "추천을 받지 못했어요");
    } finally {
      setRunning(false);
    }
  }, []);

  // 부탁 쪼개기·목표 경로에서 '맞는 사람 찾기'로 넘어오면 바로 찾아요
  useEffect(() => {
    if (initial && !ranInitial.current) {
      ranInitial.current = true;
      void run(initial);
    }
  }, [initial, run]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void run(query);
  }

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-3xl font-black">도와줄 사람 찾기</h1>
        <p className="text-muted">필요한 도움을 편하게 적으면, AI가 재능이 맞는 학생을 추천해요.</p>
      </div>
      <Card>
        <form onSubmit={onSubmit} className="space-y-3" noValidate>
          <TextArea
            label="이런 도움이 필요해요"
            placeholder="예: 다음 주 발표 PPT 구성을 봐 줄 사람"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={300}
            className="min-h-16"
          />
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {EXAMPLES.map((ex) => (
              <button key={ex} type="button" onClick={() => setQuery(ex)} className="text-xs text-muted underline underline-offset-4 hover:text-foreground">
                {ex}
              </button>
            ))}
          </div>
          <Button type="submit" disabled={running}>
            {error ? "다시 시도" : "AI로 추천받기"}
          </Button>
        </form>
      </Card>

      {error && <ErrorBox message={error} />}
      {running && <AiLoading messages={LOADING} />}

      {!running && result && (
        <section className="space-y-3">
          {result.candidates.length === 0 ? (
            <Card className="space-y-2 text-muted">
              <p>아직 이 요청에 맞는 재능을 가진 학생이 없어요.</p>
              <p className="text-sm">다르게 표현해 보거나, 마켓을 둘러보세요.</p>
              <Link href="/market" className="font-semibold text-brand">
                마켓 둘러보기
              </Link>
            </Card>
          ) : (
            <>
              <p className="text-sm text-muted">재능 일치도·후기 평점·활동 이력을 함께 반영한 순서예요.</p>
              {result.candidates.map((c, i) => (
                <CandidateCard key={c.user.id} c={c} rank={i + 1} />
              ))}
            </>
          )}
        </section>
      )}
    </div>
  );
}

export default function MatchPage() {
  return (
    <RequireLogin>
      <Suspense fallback={<PageLoading />}>
        <Match />
      </Suspense>
    </RequireLogin>
  );
}
