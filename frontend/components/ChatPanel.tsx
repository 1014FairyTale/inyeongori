"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { api, ApiError, type ChatMessage, type ChatResponse, type ChatState } from "@/lib/api";

const POLL_MS = 3000; // 새 메시지 확인 간격 (결정 사항: 폴링)

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit" });
}

/**
 * 거래 채팅. 수락된 뒤부터 두 사람이 진행 방식을 이야기해요.
 * 화면이 보이는 동안 3초마다 새 메시지만(after_id) 가져와요.
 */
export function ChatPanel({
  exchangeId,
  initialState,
  counterpartName,
  onSystemMessage,
}: {
  exchangeId: number;
  initialState: ChatState;
  counterpartName: string;
  onSystemMessage?: () => void; // 상태 안내가 오면 거래 화면을 새로 불러요
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<ChatState>(initialState);
  const [otherRead, setOtherRead] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastId = useRef(0);
  const loaded = useRef(false);
  const listRef = useRef<HTMLDivElement>(null);
  const onSystemRef = useRef(onSystemMessage);
  useEffect(() => {
    onSystemRef.current = onSystemMessage;
  }, [onSystemMessage]);

  const append = useCallback((incoming: ChatMessage[]) => {
    if (incoming.length === 0) return;
    lastId.current = Math.max(lastId.current, incoming[incoming.length - 1].id);
    setMessages((prev) => {
      const seen = new Set(prev.map((m) => m.id));
      return [...prev, ...incoming.filter((m) => !seen.has(m.id))];
    });
  }, []);

  const poll = useCallback(async () => {
    try {
      const res = await api<ChatResponse>(`/exchanges/${exchangeId}/messages?after_id=${lastId.current}`);
      const hadSystem = loaded.current && res.messages.some((m) => m.kind === "system");
      append(res.messages);
      setState(res.state);
      setOtherRead(res.other_last_read_id);
      loaded.current = true;
      if (hadSystem) onSystemRef.current?.();
    } catch {
      // 잠깐 연결이 안 되면 다음 주기에 다시 시도해요
    }
  }, [exchangeId, append]);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    const start = () => {
      void poll();
      timer = setInterval(() => {
        if (document.visibilityState === "visible") void poll();
      }, POLL_MS);
    };
    start();
    const onVisible = () => document.visibilityState === "visible" && void poll();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      if (timer) clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [poll]);

  // 새 메시지가 오면 맨 아래로
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length]);

  async function send(e?: FormEvent) {
    e?.preventDefault();
    const body = text.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);
    try {
      const m = await api<ChatMessage>(`/exchanges/${exchangeId}/messages`, { method: "POST", json: { body } });
      append([m]);
      setText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "보내지 못했어요. 다시 시도해 주세요");
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // 한글 조합 중 Enter는 무시해요 (두 번 보내지는 문제 방지). Shift+Enter는 줄바꿈.
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send();
    }
  }

  const lastMine = [...messages].reverse().find((m) => m.mine);

  return (
    <section id="chat" className="overflow-hidden rounded-2xl border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="font-bold">💬 {counterpartName}님과 대화</h2>
        <p className="text-xs text-muted">
          {state === "open" ? "일정, 장소·온라인 도구 같은 진행 방식을 함께 정해 보세요" : "취소된 거래의 대화 기록이에요"}
        </p>
      </div>

      <div ref={listRef} className="max-h-96 min-h-48 space-y-2 overflow-y-auto bg-background px-3 py-3" aria-live="polite">
        {messages.length === 0 && <p className="py-10 text-center text-sm text-muted">불러오는 중…</p>}
        {messages.map((m) =>
          m.kind === "system" ? (
            <p key={m.id} className="mx-auto max-w-[90%] rounded-xl bg-brand-soft px-3 py-2 text-center text-xs text-brand">
              {m.body}
            </p>
          ) : (
            <div key={m.id} className={`flex flex-col ${m.mine ? "items-end" : "items-start"}`}>
              <div
                className={`max-w-[80%] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2 text-sm ${
                  m.mine ? "rounded-br-sm bg-brand text-white" : "rounded-bl-sm border border-border bg-card"
                }`}
              >
                {m.body}
              </div>
              <span className="mt-0.5 text-[11px] text-muted">
                {timeLabel(m.created_at)}
                {m.mine && lastMine?.id === m.id && otherRead != null && otherRead >= m.id && " · 읽음"}
              </span>
            </div>
          ),
        )}
      </div>

      {state === "open" ? (
        <form onSubmit={send} className="flex items-end gap-2 border-t border-border p-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            maxLength={1000}
            placeholder="예: 토요일 오후 2시에 줌으로 괜찮을까요?"
            aria-label="메시지 입력"
            className="max-h-32 min-h-11 flex-1 resize-none rounded-xl border border-border bg-background px-3 py-2.5 text-base outline-none focus:border-brand"
          />
          <button
            type="submit"
            disabled={sending || !text.trim()}
            className="h-11 shrink-0 rounded-xl bg-brand px-4 font-semibold text-white disabled:opacity-40"
          >
            보내기
          </button>
        </form>
      ) : (
        <p className="border-t border-border px-4 py-3 text-center text-sm text-muted">취소된 거래라 메시지를 보낼 수 없어요.</p>
      )}
      {error && <p className="px-4 pb-3 text-sm text-danger">{error}</p>}
    </section>
  );
}
