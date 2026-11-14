"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type DiscoverySession, type TalentCandidate } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AiLoading } from "@/components/AiLoading";
import { CandidateCard } from "@/components/CandidateCard";
import { RequireLogin } from "@/components/RequireLogin";
import { Button, Card, ErrorBox, Field, TextArea } from "@/components/ui";

const LOADING_MESSAGES = [
  "적어 주신 경험을 꼼꼼히 읽고 있어요…",
  "경험 속에 숨은 능력을 찾고 있어요…",
  "다른 학생에게 도움이 될 재능을 고르고 있어요…",
  "확인 질문을 만들고 있어요…",
];

const EXAMPLE = {
  intro_text: "저는 딱히 잘하는 게 없는 평범한 경영학과 2학년이에요. 동아리 총무를 1년 했어요.",
  recent_roles: "동아리 총무, MT 준비도 제가 다 했어요",
  friends_ask: "친구들이 과제 PPT 좀 봐 달라고 해요",
  confident_tools: "엑셀, 노션은 자신 있어요",
};

type Form = typeof EXAMPLE;
const EMPTY: Form = { intro_text: "", recent_roles: "", friends_ask: "", confident_tools: "" };

function Onboarding() {
  const { me } = useAuth();
  const [session, setSession] = useState<DiscoverySession | null>(null);
  const [checked, setChecked] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Form>(EMPTY);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<DiscoverySession | null>("/discovery/sessions/latest")
      .then((s) => {
        setSession(s);
        setShowForm(!s);
      })
      .catch(() => setShowForm(true))
      .finally(() => setChecked(true));
  }, []);

  const set = (k: keyof Form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function run(e?: FormEvent) {
    e?.preventDefault();
    if (form.intro_text.trim().length < 5) {
      setError("자기소개를 5자 이상 적어 주세요. 짧아도 괜찮아요!");
      return;
    }
    setError(null);
    setRunning(true);
    try {
      const s = await api<DiscoverySession>("/discovery/sessions", {
        method: "POST",
        json: {
          intro_text: form.intro_text,
          answers: {
            recent_roles: form.recent_roles || null,
            friends_ask: form.friends_ask || null,
            confident_tools: form.confident_tools || null,
          },
        },
      });
      setSession(s);
      setShowForm(false);
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI가 응답하지 않았어요");
    } finally {
      setRunning(false);
    }
  }

  function updateCandidate(next: TalentCandidate) {
    setSession((s) => (s ? { ...s, candidates: s.candidates.map((c) => (c.id === next.id ? next : c)) } : s));
  }

  if (!checked) return <p className="py-10 text-center text-muted">불러오는 중…</p>;
  if (running) return <AiLoading messages={LOADING_MESSAGES} />;

  if (showForm || !session) {
    return (
      <div className="space-y-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">{me?.user.nickname}님의 숨은 재능을 찾아 볼게요 ✨</h1>
          <p className="text-muted">대단한 경험이 아니어도 괜찮아요. 평소 하던 일을 편하게 적어 주세요.</p>
        </div>
        <Card>
          <form onSubmit={run} className="space-y-4" noValidate>
            <TextArea
              label="자기소개"
              placeholder="예: 경영학과 2학년이에요. 동아리 총무를 1년 했어요."
              value={form.intro_text}
              onChange={set("intro_text")}
              maxLength={2000}
            />
            <Field
              label="최근에 맡았던 역할은요?"
              placeholder="예: 동아리 총무, 조장, 과외 선생님"
              value={form.recent_roles}
              onChange={set("recent_roles")}
              maxLength={500}
            />
            <Field
              label="친구들이 자주 부탁하는 건요?"
              placeholder="예: PPT 봐 주기, 맛집 추천, 시간표 짜기"
              value={form.friends_ask}
              onChange={set("friends_ask")}
              maxLength={500}
            />
            <Field
              label="자신 있는 도구는요?"
              placeholder="예: 엑셀, 노션, 포토샵, 기타"
              value={form.confident_tools}
              onChange={set("confident_tools")}
              maxLength={500}
            />
            {error && (
              <div className="space-y-2">
                <ErrorBox message={error} />
              </div>
            )}
            <Button type="submit">{error && form.intro_text.trim().length >= 5 ? "다시 시도" : "✨ AI로 내 재능 찾기"}</Button>
            <button type="button" onClick={() => setForm(EXAMPLE)} className="w-full text-center text-sm text-muted underline">
              예시로 채워 보기
            </button>
          </form>
        </Card>
        {session && (
          <button onClick={() => setShowForm(false)} className="w-full text-center text-sm text-muted">
            ← 지난 결과 보기
          </button>
        )}
      </div>
    );
  }

  const kept = session.candidates.filter((c) => c.status === "accepted" || c.status === "edited");
  const pending = session.candidates.filter((c) => c.status === "pending").length;

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">이런 재능이 숨어 있었어요!</h1>
        {session.encouragement && (
          <p className="rounded-xl bg-ai-soft px-4 py-3 text-sm text-ai">💜 {session.encouragement}</p>
        )}
        <p className="text-sm text-muted">
          AI가 추론한 후보예요. 확정은 {me?.user.nickname}님이 해요. 맞는 것만 골라 주세요.
        </p>
      </div>

      <div className="space-y-3">
        {session.candidates.map((c) => (
          <CandidateCard key={c.id} candidate={c} onChange={updateCandidate} />
        ))}
      </div>

      <Card className="space-y-3">
        <p className="font-semibold">
          확정한 재능 {kept.length}개{pending > 0 && <span className="font-normal text-muted"> · 남은 후보 {pending}개</span>}
        </p>
        {kept.length > 0 ? (
          <>
            <p className="text-sm text-muted">확정한 재능을 마켓에 올리면 다른 학생이 토큰으로 요청할 수 있어요.</p>
            <Link
              href={`/market/new?${new URLSearchParams({
                title: kept[0].final_name ?? kept[0].name,
                category: kept[0].category,
                description: kept[0].final_description ?? kept[0].description,
              })}`}
              className="block rounded-xl bg-brand px-4 py-3 text-center font-semibold text-white"
            >
              &lsquo;{kept[0].final_name ?? kept[0].name}&rsquo; 마켓에 올리기
            </Link>
            <Link href="/me" className="block text-center text-sm font-medium text-brand">
              내 재능 모두 보기
            </Link>
          </>
        ) : (
          <p className="text-sm text-muted">맞는 후보에 &lsquo;맞아요&rsquo;를 누르면 내 재능으로 저장돼요.</p>
        )}
      </Card>

      <button
        onClick={() => {
          setForm({
            intro_text: session.intro_text,
            recent_roles: session.answers.recent_roles ?? "",
            friends_ask: session.answers.friends_ask ?? "",
            confident_tools: session.answers.confident_tools ?? "",
          });
          setShowForm(true);
        }}
        className="w-full text-center text-sm text-muted underline"
      >
        내용을 고쳐서 다시 찾기
      </button>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <RequireLogin>
      <Onboarding />
    </RequireLogin>
  );
}
