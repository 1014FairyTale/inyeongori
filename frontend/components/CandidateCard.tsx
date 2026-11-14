"use client";

import { useState } from "react";
import { api, ApiError, type DecisionResult, type TalentCandidate } from "@/lib/api";
import { AiBadge } from "@/components/AiBadge";
import { Button, ErrorBox, Field } from "@/components/ui";

/** AI 재능 후보 1개. [맞아요 / 아니에요 / 수정]으로 확정해요. */
export function CandidateCard({
  candidate,
  onChange,
}: {
  candidate: TalentCandidate;
  onChange: (next: TalentCandidate) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(candidate.final_name ?? candidate.name);
  const [description, setDescription] = useState(candidate.final_description ?? candidate.description);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(action: "accept" | "reject" | "edit") {
    setBusy(true);
    setError(null);
    try {
      const res = await api<DecisionResult>(`/discovery/candidates/${candidate.id}/decision`, {
        method: "POST",
        json: action === "edit" ? { action, name: name.trim(), description: description.trim() } : { action },
      });
      onChange(res.candidate);
      setEditing(false);
    } catch (e) {
      setError(e instanceof ApiError && e.code !== "VALIDATION_ERROR" ? e.message : "재능 이름을 2자 이상 적어 주세요");
    } finally {
      setBusy(false);
    }
  }

  const decided = candidate.status !== "pending";
  const kept = candidate.status === "accepted" || candidate.status === "edited";

  return (
    <article
      className={`space-y-3 rounded-2xl border bg-card p-5 transition ${
        kept ? "border-green-300" : candidate.status === "rejected" ? "border-border opacity-60" : "border-border"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <AiBadge />
        <span className="text-xs font-medium text-brand">{candidate.category}</span>
      </div>

      <div>
        <h3 className="text-lg font-bold">{candidate.final_name ?? candidate.name}</h3>
        {candidate.status === "edited" && candidate.final_name !== candidate.name && (
          <p className="text-xs text-muted">AI 원래 제안: {candidate.name}</p>
        )}
        {candidate.final_description && candidate.status === "edited" && (
          <p className="text-sm">{candidate.final_description}</p>
        )}
      </div>

      <div className="space-y-1 rounded-xl bg-background px-3.5 py-3 text-sm">
        <p className="font-medium text-muted">이렇게 생각했어요</p>
        <p>{candidate.evidence}</p>
        {candidate.source_quote && <p className="text-muted">— &ldquo;{candidate.source_quote}&rdquo;</p>}
      </div>

      {!decided && !editing && (
        <>
          <p className="font-semibold">🙋 {candidate.confirm_question}</p>
          <div className="grid grid-cols-3 gap-2">
            <Button disabled={busy} onClick={() => decide("accept")} className="px-2 py-2.5 text-sm">
              맞아요
            </Button>
            <Button variant="ghost" disabled={busy} onClick={() => decide("reject")} className="px-2 py-2.5 text-sm">
              아니에요
            </Button>
            <Button variant="ghost" disabled={busy} onClick={() => setEditing(true)} className="px-2 py-2.5 text-sm">
              수정
            </Button>
          </div>
        </>
      )}

      {editing && (
        <div className="space-y-3">
          <Field label="재능 이름" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} />
          <Field
            label="이 재능으로 해 줄 수 있는 도움"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={200}
          />
          <div className="flex gap-2">
            <Button variant="ghost" disabled={busy} onClick={() => setEditing(false)} className="py-2.5 text-sm">
              취소
            </Button>
            <Button disabled={busy} onClick={() => decide("edit")} className="py-2.5 text-sm">
              이렇게 저장
            </Button>
          </div>
        </div>
      )}

      {decided && !editing && (
        <div className="flex items-center justify-between gap-2 border-t border-border pt-3 text-sm">
          <span className={kept ? "font-semibold text-green-700" : "text-muted"}>
            {candidate.status === "accepted" && "✅ 내 재능으로 저장했어요"}
            {candidate.status === "edited" && "✏️ 고쳐서 저장했어요"}
            {candidate.status === "rejected" && "빼 두었어요"}
          </span>
          <div className="flex gap-3">
            {candidate.status === "rejected" ? (
              <button className="text-brand" disabled={busy} onClick={() => decide("accept")}>
                다시 넣기
              </button>
            ) : (
              <>
                <button className="text-muted" disabled={busy} onClick={() => setEditing(true)}>
                  수정
                </button>
                <button className="text-muted" disabled={busy} onClick={() => decide("reject")}>
                  빼기
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {error && <ErrorBox message={error} />}
    </article>
  );
}
