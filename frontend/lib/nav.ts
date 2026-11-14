// 로그인·가입 후 돌아갈 경로. 외부 주소로 튀지 않도록 내부 경로만 허용해요.
export function safeNext(next: string | null, fallback = "/"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//")) return fallback;
  return next;
}
