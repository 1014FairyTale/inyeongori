"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { api, ApiError, type AgreementTerms, type Exchange, type ExchangeAction } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import { RequireLogin } from "@/components/RequireLogin";
import { StatusBadge } from "@/components/StatusBadge";
import { TermsForm } from "@/components/TermsForm";
import { TokenAmount } from "@/components/TokenAmount";
import { ReviewSection } from "@/components/ReviewSection";
import { ChatPanel } from "@/components/ChatPanel";
import { Button, Card, ErrorBox } from "@/components/ui";

const ACTIONS: Record<
  Exclude<ExchangeAction, "propose" | "review">,
  { label: string; path: string; variant: "primary" | "ghost"; confirm?: string }
> = {
  agree: { label: "합의서에 동의하기", path: "agree", variant: "primary" },
  complete: { label: "완료 확인", path: "complete", variant: "primary" },
  approve_cancel: {
    label: "취소 승인 (요청자에게 환불)",
    path: "cancel",
    variant: "primary",
    confirm: "취소를 승인하면 보류된 토큰이 요청자에게 전액 환불돼요. 승인할까요?",
  },
  decline_cancel: { label: "취소 거절", path: "cancel/decline", variant: "ghost" },
  reject: { label: "요청 거절", path: "reject", variant: "ghost", confirm: "이 요청을 거절할까요?" },
  withdraw: { label: "요청 철회", path: "reject", variant: "ghost", confirm: "요청을 철회할까요?" },
  cancel: {
    label: "거래 취소 (전액 환불)",
    path: "cancel",
    variant: "ghost",
    confirm: "거래를 취소하면 보류된 토큰이 요청자에게 전액 환불돼요. 취소할까요?",
  },
  request_cancel: {
    label: "취소 요청",
    path: "cancel",
    variant: "ghost",
    confirm: "제공자가 승인하면 토큰이 환불돼요. 취소를 요청할까요?",
  },
};

const STEPS = ["요청", "합의·수락", "진행", "완료"];

function stepIndex(ex: Exchange): number {
  if (ex.status === "requested") return 1;
  if (ex.status === "accepted" || ex.status === "cancel_requested") return 2;
  if (ex.status === "completed") return 3;
  return -1;
}

function TermsView({ terms }: { terms: AgreementTerms }) {
  const rows: [string, string | null][] = [
    ["범위", terms.scope ?? null],
    ["분량", terms.quantity ?? null],
    ["수정 횟수", terms.revisions != null ? `${terms.revisions}회` : null],
    ["소요 시간", terms.duration_minutes != null ? `${terms.duration_minutes}분` : null],
    ["메모", terms.notes ?? null],
  ];
  return (
    <div className="space-y-2">
      <p className="whitespace-pre-wrap">{terms.request_text}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-muted">{k}</dt>
            <dd className={v ? "" : "text-muted"}>{v ?? "정하지 않음"}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function ExchangeDetail() {
  const { id } = useParams<{ id: string }>();
  const { refresh } = useAuth();
  const [ex, setEx] = useState<Exchange | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);

  const load = useCallback(async () => {
    try {
      setEx(await api<Exchange>(`/exchanges/${id}`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "불러오지 못했어요");
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    api<Exchange>(`/exchanges/${id}`)
      .then((d) => !cancelled && setEx(d))
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : "불러오지 못했어요"));
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function run(path: string, json?: unknown) {
    setBusy(true);
    setError(null);
    try {
      setEx(await api<Exchange>(`/exchanges/${id}/${path}`, { method: "POST", json }));
      setEditing(false);
      await refresh(); // 헤더 잔액 갱신
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "처리하지 못했어요. 다시 시도해 주세요");
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (!ex) return error ? <ErrorBox message={error} /> : <p className="py-10 text-center text-muted">불러오는 중…</p>;

  const counterpart = ex.my_role === "requester" ? ex.provider : ex.requester;
  const step = stepIndex(ex);
  const ag = ex.agreement;
  const mineAgreed = ex.my_role === "requester" ? ag.requester_agreed : ag.provider_agreed;
  const theirsAgreed = ex.my_role === "requester" ? ag.provider_agreed : ag.requester_agreed;
  const mineDone = ex.my_role === "requester" ? ex.requester_done : ex.provider_done;
  const theirsDone = ex.my_role === "requester" ? ex.provider_done : ex.requester_done;

  let hint = "";
  if (ex.status === "requested") {
    hint = mineAgreed
      ? `${counterpart.nickname}님이 합의서에 동의하면 거래가 시작돼요.`
      : "합의서 내용을 확인하고 동의하면 거래가 시작돼요. 조건을 바꾸고 싶으면 수정 제안을 보내세요.";
  } else if (ex.status === "accepted") {
    hint = mineDone
      ? `${counterpart.nickname}님의 완료 확인을 기다리고 있어요.`
      : ex.my_role === "requester"
        ? "도움을 다 받았다면 완료를 확인해 주세요. 양쪽이 확인하면 토큰이 지급돼요."
        : "도움을 다 드렸다면 완료를 확인해 주세요. 양쪽이 확인하면 토큰을 받아요.";
  } else if (ex.status === "cancel_requested") {
    hint = ex.my_role === "provider" ? "요청자가 취소를 요청했어요. 승인하면 토큰이 환불돼요." : "제공자의 취소 승인을 기다리고 있어요.";
  } else if (ex.status === "completed") {
    hint =
      ex.my_role === "provider"
        ? `${ex.price_tokens}토큰을 받았어요. 수고하셨어요!`
        : ex.has_review
          ? "거래가 완료됐어요. 후기를 남겨 주셔서 고마워요!"
          : "거래가 완료됐어요. 아래에서 후기를 남겨 주세요 ✍️";
  } else {
    hint = ex.status === "rejected" ? "제공자가 요청을 거절했어요." : "거래가 취소됐어요. 보류된 토큰이 있었다면 환불됐어요.";
  }

  const buttons = ex.actions.filter(
    (a): a is Exclude<ExchangeAction, "propose" | "review"> => a !== "propose" && a !== "review",
  );

  return (
    <div className="space-y-5">
      <Link href="/exchanges" className="text-sm text-muted">
        ← 내 거래
      </Link>

      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <StatusBadge status={ex.status} />
          <TokenAmount amount={ex.price_tokens} />
        </div>
        <h1 className="text-xl font-bold">
          {ex.listing_id ? <Link href={`/market/${ex.listing_id}`}>{ex.listing_title}</Link> : "재능 교환"}
        </h1>
        <p className="text-sm text-muted">
          {ex.my_role === "requester" ? "제공자" : "요청자"} <b className="text-foreground">{counterpart.nickname}</b> ·{" "}
          {formatDate(ex.created_at)}
        </p>
        {step >= 0 && (
          <ol className="flex items-center gap-1 pt-1 text-xs">
            {STEPS.map((s, i) => (
              <li key={s} className="flex flex-1 flex-col items-center gap-1">
                <span className={`h-1.5 w-full rounded-full ${i <= step ? "bg-brand" : "bg-border"}`} />
                <span className={i <= step ? "font-semibold text-brand" : "text-muted"}>{s}</span>
              </li>
            ))}
          </ol>
        )}
      </Card>

      <div className="rounded-xl bg-brand-soft px-4 py-3 text-sm">{hint}</div>

      {ex.chat_state !== "closed" && (
        <a href="#chat" className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-sm">
          <span>
            💬 <b>{counterpart.nickname}</b>님과 대화하기
          </span>
          {ex.unread_count > 0 ? (
            <span className="rounded-full bg-brand px-2 py-0.5 text-xs font-bold text-white">새 메시지 {ex.unread_count}</span>
          ) : (
            <span className="text-muted">↓</span>
          )}
        </a>
      )}
      {ex.status === "requested" && (
        <p className="text-center text-xs text-muted">거래가 수락되면 {counterpart.nickname}님과 채팅할 수 있어요.</p>
      )}

      {ex.status === "completed" && (
        <ReviewSection
          exchange={ex}
          onChanged={() => {
            void load();
            void refresh(); // 보너스를 받으면 헤더 잔액이 바뀌어요
          }}
        />
      )}

      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">
            합의서 <span className="text-sm font-normal text-muted">v{ag.version}</span>
          </h2>
          {ag.ai_generated && (
            <span className="rounded-full bg-ai-soft px-2 py-0.5 text-xs font-semibold text-ai">✨ AI 제안</span>
          )}
        </div>
        {editing ? (
          <TermsForm
            initial={ag.terms}
            submitLabel="수정 제안 보내기"
            submitting={busy}
            onSubmit={(terms) => run("agreement", { terms })}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            <TermsView terms={ag.terms} />
            <div className="space-y-1 border-t border-border pt-3 text-sm">
              <p>
                <span className="text-muted">합의 동의 · </span>
                {mineAgreed ? "✅" : "⏳"} 나 &nbsp; {theirsAgreed ? "✅" : "⏳"} {counterpart.nickname}
              </p>
              {(ex.status === "accepted" || ex.status === "completed") && (
                <p>
                  <span className="text-muted">완료 확인 · </span>
                  {mineDone ? "✅" : "⏳"} 나 &nbsp; {theirsDone ? "✅" : "⏳"} {counterpart.nickname}
                </p>
              )}
            </div>
          </>
        )}
      </Card>

      {error && <ErrorBox message={error} />}

      {!editing && (buttons.length > 0 || ex.actions.includes("propose")) && (
        <div className="space-y-2">
          {buttons.map((a) => {
            const spec = ACTIONS[a];
            return (
              <Button
                key={a}
                variant={spec.variant}
                disabled={busy}
                onClick={() => {
                  if (spec.confirm && !window.confirm(spec.confirm)) return;
                  void run(spec.path);
                }}
              >
                {spec.label}
              </Button>
            );
          })}
          {ex.actions.includes("propose") && (
            <Button variant="ghost" disabled={busy} onClick={() => setEditing(true)}>
              조건 수정 제안
            </Button>
          )}
        </div>
      )}

      {ex.chat_state !== "closed" && (
        <ChatPanel
          key={ex.id}
          exchangeId={ex.id}
          initialState={ex.chat_state}
          counterpartName={counterpart.nickname}
          onSystemMessage={() => {
            // 상대가 완료·취소를 하면 안내 메시지가 와요 → 상태·버튼·잔액을 새로 불러요
            void load();
            void refresh();
          }}
        />
      )}
    </div>
  );
}

export default function ExchangeDetailPage() {
  return (
    <RequireLogin>
      <Suspense fallback={<p className="py-10 text-center text-muted">불러오는 중…</p>}>
        <ExchangeDetail />
      </Suspense>
    </RequireLogin>
  );
}
