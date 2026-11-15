"use client";

import { useEffect, useState } from "react";
import { LogoSpinner } from "@/components/Logo";

/** AI가 처리하는 동안 보여 주는 로딩 화면. 로고의 두 고리가 돌고, 문구가 몇 초마다 바뀌어요. */
export function AiLoading({ messages }: { messages: string[] }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % messages.length), 2200);
    return () => clearInterval(t);
  }, [messages.length]);

  return (
    <div aria-live="polite" className="flex flex-col items-center gap-5 py-20 text-center">
      <LogoSpinner size={56} label="AI가 처리하는 중" />
      <p className="text-lg font-bold">{messages[i]}</p>
      <p className="text-sm text-muted">AI가 분석하는 데 몇 초 정도 걸려요</p>
    </div>
  );
}
