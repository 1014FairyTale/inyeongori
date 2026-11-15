"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Exchange, type ReviewAnalysis, type ReviewResult } from "@/lib/api";
import { daysLeft, dueLabel, formatDate } from "@/lib/format";
import { AiBadge } from "@/components/AiBadge";
import { AiLoading } from "@/components/AiLoading";
import { Button, Card, ErrorBox, TextArea } from "@/components/ui";

const LOADING = ["후기를 꼼꼼히 읽고 있어요…", "합의한 조건과 비교하고 있어요…", "기여도를 판단하고 있어요…"];
const MIN_CHARS = 30; // 후기 환급 조건 (백엔드 REVIEW_REWARD_MIN_CHARS와 같게)
const REWARD_RATE = 0.1; // 백엔드 REVIEW_REWARD_RATE와 같게

function Stars({ value, onChange }: { value: number; onChange?: (v: number) => void }) {
  return (
    <div className="flex gap-1" role={onChange ? "radiogroup" : undefined} aria-label="별점">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={!onChange}
          onClick={() => onChange?.(n)}
          aria-label={`${n}점`}
          aria-checked={onChange ? value === n : undefined}
          role={onChange ? "radio" : undefined}
          className={`text-3xl leading-none ${n <= value ? "text-amber-400" : "text-border"} disabled:cursor-default`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

function AnalysisCard({ a, isProvider, providerName }: { a: ReviewAnalysis; isProvider: boolean; providerName: string }) {
  const [showSteps, setShowSteps] = useState(false);
  return (
    <div className="space-y-3 rounded-2xl border border-ai/30 bg-ai-soft/50 p-4">
      <div className="flex items-center justify-between">
        <AiBadge label="AI 후기 분석" />
        <span className="text-sm font-bold text-ai">기여도 {a.contribution_score}점</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-card">
        <div className="h-full rounded-full bg-ai" style={{ width: `${a.contribution_score}%` }} />
      </div>
      <p className="text-sm">{a.summary}</p>
      <div className="space-y-1 rounded-xl bg-card px-3.5 py-3 text-sm">
        <p className="font-medium text-muted">AI 판단 근거</p>
        <ul className="list-disc space-y-1 pl-5">
          {a.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
        {a.flags.length > 0 && <p className="pt-1 text-xs text-danger">주의: {a.flags.join(" · ")}</p>}
      </div>

      {a.final_bonus > 0 ? (
        <p className="rounded-xl bg-brand-soft px-4 py-3 font-semibold text-brand">
          🎁 {isProvider ? `정성스러운 도움 덕분에 보너스 ${a.final_bonus}토큰을 받았어요!` : `${providerName}님에게 보너스 ${a.final_bonus}토큰이 지급됐어요`}
        </p>
      ) : (
        <p className="rounded-xl bg-card px-4 py-3 text-sm text-muted">이번 거래는 보너스 지급 조건에 해당하지 않았어요.</p>
      )}

      {!isProvider && (
        <div className={`space-y-1 rounded-xl px-4 py-3 text-sm ${a.reviewer_reward > 0 ? "bg-green-50" : "bg-card"}`}>
          <p className="font-semibold">
            📝 후기 성의 점수 {a.review_quality}점
            {a.reviewer_reward > 0 && <span className="text-green-700"> · {a.reviewer_reward}토큰을 돌려받았어요!</span>}
          </p>
          {a.review_quality_reason && <p className="text-muted">{a.review_quality_reason}</p>}
          {a.reviewer_reward === 0 && a.reviewer_reward_note && <p className="text-xs text-muted">{a.reviewer_reward_note}</p>}
        </div>
      )}

      {a.adjustments.length > 0 && (
        <div className="text-sm">
          <button onClick={() => setShowSteps((v) => !v)} className="text-muted underline">
            {showSteps ? "계산 과정 접기" : "보너스 계산 과정 보기"}
          </button>
          {showSteps && (
            <ol className="mt-2 space-y-1 rounded-xl bg-card px-3.5 py-3 text-xs text-muted">
              {a.adjustments.map((x, i) => (
                <li key={i}>
                  {i + 1}. {x.message}
                  {x.after != null && ` → ${x.after}토큰`}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

/** 완료된 거래의 후기: 요청자는 작성, 양쪽 모두 AI 분석 결과를 볼 수 있어요. */
export function ReviewSection({ exchange, onChanged }: { exchange: Exchange; onChanged: () => void }) {
  const [data, setData] = useState<ReviewResult | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [rating, setRating] = useState(0);
  const [good, setGood] = useState("");
  const [bad, setBad] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isProvider = exchange.my_role === "provider";

  useEffect(() => {
    api<ReviewResult | null>(`/exchanges/${exchange.id}/review`)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoaded(true));
  }, [exchange.id]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (rating === 0) return setError("별점을 골라 주세요");
    if (good.trim().length < 2) return setError("좋았던 점을 적어 주세요");
    setError(null);
    setBusy(true);
    try {
      setData(await api<ReviewResult>(`/exchanges/${exchange.id}/review`, { method: "POST", json: { rating, good_text: good, bad_text: bad || null } }));
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "후기를 저장하지 못했어요");
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    setBusy(true);
    setError(null);
    try {
      setData(await api<ReviewResult>(`/exchanges/${exchange.id}/review/analyze`, { method: "POST" }));
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "다시 시도해 주세요");
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) return null;
  if (busy && !data) return <AiLoading messages={LOADING} />;

  if (!data) {
    if (isProvider) return <Card className="text-sm text-muted">요청자의 후기를 기다리고 있어요. 좋은 후기를 받으면 AI가 판단해서 보너스 토큰을 줘요 🎁</Card>;
    const chars = good.trim().length + bad.trim().length;
    return (
      <Card className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-bold">후기 남기기</h2>
          <p className="text-sm text-muted">
            AI가 후기를 읽고 {exchange.provider.nickname}님의 기여도를 판단해요. 정성스러운 도움이었다면 보너스 토큰이 지급돼요.
          </p>
        </div>
        {exchange.review_due_at &&
          (daysLeft(exchange.review_due_at) >= 0 ? (
            <p className="rounded-xl bg-green-50 px-3.5 py-2.5 text-sm text-green-800">
              🎁 <b>{formatDate(exchange.review_due_at)}</b>까지({dueLabel(exchange.review_due_at)}) 성의 있게 쓰면{" "}
              <b>{Math.max(1, Math.round(exchange.price_tokens * REWARD_RATE))}토큰</b>(거래 토큰의 10%)을 돌려받아요.
              좋았던 점·아쉬운 점을 구체적으로 적어 주세요. 불만이어도 괜찮아요!
            </p>
          ) : (
            <p className="rounded-xl bg-red-50 px-3.5 py-2.5 text-sm text-danger">
              후기 기한이 지나서 인연고리 이용이 잠시 막혀 있어요. 후기를 쓰면 바로 다시 이용할 수 있어요. (기한이 지나 10% 환급은 없어요)
            </p>
          ))}
        <form onSubmit={submit} className="space-y-4" noValidate>
          <Stars value={rating} onChange={setRating} />
          <TextArea label="좋았던 점" placeholder="예: 장표마다 왜 고쳐야 하는지 이유까지 설명해 줬어요" value={good} onChange={(e) => setGood(e.target.value)} maxLength={1000} />
          <TextArea label="아쉬운 점 (선택)" placeholder="예: 시간이 조금 짧았어요" value={bad} onChange={(e) => setBad(e.target.value)} maxLength={1000} className="min-h-16" />
          <p className={`text-xs ${chars >= MIN_CHARS ? "text-green-700" : "text-muted"}`}>
            {chars >= MIN_CHARS ? "✅ 구체적으로 적어 주셔서 고마워요" : `환급을 받으려면 ${MIN_CHARS}자 이상 구체적으로 적어 주세요 (${chars}자)`}
          </p>
          {error && <ErrorBox message={error} />}
          <Button type="submit" disabled={busy}>
            후기 남기기
          </Button>
        </form>
      </Card>
    );
  }

  const r = data.review;
  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">{isProvider ? "받은 후기" : "내가 남긴 후기"}</h2>
          <Stars value={r.rating} />
        </div>
        <p className="text-sm">👍 {r.good_text}</p>
        {r.bad_text && <p className="text-sm text-muted">🤏 {r.bad_text}</p>}
      </Card>
      {data.analysis ? (
        <AnalysisCard a={data.analysis} isProvider={isProvider} providerName={exchange.provider.nickname} />
      ) : (
        <Card className="space-y-3">
          <p className="text-sm text-muted">후기는 저장됐지만 AI 분석이 아직 끝나지 않았어요.</p>
          {error && <ErrorBox message={error} />}
          {!isProvider && (
            <Button variant="ghost" disabled={busy} onClick={retry}>
              {busy ? "AI가 분석하는 중…" : "AI 분석 다시 시도"}
            </Button>
          )}
        </Card>
      )}
    </div>
  );
}
