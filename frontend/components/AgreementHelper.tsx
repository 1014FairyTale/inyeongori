"use client";

import { useState } from "react";
import { api, ApiError, type AgreementDraft, type AgreementTerms, type TermField } from "@/lib/api";
import { AiBadge } from "@/components/AiBadge";
import { Button, ErrorBox, TextArea } from "@/components/ui";

/**
 * 교환 범위 합의 도우미.
 * 모호한 요청 → AI가 조건으로 정리 → 빠진 조건은 보기 중에서 고르면 다시 정리 → 요청서에 채우기
 */
export function AgreementHelper({
  listingId,
  onApply,
}: {
  listingId: number;
  onApply: (terms: AgreementTerms) => void;
}) {
  const [raw, setRaw] = useState("");
  const [draft, setDraft] = useState<AgreementDraft | null>(null);
  const [answers, setAnswers] = useState<Partial<Record<TermField, string>>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(nextAnswers: Partial<Record<TermField, string>>) {
    if (raw.trim().length < 2) {
      setError("어떤 도움이 필요한지 한 줄이라도 적어 주세요");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const d = await api<AgreementDraft>("/ai/agreements/draft", {
        method: "POST",
        // 이전 정리 결과를 같이 보내서, 다시 정리해도 이미 정한 조건이 사라지지 않게 해요
        json: { listing_id: listingId, raw_request: raw.trim(), answers: nextAnswers, previous_terms: draft?.terms ?? null },
      });
      setDraft(d);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "AI가 응답하지 않았어요");
    } finally {
      setBusy(false);
    }
  }

  function answer(field: TermField, value: string) {
    const next = { ...answers, [field]: value };
    setAnswers(next);
    void run(next);
  }

  return (
    <div className="space-y-3 rounded-2xl border border-ai/30 bg-ai-soft/60 p-4">
      <div className="flex items-center gap-2">
        <AiBadge label="AI 합의 도우미" />
      </div>
      <p className="text-sm text-muted">
        &ldquo;PPT 봐주세요&rdquo;처럼 편하게 적으면, AI가 분량·범위·수정 횟수·시간을 정리해서 서로 기대가 다르지 않게 도와줘요.
      </p>
      <TextArea
        label="어떤 도움이 필요하세요?"
        placeholder="예: 다음 주 발표 PPT 좀 봐주세요"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        maxLength={500}
        className="min-h-16"
      />
      {!draft && (
        <Button type="button" disabled={busy} onClick={() => run(answers)} className="bg-ai">
          {busy ? "AI가 정리하는 중…" : "✨ AI로 조건 정리하기"}
        </Button>
      )}

      {error && (
        <div className="space-y-2">
          <ErrorBox message={error} />
          <Button type="button" variant="ghost" disabled={busy} onClick={() => run(answers)}>
            다시 시도
          </Button>
        </div>
      )}

      {draft && (
        <div className="space-y-3">
          <div className="rounded-xl bg-card px-3.5 py-3">
            <p className="text-xs font-medium text-ai">AI가 정리한 조건</p>
            <p className="font-semibold">{draft.summary}</p>
          </div>

          {draft.missing.map((q) => (
            <div key={q.field} className="space-y-2 rounded-xl bg-card px-3.5 py-3">
              <p className="text-sm font-semibold">🙋 {q.question}</p>
              <div className="flex flex-wrap gap-2">
                {q.options.map((o) => (
                  <button
                    key={o}
                    type="button"
                    disabled={busy}
                    onClick={() => answer(q.field, o)}
                    className="rounded-full border border-border bg-background px-3 py-1.5 text-sm hover:border-ai"
                  >
                    {o}
                  </button>
                ))}
              </div>
            </div>
          ))}
          {busy && <p className="text-center text-sm text-ai">AI가 답변을 반영하는 중…</p>}
          {draft.missing.length === 0 && !busy && <p className="text-sm text-green-700">✅ 중요한 조건이 모두 정해졌어요</p>}

          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setDraft(null);
                setAnswers({});
              }}
              className="py-2.5 text-sm"
            >
              처음부터
            </Button>
            <Button type="button" disabled={busy} onClick={() => onApply(draft.terms)} className="py-2.5 text-sm">
              요청서에 채우기
            </Button>
          </div>
          <p className="text-xs text-muted">채운 뒤에도 아래 요청서에서 직접 고칠 수 있어요.</p>
        </div>
      )}
    </div>
  );
}
