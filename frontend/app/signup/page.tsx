"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { safeNext } from "@/lib/nav";
import { Button, Card, ErrorBox, Field } from "@/components/ui";

function SignupForm() {
  const { signup } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"), "/onboarding");

  const [form, setForm] = useState({ email: "", password: "", nickname: "", school: "", major: "" });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setSubmitting(true);
    try {
      await signup({
        email: form.email,
        password: form.password,
        nickname: form.nickname,
        school: form.school || undefined,
        major: form.major || undefined,
      });
      router.push(`/guide?next=${encodeURIComponent(next)}`); // 처음 가입하면 이용 가이드부터 보여 줘요
    } catch (err) {
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
        const fields = (err.details.fields as { field: string }[] | undefined) ?? [];
        const map: Record<string, string> = {};
        for (const f of fields) {
          map[f.field] =
            f.field === "password"
              ? "비밀번호는 8자 이상으로 입력해 주세요"
              : f.field === "email"
                ? "이메일 형식을 확인해 주세요"
                : "입력값을 확인해 주세요";
        }
        setFieldErrors(map);
      } else {
        setError(err instanceof ApiError ? err.message : "가입하지 못했어요. 다시 시도해 주세요");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-black">반가워요</h1>
        <p className="text-muted">
          가입하면 <b className="text-brand">100토큰</b>을 드려요. 바로 재능을 나누고 받아 보세요.
        </p>
      </div>
      <Card>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <Field label="이메일" type="email" autoComplete="email" required value={form.email} onChange={set("email")} error={fieldErrors.email} />
          <Field
            label="비밀번호"
            type="password"
            autoComplete="new-password"
            required
            value={form.password}
            onChange={set("password")}
            hint="8자 이상"
            error={fieldErrors.password}
          />
          <Field label="닉네임" required maxLength={40} value={form.nickname} onChange={set("nickname")} error={fieldErrors.nickname} />
          <div className="grid grid-cols-2 gap-3">
            <Field label="학교 (선택)" maxLength={80} value={form.school} onChange={set("school")} />
            <Field label="전공 (선택)" maxLength={80} value={form.major} onChange={set("major")} />
          </div>
          {error && <ErrorBox message={error} />}
          <Button type="submit" disabled={submitting}>
            {submitting ? "가입하는 중…" : "가입하고 100토큰 받기"}
          </Button>
        </form>
      </Card>
      <p className="text-center text-sm text-muted">
        이미 계정이 있나요?{" "}
        <Link href={`/login?next=${encodeURIComponent(next)}`} className="font-medium text-brand">
          로그인
        </Link>
      </p>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}
