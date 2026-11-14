"use client";

import { useState, type FormEvent } from "react";
import type { AgreementTerms } from "@/lib/api";
import { Button, Field, TextArea } from "@/components/ui";

/** 교환 범위(합의서) 입력. 5단계에서 "AI로 정리하기"가 이 폼을 채워 줘요. */
export function TermsForm({
  initial,
  submitLabel,
  submitting,
  onSubmit,
  onCancel,
}: {
  initial?: AgreementTerms;
  submitLabel: string;
  submitting: boolean;
  onSubmit: (terms: AgreementTerms) => void;
  onCancel?: () => void;
}) {
  const [t, setT] = useState({
    request_text: initial?.request_text ?? "",
    scope: initial?.scope ?? "",
    quantity: initial?.quantity ?? "",
    revisions: initial?.revisions?.toString() ?? "",
    duration_minutes: initial?.duration_minutes?.toString() ?? "",
    notes: initial?.notes ?? "",
  });
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof t) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setT((v) => ({ ...v, [k]: e.target.value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    if (t.request_text.trim().length < 2) {
      setError("어떤 도움이 필요한지 적어 주세요");
      return;
    }
    setError(null);
    const num = (s: string) => (s.trim() === "" ? null : Number(s));
    onSubmit({
      request_text: t.request_text.trim(),
      scope: t.scope.trim() || null,
      quantity: t.quantity.trim() || null,
      revisions: num(t.revisions),
      duration_minutes: num(t.duration_minutes),
      notes: t.notes.trim() || null,
    });
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <TextArea
        label="요청 내용"
        placeholder="예: 발표 PPT 구성을 봐 주세요"
        value={t.request_text}
        onChange={set("request_text")}
        error={error ?? undefined}
        maxLength={1000}
      />
      <p className="text-sm text-muted">아래 조건을 미리 정해 두면 서로 기대가 달라서 생기는 갈등을 줄일 수 있어요.</p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="범위" placeholder="예: 구성 피드백" value={t.scope} onChange={set("scope")} maxLength={300} />
        <Field label="분량" placeholder="예: 10장" value={t.quantity} onChange={set("quantity")} maxLength={100} />
        <Field label="수정 횟수" type="number" min={0} max={20} placeholder="예: 1" value={t.revisions} onChange={set("revisions")} />
        <Field
          label="소요 시간(분)"
          type="number"
          min={5}
          max={600}
          placeholder="예: 30"
          value={t.duration_minutes}
          onChange={set("duration_minutes")}
        />
      </div>
      <TextArea label="기타 메모 (선택)" value={t.notes} onChange={set("notes")} maxLength={500} className="min-h-16" />
      <div className="flex gap-2">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            취소
          </Button>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "보내는 중…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
