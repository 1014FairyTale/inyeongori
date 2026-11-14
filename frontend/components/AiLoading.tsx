"use client";

import { useEffect, useState } from "react";

/** AI가 처리하는 동안 보여 주는 로딩 화면. 문구가 몇 초마다 바뀌어요. */
export function AiLoading({ messages }: { messages: string[] }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % messages.length), 2200);
    return () => clearInterval(t);
  }, [messages.length]);

  return (
    <div role="status" aria-live="polite" className="flex flex-col items-center gap-4 py-16 text-center">
      <div className="relative h-14 w-14">
        <span className="absolute inset-0 animate-ping rounded-full bg-ai/20" />
        <span className="absolute inset-2 flex items-center justify-center rounded-full bg-ai text-2xl text-white">✨</span>
      </div>
      <p className="font-semibold text-ai">{messages[i]}</p>
      <p className="text-sm text-muted">AI가 분석하는 데 몇 초 정도 걸려요</p>
    </div>
  );
}
