"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui";
import { TokenAmount } from "@/components/TokenAmount";

// 4단계에서 자기소개·문답 입력과 AI 재능 발굴 화면으로 바뀌어요.
export default function OnboardingPage() {
  const { me, loading } = useAuth();

  if (loading) return null;
  if (!me) {
    return (
      <Card className="space-y-3 text-center">
        <p>재능을 찾으려면 먼저 가입해 주세요.</p>
        <Link href="/signup?next=/onboarding" className="font-semibold text-brand">
          가입하러 가기
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{me.user.nickname}님, 환영해요! 🎉</h1>
      <Card className="space-y-2">
        <p>가입 축하 토큰이 지급됐어요.</p>
        <TokenAmount amount={me.wallet.available} className="text-lg" />
      </Card>
      <Card className="text-muted">AI 재능 찾기 화면은 곧 열려요. (4단계)</Card>
    </div>
  );
}
