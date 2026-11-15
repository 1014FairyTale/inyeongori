import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

/*
 * 공통 UI. 각진 모서리, 1px 선, 주황 하나만 강조색.
 * 박스·배경색·그림자 대신 선과 글자 굵기로 구획을 나눠요.
 */

export function Button({
  children,
  variant = "primary",
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "text" }) {
  const base =
    "inline-flex w-full items-center justify-center px-4 py-3 text-base font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-40";
  const styles =
    variant === "primary"
      ? "bg-brand text-white hover:bg-foreground"
      : variant === "ghost"
        ? "border border-foreground text-foreground hover:bg-foreground hover:text-background"
        : "text-muted underline underline-offset-4 hover:text-foreground";
  return (
    <button className={`${base} ${styles} ${className}`} {...rest}>
      {children}
    </button>
  );
}

const inputBase =
  "w-full border bg-transparent px-3.5 py-3 text-base outline-none placeholder:text-muted/70 focus:border-foreground";

export function Field({
  label,
  hint,
  error,
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold">{label}</span>
      <input {...rest} className={`${inputBase} ${error ? "border-danger" : "border-line"} ${className}`} />
      {error ? <span className="text-sm text-danger">{error}</span> : hint ? <span className="text-sm text-muted">{hint}</span> : null}
    </label>
  );
}

export function TextArea({
  label,
  hint,
  error,
  className = "min-h-24",
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; hint?: string; error?: string }) {
  // className은 기본 스타일을 덮어쓰지 않고 '추가'돼요 (높이 조절용)
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold">{label}</span>
      <textarea {...rest} className={`block ${inputBase} ${error ? "border-danger" : "border-line"} ${className}`} />
      {error ? <span className="text-sm text-danger">{error}</span> : hint ? <span className="text-sm text-muted">{hint}</span> : null}
    </label>
  );
}

/** 구획: 박스 대신 위쪽 굵은 선 하나로 나눠요. */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`border-t border-foreground pt-4 ${className}`}>{children}</section>;
}

/** 작은 머리말 (구획 제목 위의 분류 글자) */
export function Eyebrow({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`text-xs font-bold tracking-wide text-brand ${className}`}>{children}</p>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <p role="alert" className="border-t border-danger pt-2 text-sm text-danger">
      {message}
    </p>
  );
}
