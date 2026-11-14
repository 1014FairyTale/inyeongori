import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Button({
  children,
  variant = "primary",
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const base =
    "inline-flex w-full items-center justify-center rounded-xl px-4 py-3 text-base font-semibold transition disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-brand text-white hover:brightness-95"
      : "border border-border bg-card text-foreground hover:bg-brand-soft";
  return (
    <button className={`${base} ${styles} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  error,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium">{label}</span>
      <input
        className={`w-full rounded-xl border bg-card px-3.5 py-3 text-base outline-none focus:border-brand ${
          error ? "border-danger" : "border-border"
        }`}
        {...rest}
      />
      {error ? (
        <span className="text-sm text-danger">{error}</span>
      ) : hint ? (
        <span className="text-sm text-muted">{hint}</span>
      ) : null}
    </label>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-border bg-card p-5 ${className}`}>{children}</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">
      {message}
    </div>
  );
}
