"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { safeNext } from "@/lib/nav";
import { Button, Card, ErrorBox, Field } from "@/components/ui";

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push(next);
    } catch (err) {
      setError(
        err instanceof ApiError && err.code !== "VALIDATION_ERROR"
          ? err.message
          : "이메일과 비밀번호를 확인해 주세요",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">다시 오셨네요 😊</h1>
      <Card>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <Field label="이메일" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Field
            label="비밀번호"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <ErrorBox message={error} />}
          <Button type="submit" disabled={submitting}>
            {submitting ? "로그인하는 중…" : "로그인"}
          </Button>
        </form>
      </Card>
      <p className="text-center text-sm text-muted">
        처음이신가요?{" "}
        <Link href={`/signup?next=${encodeURIComponent(next)}`} className="font-medium text-brand">
          가입하고 100토큰 받기
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
